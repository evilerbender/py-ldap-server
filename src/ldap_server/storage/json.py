"""
Unified JSON-backed LDAP storage backend plugin with federation capabilities and read-only support.

This is a complete rewrite that unifies JSONStorage and FederatedJSONStorage into a single,
clean plugin architecture with read-only mode support for consuming externally managed configs.
"""
import json
import logging
import tempfile
import os
import shutil
import time
import weakref
import fcntl
import errno
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Set, Tuple, Iterator
from collections import OrderedDict
from twisted.internet import defer
from ldaptor.ldiftree import LDIFTreeEntry
from ldaptor.protocols.ldap import distinguishedname
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

from ldap_server.auth.password import PasswordManager


class AtomicJSONWriter:
    """
    Atomic JSON file writer that ensures data integrity during write operations.
    
    Uses temporary files and atomic rename operations to prevent data corruption
    and provides concurrent access protection through file locking.
    """
    
    def __init__(self, target_path: Path, backup_enabled: bool = True, lock_timeout: float = 10.0):
        """
        Initialize atomic JSON writer.
        
        Args:
            target_path: Path to the target JSON file
            backup_enabled: Whether to create backups before writing
            lock_timeout: Maximum time to wait for file lock (seconds)
        """
        self.target_path = Path(target_path)
        self.backup_enabled = backup_enabled
        self.lock_timeout = lock_timeout
        self._lock_file = None
        self._temp_file = None
        
        # Ensure target directory exists
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
    
    def __enter__(self):
        """Context manager entry - acquire lock and prepare for writing."""
        try:
            self._acquire_lock()
            
            # Create backup if enabled and file exists
            if self.backup_enabled and self.target_path.exists():
                self._backup_path = self._create_backup()
                
            self._prepare_temp_file()
            return self
        except Exception:
            self._cleanup()
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - commit or rollback and cleanup."""
        try:
            if exc_type is None:
                self._commit_write()
            else:
                self._rollback_write()
        finally:
            self._cleanup()
    
    def _acquire_lock(self):
        """Acquire exclusive lock on the target file."""
        lock_path = self.target_path.with_suffix(self.target_path.suffix + '.lock')
        
        try:
            self._lock_file = open(lock_path, 'w')
            
            # Try to acquire exclusive lock with timeout
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (IOError, OSError) as e:
                    if e.errno not in (errno.EAGAIN, errno.EACCES):
                        raise
                    
                    if time.time() - start_time > self.lock_timeout:
                        raise TimeoutError(f"Could not acquire lock on {self.target_path} within {self.lock_timeout}s")
                    
                    time.sleep(0.1)
            
            # Write PID to lock file for debugging
            self._lock_file.write(str(os.getpid()))
            self._lock_file.flush()
            
        except Exception as e:
            if self._lock_file:
                try:
                    self._lock_file.close()
                except:
                    pass
                self._lock_file = None
            raise RuntimeError(f"Failed to acquire file lock: {e}")
    
    def _create_backup(self) -> Path:
        """Create timestamped backup of existing file."""
        timestamp = int(time.time())
        backup_path = self.target_path.with_suffix(f"{self.target_path.suffix}.{timestamp}.bak")
        shutil.copy2(self.target_path, backup_path)
        return backup_path
    
    def _prepare_temp_file(self):
        """Prepare temporary file for atomic write."""
        temp_dir = self.target_path.parent
        self._temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            dir=temp_dir,
            prefix=f".{self.target_path.name}.",
            suffix='.tmp',
            delete=False
        )
    
    def _commit_write(self):
        """Commit the write by atomically renaming temp file."""
        if self._temp_file:
            self._temp_file.close()
            # Atomic rename
            os.rename(self._temp_file.name, self.target_path)
            self._temp_file = None
    
    def _rollback_write(self):
        """Rollback failed write by removing temp file."""
        if self._temp_file:
            try:
                self._temp_file.close()
                os.unlink(self._temp_file.name)
            except:
                pass
            self._temp_file = None
    
    def _cleanup(self):
        """Clean up lock file and resources."""
        if self._lock_file:
            try:
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
                # Remove lock file
                lock_path = self.target_path.with_suffix(self.target_path.suffix + '.lock')
                if lock_path.exists():
                    lock_path.unlink()
            except:
                pass
            self._lock_file = None
    
    def write_json(self, data: List[Dict[str, Any]]) -> None:
        """
        Write JSON data to file atomically.
        
        Args:
            data: List of entries to write
            
        Raises:
            RuntimeError: If write operation fails
        """
        if not self._temp_file:
            raise RuntimeError("AtomicJSONWriter not properly initialized")
        
        try:
            json.dump(data, self._temp_file, indent=2, ensure_ascii=False)
            self._temp_file.flush()
            os.fsync(self._temp_file.fileno())
        except Exception as e:
            raise RuntimeError(f"Failed to write JSON data: {e}")


class JSONFileWatcher(FileSystemEventHandler):
    """File system watcher for JSON file changes."""
    
    def __init__(self, storage: 'JSONStorage'):
        """Initialize watcher with reference to storage."""
        super().__init__()
        self.storage_ref = weakref.ref(storage)
        self.last_reload = 0
        self.debounce_time = 0.5
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        storage = self.storage_ref()
        if storage is None:
            return
            
        # Check if any of our watched files was modified
        modified_path = Path(event.src_path)
        
        # Skip temporary files (like atomic write temp files)
        if modified_path.name.endswith('.tmp') or '.tmp.' in modified_path.name:
            return
            
        try:
            # Check if this is one of our watched JSON files
            is_watched_file = any(modified_path.samefile(json_file) for json_file in storage.json_files)
        except (OSError, FileNotFoundError):
            # File may have been deleted (e.g., temporary atomic write files)
            return
            
        if is_watched_file:
            # Debounce rapid changes
            current_time = time.time()
            if current_time - self.last_reload > self.debounce_time:
                self.last_reload = current_time
                try:
                    logging.info(f"Reloading JSON data due to file change: {modified_path}")
                    storage._load_all_files()
                    logging.info("Hot reload completed successfully")
                except Exception as e:
                    logging.error(f"Failed to reload JSON data: {e}")


class JSONStorage:
    """
    Unified JSON storage backend plugin supporting both single and multiple files.
    
    Features:
    - Single or multiple JSON file support
    - Read-only mode for consuming externally managed configs
    - Atomic write operations with file locking
    - Hot reload with file watching
    - Password security with automatic upgrades
    - Lazy loading for large datasets
    - Federation with configurable merge strategies
    - Full plugin architecture compliance
    """
    
    def __init__(
        self,
        json_files: Union[str, List[str], Path, List[Path]],
        read_only: bool = False,
        merge_strategy: str = "last_wins",
        hash_plain_passwords: bool = True,
        enable_file_watching: bool = True,
        debounce_time: float = 0.5,
        enable_lazy_loading: bool = False,
        lazy_cache_max_entries: int = 1000,
        lazy_cache_max_memory_mb: int = 100,
        atomic_write_timeout: float = 10.0,
        enable_backups: bool = True
    ):
        """
        Initialize unified JSON storage backend.
        
        Args:
            json_files: Single file path or list of file paths
            read_only: If True, disable all write operations (for consuming external configs)
            merge_strategy: How to handle DN conflicts in multi-file mode ("last_wins", "first_wins", "error")
            hash_plain_passwords: Automatically hash plain text passwords
            enable_file_watching: Monitor files for changes and hot reload
            debounce_time: Minimum time between file change reloads (seconds)
            enable_lazy_loading: Enable lazy loading for large files
            lazy_cache_max_entries: Maximum entries in lazy loading cache
            lazy_cache_max_memory_mb: Maximum memory for lazy loading cache (MB)
            atomic_write_timeout: Timeout for acquiring file locks during writes (seconds)
            enable_backups: Create backups before write operations
        """
        # Normalize file paths
        if isinstance(json_files, (str, Path)):
            self.json_files = [Path(json_files)]
        else:
            self.json_files = [Path(f) for f in json_files]
        
        # Configuration
        self.read_only = read_only
        self.merge_strategy = merge_strategy
        self.hash_plain_passwords = hash_plain_passwords
        self.enable_file_watching = enable_file_watching
        self.debounce_time = debounce_time
        self.enable_lazy_loading = enable_lazy_loading
        self.lazy_cache_max_entries = lazy_cache_max_entries
        self.lazy_cache_max_memory_mb = lazy_cache_max_memory_mb
        self.atomic_write_timeout = atomic_write_timeout
        self.enable_backups = enable_backups
        
        # Internal state
        self._temp_dir = tempfile.mkdtemp(prefix="ldap_json_unified_")
        self._root_entry = None
        self._file_watcher = None
        self._observer = None
        self._entries_by_file = {}  # Track which entries came from which file
        self._all_entries = []
        
        # Load initial data
        self._load_all_files()
        
        # Start file watching if enabled and not read-only
        if self.enable_file_watching:
            self._start_file_watching()
        
        logging.info(f"JSON Storage initialized: {len(self.json_files)} files, "
                    f"read_only={self.read_only}, merge_strategy={self.merge_strategy}")
    
    def _load_all_files(self):
        """Load and merge data from all JSON files."""
        all_entries = []
        self._entries_by_file = {}
        load_errors = []
        
        for json_file in self.json_files:
            if not json_file.exists():
                logging.warning(f"JSON file does not exist: {json_file}")
                continue
                
            try:
                entries = self._load_json_file(json_file)
                
                # Hash passwords if enabled and not read-only
                if self.hash_plain_passwords and not self.read_only:
                    original_entries = entries.copy()
                    entries = self._upgrade_passwords(entries)
                    
                    # Write back upgraded passwords if any were changed
                    if entries != original_entries:
                        try:
                            with AtomicJSONWriter(
                                target_path=json_file,
                                backup_enabled=self.enable_backups,
                                lock_timeout=self.atomic_write_timeout
                            ) as writer:
                                writer.write_json(entries)
                            logging.info(f"Updated passwords in {json_file}")
                        except Exception as e:
                            logging.error(f"Failed to write back password upgrades to {json_file}: {e}")
                    
                self._entries_by_file[str(json_file)] = entries
                all_entries.extend(entries)
                
                logging.debug(f"Loaded {len(entries)} entries from {json_file}")
                
            except Exception as e:
                logging.error(f"Failed to load JSON file {json_file}: {e}")
                load_errors.append((json_file, e))
                
                # For single file mode, immediately re-raise the error
                if len(self.json_files) == 1:
                    raise
                continue
        
        # If we have multiple files but none loaded successfully, raise the first error
        if not all_entries and load_errors:
            raise load_errors[0][1]
        
        # Merge entries according to strategy
        merged_entries = self._merge_entries(all_entries)
        self._all_entries = merged_entries
        
        # Build LDAP tree
        self._root_entry = self._build_ldap_tree(merged_entries)
        
        logging.info(f"Loaded {len(merged_entries)} total entries from {len(self.json_files)} files")
    
    def _load_json_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load and validate entries from a single JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support both old format (dict with entries list) and new format (direct list)
        if isinstance(data, dict):
            if 'entries' in data:
                entries = data['entries']
            else:
                raise ValueError("JSON dict format must contain 'entries' key")
        elif isinstance(data, list):
            entries = data
        else:
            raise ValueError("JSON root must be a list of entries or dict with 'entries' key")
        
        # Validate entry format
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"Entry {i} must be a dict")
            if 'dn' not in entry:
                raise ValueError(f"Entry {i} missing 'dn' field")
            if 'attributes' not in entry:
                raise ValueError(f"Entry {i} missing 'attributes' field")
            if not isinstance(entry['attributes'], dict):
                raise ValueError(f"Entry {i} 'attributes' must be a dict")
            
            # Validate attribute values are lists
            for attr_name, attr_values in entry['attributes'].items():
                if not isinstance(attr_values, list):
                    raise ValueError(f"Entry {i} attribute '{attr_name}' values must be a list")
        
        return entries
    
    def _upgrade_passwords(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Upgrade plain text passwords to secure hashes."""
        upgraded_entries = []
        
        for entry in entries:
            updated_entry = entry.copy()
            attributes = updated_entry.get('attributes', {}).copy()
            
            if 'userPassword' in attributes:
                passwords = attributes['userPassword']
                hashed_passwords = []
                
                for password in passwords:
                    if not password.startswith('{') and not password.startswith('$'):
                        # Plain text password - hash it
                        hashed_password = PasswordManager.hash_password(password)
                        hashed_passwords.append(hashed_password)
                        logging.info(f"Upgraded password for {updated_entry.get('dn', 'unknown')}")
                    else:
                        # Already hashed
                        hashed_passwords.append(password)
                
                attributes['userPassword'] = hashed_passwords
                updated_entry['attributes'] = attributes
            
            upgraded_entries.append(updated_entry)
        
        return upgraded_entries
    
    def _merge_entries(self, all_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge entries from multiple files according to merge strategy."""
        if len(self.json_files) == 1:
            return all_entries
        
        dn_to_entry = {}
        dn_sources = {}  # Track which file each DN came from
        
        for entry in all_entries:
            dn = entry['dn']
            
            if dn not in dn_to_entry:
                dn_to_entry[dn] = entry
                dn_sources[dn] = [entry]
            else:
                dn_sources[dn].append(entry)
                
                if self.merge_strategy == "first_wins":
                    # Keep first occurrence
                    continue
                elif self.merge_strategy == "last_wins":
                    # Use latest occurrence
                    dn_to_entry[dn] = entry
                elif self.merge_strategy == "error":
                    raise ValueError(f"Duplicate DN found with error merge strategy: {dn}")
                else:
                    raise ValueError(f"Unknown merge strategy: {self.merge_strategy}")
        
        # Log conflicts
        conflicts = {dn: sources for dn, sources in dn_sources.items() if len(sources) > 1}
        if conflicts:
            logging.warning(f"Resolved {len(conflicts)} DN conflicts using {self.merge_strategy} strategy")
        
        return list(dn_to_entry.values())
    
    def _build_ldap_tree(self, entries: List[Dict[str, Any]]) -> LDIFTreeEntry:
        """Build LDAP tree structure from flat entry list."""
        # Create root entry with temp directory path
        root = LDIFTreeEntry(self._temp_dir)
        
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
                continue
        
        return root
    
    def _ensure_parent_exists(self, parent_dn_str: str, created_entries: Dict[str, LDIFTreeEntry], root: LDIFTreeEntry) -> LDIFTreeEntry:
        """Ensure parent entry exists, creating intermediate entries if needed."""
        if not parent_dn_str or parent_dn_str in created_entries:
            return created_entries.get(parent_dn_str, root)
        
        # Parse parent DN
        try:
            parent_dn = distinguishedname.DistinguishedName(stringValue=parent_dn_str)
            parent_components = list(parent_dn.split())
        except Exception as e:
            logging.debug(f"Could not parse parent DN {parent_dn_str}: {e}")
            return root
        
        if not parent_components:
            return root
        
        # Get grandparent
        if len(parent_components) > 1:
            grandparent_components = parent_components[1:]
            grandparent_dn_str = ",".join([comp.getText() for comp in grandparent_components])
        else:
            grandparent_dn_str = ""
        
        # Recursively ensure grandparent exists
        grandparent_entry = self._ensure_parent_exists(grandparent_dn_str, created_entries, root)
        
        # Create parent entry
        parent_rdn = parent_components[0].getText()
        
        # Extract attribute type and value from RDN
        if '=' in parent_rdn:
            rdn_attr, rdn_value = parent_rdn.split('=', 1)
        else:
            rdn_attr, rdn_value = 'cn', parent_rdn
        
        parent_attributes = {
            'objectClass': ['top'],
            rdn_attr: [rdn_value]
        }
        
        # Add appropriate object classes
        if rdn_attr == 'dc':
            parent_attributes['objectClass'].append('domain')
        elif rdn_attr == 'ou':
            parent_attributes['objectClass'].append('organizationalUnit')
        elif rdn_attr == 'cn':
            parent_attributes['objectClass'].append('organizationalRole')
        
        parent_entry = grandparent_entry.addChild(parent_rdn, parent_attributes)
        created_entries[parent_dn_str] = parent_entry
        logging.debug(f"Created intermediate parent entry: {parent_dn_str}")
        
        return parent_entry
    
    def _start_file_watching(self):
        """Start file system watcher for hot reload."""
        if self._observer is not None:
            return
        
        try:
            self._file_watcher = JSONFileWatcher(self)
            self._observer = Observer()
            
            # Watch directories containing our JSON files
            watched_dirs = set()
            for json_file in self.json_files:
                if json_file.exists():
                    watch_dir = json_file.parent
                    if watch_dir not in watched_dirs:
                        self._observer.schedule(self._file_watcher, str(watch_dir), recursive=False)
                        watched_dirs.add(watch_dir)
            
            self._observer.start()
            logging.info(f"Started file watching for {len(watched_dirs)} directories")
            
        except Exception as e:
            logging.error(f"Failed to start file watcher: {e}")
            self._file_watcher = None
            self._observer = None
    
    def _stop_file_watching(self):
        """Stop file system watcher."""
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=1.0)
            except Exception as e:
                logging.error(f"Error stopping file watcher: {e}")
            finally:
                self._observer = None
                self._file_watcher = None
    
    def _find_target_file(self, dn: str) -> Path:
        """Determine which file should contain the given DN."""
        if len(self.json_files) == 1:
            return self.json_files[0]
        
        # For multi-file mode, use simple hashing or explicit routing
        # This is a simple implementation - could be made more sophisticated
        dn_lower = dn.lower()
        
        # Route based on DN patterns
        if 'ou=users' in dn_lower or 'uid=' in dn_lower:
            # User entries
            for json_file in self.json_files:
                if 'user' in str(json_file).lower():
                    return json_file
        elif 'ou=groups' in dn_lower or 'cn=' in dn_lower:
            # Group entries
            for json_file in self.json_files:
                if 'group' in str(json_file).lower():
                    return json_file
        
        # Default to first file
        return self.json_files[0]
    
    # Plugin Interface Methods
    
    def get_root(self) -> LDIFTreeEntry:
        """Get the root entry of the LDAP directory tree."""
        return self._root_entry
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._stop_file_watching()
        
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)
        
        logging.info("JSON storage cleaned up")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            'total_entries': len(self._all_entries),
            'files_count': len(self.json_files),
            'files': [str(f) for f in self.json_files],
            'read_only': self.read_only,
            'merge_strategy': self.merge_strategy,
            'file_watching_enabled': self.enable_file_watching,
            'lazy_loading_enabled': self.enable_lazy_loading,
            'entries_by_file': {k: len(v) for k, v in self._entries_by_file.items()}
        }
    
    # Write Operations (disabled in read-only mode)
    
    def add_entry(self, dn: str, attributes: Dict[str, List[str]], target_file: Optional[str] = None) -> bool:
        """Add a new LDAP entry."""
        if self.read_only:
            logging.warning("Add operation attempted on read-only JSON storage")
            return False
        
        try:
            # Determine target file
            if target_file:
                file_path = Path(target_file)
            else:
                file_path = self._find_target_file(dn)
            
            # Load current entries from target file
            current_entries = self._entries_by_file.get(str(file_path), [])
            
            # Check for duplicate DN
            for entry in current_entries:
                if entry['dn'] == dn:
                    logging.warning(f"Entry with DN {dn} already exists")
                    return False
            
            # Create new entry
            new_entry = {
                'dn': dn,
                'attributes': attributes
            }
            
            # Add to entries list
            updated_entries = current_entries + [new_entry]
            
            # Write atomically
            with AtomicJSONWriter(file_path, self.enable_backups, self.atomic_write_timeout) as writer:
                writer.write_json(updated_entries)
            
            # Reload all data
            self._load_all_files()
            
            logging.info(f"Added entry {dn} to {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to add entry {dn}: {e}")
            return False
    
    def modify_entry(self, dn: str, new_attributes: Dict[str, List[str]], target_file: Optional[str] = None) -> bool:
        """Modify an existing LDAP entry."""
        if self.read_only:
            logging.warning("Modify operation attempted on read-only JSON storage")
            return False
        
        try:
            # Find entry in files
            for file_path, entries in self._entries_by_file.items():
                for i, entry in enumerate(entries):
                    if entry['dn'] == dn:
                        # Update entry
                        entries[i]['attributes'] = new_attributes
                        
                        # Write atomically
                        with AtomicJSONWriter(Path(file_path), self.enable_backups, self.atomic_write_timeout) as writer:
                            writer.write_json(entries)
                        
                        # Reload all data
                        self._load_all_files()
                        
                        logging.info(f"Modified entry {dn} in {file_path}")
                        return True
            
            logging.warning(f"Entry {dn} not found for modification")
            return False
            
        except Exception as e:
            logging.error(f"Failed to modify entry {dn}: {e}")
            return False
    
    def delete_entry(self, dn: str) -> bool:
        """Delete an LDAP entry."""
        if self.read_only:
            logging.warning("Delete operation attempted on read-only JSON storage")
            return False
        
        try:
            # Find and remove entry from files
            for file_path, entries in self._entries_by_file.items():
                for i, entry in enumerate(entries):
                    if entry['dn'] == dn:
                        # Remove entry
                        updated_entries = entries[:i] + entries[i+1:]
                        
                        # Write atomically
                        with AtomicJSONWriter(Path(file_path), self.enable_backups, self.atomic_write_timeout) as writer:
                            writer.write_json(updated_entries)
                        
                        # Reload all data
                        self._load_all_files()
                        
                        logging.info(f"Deleted entry {dn} from {file_path}")
                        return True
            
            logging.warning(f"Entry {dn} not found for deletion")
            return False
            
        except Exception as e:
            logging.error(f"Failed to delete entry {dn}: {e}")
            return False
    
    def bulk_write_entries(self, entries: List[Dict[str, Any]], target_file: Optional[str] = None) -> bool:
        """Write multiple entries in a single atomic operation."""
        if self.read_only:
            logging.warning("Bulk write operation attempted on read-only JSON storage")
            return False
        
        try:
            # Validate all entries first
            for i, entry in enumerate(entries):
                if 'dn' not in entry or 'attributes' not in entry:
                    logging.error(f"Invalid entry format at index {i}")
                    return False
            
            # Determine target file
            if target_file:
                file_path = Path(target_file)
            else:
                file_path = self.json_files[0]  # Default to first file
            
            # Load current entries
            current_entries = self._entries_by_file.get(str(file_path), [])
            
            # Merge with new entries (replace if DN exists)
            entry_map = {entry['dn']: entry for entry in current_entries}
            for entry in entries:
                entry_map[entry['dn']] = entry
            
            updated_entries = list(entry_map.values())
            
            # Write atomically
            with AtomicJSONWriter(file_path, self.enable_backups, self.atomic_write_timeout) as writer:
                writer.write_json(updated_entries)
            
            # Reload all data
            self._load_all_files()
            
            logging.info(f"Bulk wrote {len(entries)} entries to {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to bulk write entries: {e}")
            return False


# For compatibility with existing code (can be removed later)
FederatedJSONStorage = JSONStorage
