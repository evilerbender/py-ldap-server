"""
JSON-backed LDAP storage backend with hot reload support.
"""
import json
import logging
import tempfile
import os
import shutil
from typing import Dict, List, Any
from twisted.internet import defer
from ldaptor.ldiftree import LDIFTreeEntry
from ldaptor.protocols.ldap import distinguishedname
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

from ldap_server.auth.password import PasswordManager


class JSONStorage:
    """
    Storage backend that loads LDAP entries from a JSON file and supports hot reload.
    """
    def __init__(self, json_path: str, hash_plain_passwords: bool = True, enable_watcher: bool = True):
        self.json_path = json_path
        self.hash_plain_passwords = hash_plain_passwords
        self.enable_watcher = enable_watcher
        self._temp_dir = tempfile.mkdtemp(prefix="ldap_json_")
        self.root_ref: Dict[str, LDIFTreeEntry] = {"root": None}
        self._load_json()
        if self.enable_watcher:
            self._start_file_watcher()

    def _load_json(self):
        """Load JSON data and build LDAP tree using LDIFTreeEntry."""
        entries = self._load_json_entries(self.json_path)
        
        # Hash plain text passwords if enabled
        if self.hash_plain_passwords:
            entries = self._upgrade_passwords(entries)
        
        root = self._build_ldif_tree(entries)
        self.root_ref["root"] = root
        logging.info(f"Loaded JSON LDAP entries from {self.json_path}")
    
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

    @staticmethod
    def _load_json_entries(path: str) -> List[Dict[str, Any]]:
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

    def _build_ldif_tree(self, entries: List[Dict[str, Any]]) -> LDIFTreeEntry:
        """Build LDAP tree using LDIFTreeEntry for proper LDAP server integration."""
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
                    # Build parent DN
                    parent_components = dn_components[1:]
                    parent_dn = distinguishedname.DistinguishedName()
                    for comp in reversed(parent_components):
                        parent_dn = parent_dn.child(comp)
                    parent_dn_str = parent_dn.getText()
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
            grandparent_dn = distinguishedname.DistinguishedName()
            for comp in reversed(grandparent_components):
                grandparent_dn = grandparent_dn.child(comp)
            grandparent_dn_str = grandparent_dn.getText()
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

    def _start_file_watcher(self):
        """Start file system watcher for hot reload."""
        event_handler = self._JSONFileWatcher(self.json_path, self)
        observer = Observer()
        observer.schedule(event_handler, path=".", recursive=False)
        thread = threading.Thread(target=observer.start, daemon=True)
        thread.start()

    class _JSONFileWatcher(FileSystemEventHandler):
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
        return self.root_ref["root"]

    def cleanup(self) -> None:
        """Clean up temporary directory."""
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)
