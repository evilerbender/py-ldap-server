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


class JSONStorage:
    """
    Storage backend that loads LDAP entries from a JSON file and supports hot reload.
    """
    def __init__(self, json_path: str):
        self.json_path = json_path
        self._temp_dir = tempfile.mkdtemp(prefix="ldap_json_")
        self.root_ref: Dict[str, LDIFTreeEntry] = {"root": None}
        self._load_json()
        self._start_file_watcher()

    def _load_json(self):
        """Load JSON data and build LDAP tree using LDIFTreeEntry."""
        entries = self._load_json_entries(self.json_path)
        root = self._build_ldif_tree(entries)
        self.root_ref["root"] = root
        logging.info(f"Loaded JSON LDAP entries from {self.json_path}")

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
        
        # Sort entries by DN depth to ensure parents are created before children
        sorted_entries = sorted(entries, key=lambda e: len(e["dn"].split(",")))
        
        # Keep track of created entries by DN
        created_entries = {"": root}  # Root entry
        
        for entry_data in sorted_entries:
            dn_str = entry_data["dn"]
            attributes = entry_data["attributes"]
            
            # Parse DN to get components
            dn = distinguishedname.DistinguishedName(stringValue=dn_str)
            
            # Find parent DN
            parent_dn = dn.up() if dn else distinguishedname.DistinguishedName("")
            parent_dn_str = parent_dn.getText() if parent_dn else ""
            
            # Get parent entry (create if needed)
            parent_entry = created_entries.get(parent_dn_str)
            if parent_entry is None:
                # Create intermediate parent if it doesn't exist
                parent_entry = self._create_intermediate_entry(parent_dn_str, created_entries, root)
            
            # Get RDN (relative distinguished name) for this entry
            rdn_components = list(dn.split())
            rdn = rdn_components[0].getText() if rdn_components else ""
            
            try:
                # Add child entry
                child_entry = parent_entry.addChild(rdn, attributes)
                created_entries[dn_str] = child_entry
                logging.debug(f"Created entry: {dn_str}")
            except Exception as e:
                logging.error(f"Failed to create entry {dn_str}: {e}")
        
        return root

    def _create_intermediate_entry(self, dn_str: str, created_entries: Dict[str, LDIFTreeEntry], root: LDIFTreeEntry) -> LDIFTreeEntry:
        """Create intermediate entries if they don't exist."""
        if not dn_str:
            return root
        
        if dn_str in created_entries:
            return created_entries[dn_str]
        
        # Parse DN
        dn = distinguishedname.DistinguishedName(stringValue=dn_str)
        parent_dn = dn.up()
        parent_dn_str = parent_dn.getText() if parent_dn else ""
        
        # Ensure parent exists
        parent_entry = created_entries.get(parent_dn_str, root)
        if parent_entry is None:
            parent_entry = self._create_intermediate_entry(parent_dn_str, created_entries, root)
        
        # Create this intermediate entry with minimal attributes
        rdn_components = list(dn.split())
        rdn = rdn_components[0].getText() if rdn_components else ""
        rdn_attr = rdn.split("=")[0] if "=" in rdn else "cn"
        rdn_value = rdn.split("=")[1] if "=" in rdn else rdn
        
        attrs = {
            "objectClass": ["top"],
            rdn_attr: [rdn_value]
        }
        
        # Add appropriate object classes based on attribute type
        if rdn_attr == "dc":
            attrs["objectClass"].append("domain")
        elif rdn_attr == "ou":
            attrs["objectClass"].append("organizationalUnit")
        elif rdn_attr == "cn":
            attrs["objectClass"].append("organizationalRole")
        
        entry = parent_entry.addChild(rdn, attrs)
        created_entries[dn_str] = entry
        return entry

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
