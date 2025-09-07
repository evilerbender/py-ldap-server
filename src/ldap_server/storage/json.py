"""
JSON-backed LDAP storage backend with hot reload support and federation capabilities.
"""
import json
import logging
import tempfile
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Any, Union, Optional
from twisted.internet import defer
from ldaptor.ldiftree import LDIFTreeEntry
from ldaptor.protocols.ldap import distinguishedname
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

from ldap_server.auth.password import PasswordManager


class FederatedFileWatcher(FileSystemEventHandler):
    """Enhanced file system event handler for multiple JSON files with debouncing."""
    
    def __init__(self, json_storage, debounce_time: float = 0.5):
        self.json_storage = json_storage
        self.debounce_time = debounce_time
        self._pending_reloads = set()
        self._timer = None
        self._lock = threading.Lock()
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Check if this is one of our watched JSON files
        file_path = Path(event.src_path)
        if hasattr(self.json_storage, 'json_files') and file_path in self.json_storage.json_files:
            with self._lock:
                self._pending_reloads.add(file_path)
                
                # Cancel existing timer and start a new one
                if self._timer:
                    self._timer.cancel()
                
                self._timer = threading.Timer(self.debounce_time, self._process_pending_reloads)
                self._timer.start()
        elif hasattr(self.json_storage, 'json_path') and event.src_path.endswith(self.json_storage.json_path):
            # Handle legacy single file watching
            self._handle_single_file_change(event.src_path)
    
    def _handle_single_file_change(self, file_path: str):
        """Handle single file change for legacy JSONStorage."""
        try:
            logging.info(f"Reloading JSON entries from {file_path}")
            self.json_storage._load_json()
            logging.info("Reload complete (applied atomically)")
        except Exception as e:
            logging.error(f"Failed to reload JSON: {e} (keeping old data)")
    
    def _process_pending_reloads(self):
        """Process all pending file reloads after debounce period."""
        with self._lock:
            if self._pending_reloads:
                logging.info(f"Reloading JSON files: {[str(f) for f in self._pending_reloads]}")
                try:
                    self.json_storage._load_json()
                    logging.info("JSON federation reload completed successfully")
                except Exception as e:
                    logging.error(f"Error reloading JSON federation: {e}")
                finally:
                    self._pending_reloads.clear()


class FederatedJSONStorage:
    """
    Enhanced JSON storage backend that supports loading and merging data from multiple JSON files.
    
    Features:
    - Load data from multiple JSON files
    - Automatic merging with conflict resolution
    - Hot-reload for all files
    - Configurable merge strategies
    """
    
    def __init__(self, 
                 json_files: Union[str, List[str]], 
                 merge_strategy: str = "last_wins",
                 hash_plain_passwords: bool = True,
                 enable_watcher: bool = True,
                 debounce_time: float = 0.5):
        """
        Initialize federated JSON storage.
        
        Args:
            json_files: Single file path or list of JSON file paths
            merge_strategy: How to handle conflicts ("last_wins", "first_wins", "error")
            hash_plain_passwords: Whether to hash plain text passwords
            enable_watcher: Enable automatic file watching and reloading
            debounce_time: Debounce time for file change detection
        """
        # Normalize json_files to a list of Path objects
        if isinstance(json_files, str):
            self.json_files = [Path(json_files)]
        else:
            self.json_files = [Path(f) for f in json_files]
        
        self.merge_strategy = merge_strategy
        self.hash_plain_passwords = hash_plain_passwords
        self.enable_watcher = enable_watcher
        self.debounce_time = debounce_time
        
        # Storage state
        self._temp_dir = tempfile.mkdtemp(prefix="ldap_federated_json_")
        self.root_ref: Dict[str, LDIFTreeEntry] = {"root": None}
        self._lock = threading.RLock()
        self._observer = None
        self._file_handler = None
        
        # Statistics
        self.load_stats = {
            'last_load_time': None,
            'total_entries': 0,
            'files_loaded': 0,
            'merge_conflicts': 0,
            'load_duration': 0.0
        }
        
        # Load initial data
        try:
            self._load_json()
        except ValueError as e:
            # For single file mode (backward compatibility), propagate file not found errors
            if len(self.json_files) == 1 and "No JSON files could be loaded" in str(e):
                # Check if the single file doesn't exist and re-raise as FileNotFoundError
                if not self.json_files[0].exists():
                    raise FileNotFoundError(f"No such file or directory: '{self.json_files[0]}'")
            raise
        
        # Setup file watching if enabled
        if self.enable_watcher:
            self._setup_file_watching()
    
    def _setup_file_watching(self):
        """Setup file system watching for automatic reloads."""
        try:
            self._observer = Observer()
            self._file_handler = FederatedFileWatcher(self, self.debounce_time)
            
            # Watch directories containing our JSON files
            watched_dirs = set()
            for json_file in self.json_files:
                if json_file.exists():
                    parent_dir = json_file.parent
                    if parent_dir not in watched_dirs:
                        self._observer.schedule(self._file_handler, str(parent_dir), recursive=False)
                        watched_dirs.add(parent_dir)
                        logging.debug(f"Watching directory: {parent_dir}")
            
            self._observer.start()
            logging.info(f"File watching enabled for {len(self.json_files)} JSON files")
            
        except Exception as e:
            logging.error(f"Failed to setup file watching: {e}")
            self._observer = None
            self._file_handler = None
    
    def _load_json(self):
        """Load and merge data from all JSON files."""
        start_time = time.time()
        
        with self._lock:
            try:
                logging.info(f"Loading data from {len(self.json_files)} JSON files...")
                
                # Load and merge data from all files
                merged_data = self._load_and_merge_files()
                
                # Create directory tree from merged data
                root = self._build_ldif_tree(merged_data)
                self.root_ref["root"] = root
                
                # Update statistics
                load_duration = time.time() - start_time
                self._update_load_stats(merged_data, load_duration)
                
                logging.info(f"Federation load completed: {self.load_stats['total_entries']} entries "
                           f"from {self.load_stats['files_loaded']} files in {load_duration:.3f}s")
                
            except Exception as e:
                logging.error(f"Failed to reload JSON federation: {e}")
                raise
    
    def _load_and_merge_files(self) -> List[Dict[str, Any]]:
        """Load and merge data from all JSON files."""
        merged_entries = []
        entries_by_dn = {}
        files_loaded = 0
        merge_conflicts = 0
        
        for json_file in self.json_files:
            try:
                if not json_file.exists():
                    logging.warning(f"JSON file not found: {json_file}")
                    continue
                
                logging.debug(f"Loading JSON file: {json_file}")
                
                entries = self._load_json_entries(str(json_file))
                
                # Merge this file's data
                conflicts = self._merge_entries(entries_by_dn, entries, str(json_file))
                merge_conflicts += conflicts
                files_loaded += 1
                
                logging.debug(f"Loaded {len(entries)} entries from {json_file}")
                
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON in file {json_file}: {e}")
                # For single file mode (backward compatibility), propagate JSON decode errors directly
                if len(self.json_files) == 1:
                    raise e
                else:
                    raise ValueError(f"Invalid JSON in file {json_file}: {e}")
            except Exception as e:
                logging.error(f"Error loading file {json_file}: {e}")
                raise
        
        if files_loaded == 0:
            raise ValueError("No JSON files could be loaded")
        
        # Convert merged entries back to list format
        merged_entries = [{"dn": dn, "attributes": attrs} for dn, attrs in entries_by_dn.items()]
        
        # Store stats for later use
        self._temp_files_loaded = files_loaded
        self._temp_merge_conflicts = merge_conflicts
        
        return merged_entries
    
    def _merge_entries(self, target: Dict[str, Dict[str, Any]], entries: List[Dict[str, Any]], source_name: str) -> int:
        """
        Merge entries into target according to merge strategy.
        
        Returns the number of conflicts encountered.
        """
        conflicts = 0
        
        for entry in entries:
            dn = entry["dn"]
            attributes = entry["attributes"]
            
            if dn in target:
                conflicts += 1
                
                if self.merge_strategy == "first_wins":
                    logging.debug(f"Merge conflict for {dn}: keeping first entry (ignoring {source_name})")
                    continue
                elif self.merge_strategy == "last_wins":
                    logging.debug(f"Merge conflict for {dn}: overwriting with entry from {source_name}")
                    target[dn] = attributes
                elif self.merge_strategy == "error":
                    raise ValueError(f"Merge conflict for DN '{dn}' between existing data and {source_name}")
                else:
                    raise ValueError(f"Unknown merge strategy: {self.merge_strategy}")
            else:
                target[dn] = attributes
        
        return conflicts
    
    def _load_json_entries(self, path: str) -> List[Dict[str, Any]]:
        """Load and validate JSON entries from file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list of entries")
        for e in data:
            if "dn" not in e or "attributes" not in e:
                raise ValueError("Each entry needs 'dn' and 'attributes'")
            if not isinstance(e["attributes"], dict):
                raise ValueError("'attributes' must be a dict of attr -> [values]")
            for k, v in e["attributes"].items():
                if not isinstance(v, list):
                    raise ValueError(f"Attribute '{k}' values must be a list")
        return data
    
    def _upgrade_passwords(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Upgrade plain text passwords to secure hashes."""
        upgraded_entries = []
        
        for entry in entries:
            # Create a copy to avoid modifying original
            updated_entry = entry.copy()
            attributes = updated_entry.get("attributes", {}).copy()
            
            # Check for userPassword attribute
            if "userPassword" in attributes:
                passwords = attributes["userPassword"]
                hashed_passwords = []
                
                for password in passwords:
                    # Only hash if it's plain text (no format prefix)
                    if not password.startswith("{"):
                        hashed_password = PasswordManager.hash_password(password)
                        hashed_passwords.append(hashed_password)
                        logging.info(f"🔒 Upgraded password for {updated_entry.get('dn', 'unknown')}")
                    else:
                        # Keep existing hashed passwords
                        hashed_passwords.append(password)
                
                attributes["userPassword"] = hashed_passwords
                updated_entry["attributes"] = attributes
            
            upgraded_entries.append(updated_entry)
        
        return upgraded_entries
    
    def _build_ldif_tree(self, entries: List[Dict[str, Any]]) -> LDIFTreeEntry:
        """Build LDAP tree using LDIFTreeEntry for proper LDAP server integration."""
        # Hash plain text passwords if enabled
        if self.hash_plain_passwords:
            entries = self._upgrade_passwords(entries)
        
        # Create root entry
        root = LDIFTreeEntry(self._temp_dir)
        
        # Create entries using a simpler approach similar to MemoryStorage
        # Group entries by their DN for easy lookup
        entries_by_dn = {entry["dn"]: entry["attributes"] for entry in entries}
        created_entries = {"": root}  # Root entry with empty DN
        
        # Process entries in order of DN depth (shortest first)
        sorted_dns = sorted(entries_by_dn.keys(), key=lambda dn: dn.count(','))
        
        for dn_str in sorted_dns:
            attributes = entries_by_dn[dn_str]
            
            try:
                # Parse DN
                dn = distinguishedname.DistinguishedName(stringValue=dn_str)
                
                # Get the RDN (first component)
                dn_components = list(dn.split())
                if not dn_components:
                    continue
                
                rdn = dn_components[0].getText()
                
                # Find parent DN
                if len(dn_components) > 1:
                    # Build parent DN string by joining remaining components
                    parent_components = dn_components[1:]
                    parent_dn_str = ",".join([comp.getText() for comp in parent_components])
                else:
                    parent_dn_str = ""
                
                # Get or create parent entry
                parent_entry = created_entries.get(parent_dn_str)
                if parent_entry is None:
                    # Create missing parent entries
                    parent_entry = self._ensure_parent_exists(parent_dn_str, created_entries, root)
                
                # Create this entry
                child_entry = parent_entry.addChild(rdn, attributes)
                created_entries[dn_str] = child_entry
                logging.debug(f"Created entry: {dn_str}")
                
            except Exception as e:
                logging.error(f"Failed to create entry {dn_str}: {e}")
                import traceback
                traceback.print_exc()
        
        return root
    
    def _ensure_parent_exists(self, parent_dn_str: str, created_entries: Dict[str, LDIFTreeEntry], root: LDIFTreeEntry) -> LDIFTreeEntry:
        """Ensure parent entry exists, creating intermediate entries if needed."""
        if not parent_dn_str or parent_dn_str in created_entries:
            return created_entries.get(parent_dn_str, root)
        
        # Parse parent DN
        parent_dn = distinguishedname.DistinguishedName(stringValue=parent_dn_str)
        parent_components = list(parent_dn.split())
        
        if not parent_components:
            return root
        
        # Get grandparent
        if len(parent_components) > 1:
            grandparent_components = parent_components[1:]
            grandparent_dn_str = ",".join([comp.getText() for comp in grandparent_components])
            grandparent_entry = self._ensure_parent_exists(grandparent_dn_str, created_entries, root)
        else:
            grandparent_entry = root
        
        # Create the parent entry
        rdn = parent_components[0].getText()
        rdn_attr = rdn.split("=")[0] if "=" in rdn else "cn"
        rdn_value = rdn.split("=")[1] if "=" in rdn else rdn
        
        attrs = {
            "objectClass": ["top"],
            rdn_attr: [rdn_value]
        }
        
        # Add appropriate object classes
        if rdn_attr == "dc":
            attrs["objectClass"].append("domain")
        elif rdn_attr == "ou":
            attrs["objectClass"].append("organizationalUnit")
        elif rdn_attr == "cn":
            attrs["objectClass"].append("organizationalRole")
        
        parent_entry = grandparent_entry.addChild(rdn, attrs)
        created_entries[parent_dn_str] = parent_entry
        logging.debug(f"Created intermediate entry: {parent_dn_str}")
        
        return parent_entry
    
    def _update_load_stats(self, data: List[Dict[str, Any]], load_duration: float):
        """Update loading statistics."""
        self.load_stats.update({
            'last_load_time': time.time(),
            'total_entries': len(data),
            'files_loaded': self._temp_files_loaded,
            'merge_conflicts': self._temp_merge_conflicts,
            'load_duration': load_duration
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current storage statistics."""
        return {
            **self.load_stats,
            'json_files': [str(f) for f in self.json_files],
            'merge_strategy': self.merge_strategy,
            'hash_plain_passwords': self.hash_plain_passwords,
            'enable_watcher': self.enable_watcher,
            'file_watching_active': self._observer is not None and self._observer.is_alive()
        }
    
    def add_json_file(self, json_file: Union[str, Path]):
        """Add a new JSON file to the federation."""
        json_file = Path(json_file)
        
        if json_file not in self.json_files:
            self.json_files.append(json_file)
            
            # Setup watching for the new file's directory if auto-reload is enabled
            if self.enable_watcher and self._observer:
                parent_dir = json_file.parent
                self._observer.schedule(self._file_handler, str(parent_dir), recursive=False)
                logging.info(f"Added JSON file to federation: {json_file}")
            
            # Reload data to include the new file
            self._load_json()
    
    def remove_json_file(self, json_file: Union[str, Path]):
        """Remove a JSON file from the federation."""
        json_file = Path(json_file)
        
        if json_file in self.json_files:
            self.json_files.remove(json_file)
            logging.info(f"Removed JSON file from federation: {json_file}")
            
            # Reload data without the removed file
            self._load_json()
    
    def get_root(self) -> LDIFTreeEntry:
        """Get the root entry of the directory tree."""
        return self.root_ref["root"]
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logging.info("File watching stopped")
        
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)


class JSONStorage:
    """
    Legacy JSON storage backend for single file support.
    
    This class maintains backward compatibility while internally using
    FederatedJSONStorage for consistency and enhanced capabilities.
    """
    
    def __init__(self, json_path: str, hash_plain_passwords: bool = True, enable_watcher: bool = True):
        """Initialize JSON storage with single file (legacy interface)."""
        self.json_path = json_path
        
        # Use federated storage internally for consistency
        self._federated = FederatedJSONStorage(
            json_files=[json_path],
            merge_strategy="last_wins",
            hash_plain_passwords=hash_plain_passwords,
            enable_watcher=enable_watcher
        )
        
        # For backward compatibility, also track the original parameters
        self.hash_plain_passwords = hash_plain_passwords
        self.enable_watcher = enable_watcher
        self._temp_dir = self._federated._temp_dir
        self.root_ref = self._federated.root_ref
    
    def _load_json(self):
        """Load JSON data (delegates to federated storage)."""
        self._federated._load_json()
    
    def _upgrade_passwords(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Upgrade plain text passwords to secure hashes (delegates to federated storage)."""
        return self._federated._upgrade_passwords(entries)

    @staticmethod
    def _load_json_entries(path: str) -> List[Dict[str, Any]]:
        """Load and validate JSON entries from file (delegates to federated storage)."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list of entries")
        for e in data:
            if "dn" not in e or "attributes" not in e:
                raise ValueError("Each entry needs 'dn' and 'attributes'")
            if not isinstance(e["attributes"], dict):
                raise ValueError("'attributes' must be a dict of attr -> [values]")
            for k, v in e["attributes"].items():
                if not isinstance(v, list):
                    raise ValueError(f"Attribute '{k}' values must be a list")
        return data

    def _build_ldif_tree(self, entries: List[Dict[str, Any]]) -> LDIFTreeEntry:
        """Build LDAP tree using LDIFTreeEntry (delegates to federated storage)."""
        return self._federated._build_ldif_tree(entries)
    
    def _ensure_parent_exists(self, parent_dn_str: str, created_entries: Dict[str, LDIFTreeEntry], root: LDIFTreeEntry) -> LDIFTreeEntry:
        """Ensure parent entry exists (delegates to federated storage)."""
        return self._federated._ensure_parent_exists(parent_dn_str, created_entries, root)

    def _start_file_watcher(self):
        """Start file system watcher for hot reload (handled by federated storage)."""
        # File watching is already handled by the federated storage
        pass

    class _JSONFileWatcher(FileSystemEventHandler):
        """Legacy file watcher (deprecated, use FederatedFileWatcher)."""
        def __init__(self, path: str, storage: "JSONStorage"):
            super().__init__()
            self.path = path
            self.storage = storage

        def on_modified(self, event):
            if event.src_path.endswith(self.path):
                try:
                    logging.info(f"Reloading JSON entries from {self.path}")
                    self.storage._load_json()
                    logging.info("Reload complete (applied atomically)")
                except Exception as e:
                    logging.error(f"Failed to reload JSON: {e} (keeping old data)")

    def get_root(self) -> LDIFTreeEntry:
        """Get the root entry of the directory tree."""
        return self._federated.get_root()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics (enhanced with legacy compatibility)."""
        stats = self._federated.get_stats()
        # Add legacy fields for backward compatibility
        stats['json_path'] = self.json_path
        return stats

    def cleanup(self) -> None:
        """Clean up temporary directory."""
        self._federated.cleanup()
