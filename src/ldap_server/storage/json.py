"""
JSON-backed LDAP storage backend with hot reload support, federation capabilities, and lazy loading.
"""
import json
import logging
import tempfile
import os
import shutil
import time
import weakref
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


class LazyEntryReference:
    """Reference to a JSON entry that can be loaded on-demand."""
    
    def __init__(self, dn: str, file_path: Path, entry_index: int, indexed_file: 'IndexedJSONFile'):
        self.dn = dn
        self.file_path = file_path
        self.entry_index = entry_index
        self.indexed_file = indexed_file
        self._loaded_attributes: Optional[Dict[str, List[str]]] = None
        self._load_time: Optional[float] = None
    
    def is_loaded(self) -> bool:
        """Check if attributes are loaded in memory."""
        return self._loaded_attributes is not None
    
    def get_attributes(self, cache: 'LazyEntryCache' = None) -> Dict[str, List[str]]:
        """Get entry attributes, loading from file if necessary."""
        if self._loaded_attributes is None:
            self._load_from_file(cache)
        return self._loaded_attributes
    
    def _load_from_file(self, cache: 'LazyEntryCache' = None):
        """Load entry attributes from JSON file."""
        try:
            entry_data = self.indexed_file.load_entry_by_index(self.entry_index)
            
            if not entry_data or 'attributes' not in entry_data:
                raise ValueError(f"Invalid entry format for DN {self.dn}")
            
            self._loaded_attributes = entry_data['attributes']
            self._load_time = time.time()
            
            # Add to cache if provided
            if cache:
                cache.put(self.dn, self)
            
            logging.debug(f"Lazy loaded entry: {self.dn}")
            
        except Exception as e:
            logging.error(f"Failed to lazy load entry {self.dn}: {e}")
            # Fallback to empty attributes to prevent crashes
            self._loaded_attributes = {}
    
    def unload(self):
        """Unload attributes to free memory."""
        self._loaded_attributes = None
        self._load_time = None
    
    def get_memory_size(self) -> int:
        """Estimate memory usage of loaded attributes."""
        if not self.is_loaded():
            return 0
        
        # Rough estimate of memory usage
        size = 0
        for key, values in self._loaded_attributes.items():
            size += len(key) * 2  # Unicode string overhead
            for value in values:
                size += len(str(value)) * 2
        return size


class LazyEntryCache:
    """LRU cache for lazy-loaded entries with memory limits."""
    
    def __init__(self, max_entries: int = 1000, max_memory_mb: int = 100):
        self.max_entries = max_entries
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: OrderedDict[str, LazyEntryReference] = OrderedDict()
        self._lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_evictions': 0
        }
    
    def get(self, dn: str) -> Optional[LazyEntryReference]:
        """Get entry from cache, moving to end (most recently used)."""
        with self._lock:
            if dn in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(dn)
                self.stats['hits'] += 1
                return self._cache[dn]
            
            self.stats['misses'] += 1
            return None
    
    def put(self, dn: str, entry: LazyEntryReference):
        """Add entry to cache, evicting old entries if necessary."""
        with self._lock:
            # Remove if already exists
            if dn in self._cache:
                del self._cache[dn]
            
            # Add to end
            self._cache[dn] = entry
            
            # Evict entries if over limits
            self._evict_if_needed()
    
    def _evict_if_needed(self):
        """Evict entries if cache exceeds size or memory limits."""
        # Check entry count limit
        while len(self._cache) > self.max_entries:
            self._evict_oldest()
            self.stats['evictions'] += 1
        
        # Check memory limit
        while self._get_total_memory() > self.max_memory_bytes and self._cache:
            self._evict_oldest()
            self.stats['memory_evictions'] += 1
    
    def _evict_oldest(self):
        """Evict the least recently used entry."""
        if self._cache:
            dn, entry = self._cache.popitem(last=False)
            entry.unload()
    
    def _get_total_memory(self) -> int:
        """Calculate total memory usage of cached entries."""
        return sum(entry.get_memory_size() for entry in self._cache.values())
    
    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            for entry in self._cache.values():
                entry.unload()
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            hit_rate = self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0
            return {
                **self.stats,
                'cached_entries': len(self._cache),
                'memory_usage_bytes': self._get_total_memory(),
                'memory_usage_mb': self._get_total_memory() / (1024 * 1024),
                'hit_rate': hit_rate
            }


class IndexedJSONFile:
    """Indexed JSON file reader for efficient lazy loading."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.entry_index: Dict[str, Tuple[int, int]] = {}  # dn -> (offset, length)
        self.total_entries = 0
        self._index_built = False
        self._lock = threading.RLock()
    
    def build_index(self):
        """Build an index of entry positions in the JSON file."""
        with self._lock:
            if self._index_built:
                return
            
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if not isinstance(data, list):
                    raise ValueError("JSON root must be a list of entries")
                
                # For now, we'll use a simple approach since JSON doesn't support
                # streaming parsing with position tracking easily.
                # We'll store the entries and calculate their serialized positions.
                self.entry_index.clear()
                
                for i, entry in enumerate(data):
                    if not isinstance(entry, dict) or 'dn' not in entry:
                        continue
                    
                    dn = entry['dn']
                    # For JSON, we'll simulate offsets using entry indices
                    # In a real implementation, we might use a different format
                    self.entry_index[dn] = (i, 1)  # (entry_index, length=1)
                
                self.total_entries = len(self.entry_index)
                self._index_built = True
                
                logging.debug(f"Built index for {self.file_path}: {self.total_entries} entries")
                
            except Exception as e:
                logging.error(f"Failed to build index for {self.file_path}: {e}")
                raise
    
    def get_entry_reference(self, dn: str) -> Optional[LazyEntryReference]:
        """Get a lazy reference to an entry by DN."""
        if not self._index_built:
            self.build_index()
        
        if dn not in self.entry_index:
            return None
        
        entry_index, length = self.entry_index[dn]
        # For JSON files, we use entry index as offset
        return LazyEntryReference(dn, self.file_path, entry_index, self)
    
    def get_all_dns(self) -> Set[str]:
        """Get all DNs in the file."""
        if not self._index_built:
            self.build_index()
        return set(self.entry_index.keys())
    
    def load_entry_by_index(self, entry_index: int) -> Optional[Dict[str, Any]]:
        """Load a specific entry by its index in the JSON array."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 0 <= entry_index < len(data):
                return data[entry_index]
            
            return None
            
        except Exception as e:
            logging.error(f"Failed to load entry at index {entry_index}: {e}")
            return None


class LazyLDIFTreeEntry(LDIFTreeEntry):
    """Extended LDIFTreeEntry that supports lazy loading of attributes."""
    
    def __init__(self, path: str, dn: str = "", lazy_ref: Optional[LazyEntryReference] = None):
        # Initialize with minimal attributes first
        self._lazy_ref = lazy_ref
        self._cache = None  # Will be set by parent storage
        
        # Ensure path ends with .dir as required by LDIFTreeEntry
        if not path.endswith(".dir"):
            path = path + ".dir"
        
        # If we have a lazy reference, use empty attributes initially
        if lazy_ref:
            initial_attrs = {}
        else:
            initial_attrs = None
        
        super().__init__(path, dn)
        
        # Override the attributes with empty dict if lazy loading
        if lazy_ref:
            self._attributes = {}
            self._lazy_loaded = False
        else:
            self._lazy_loaded = True
    
    def set_cache(self, cache: LazyEntryCache):
        """Set the cache for lazy loading."""
        self._cache = cache
    
    def _get_dn_text(self) -> str:
        """Get DN as text string, handling both string and DistinguishedName objects."""
        if hasattr(self.dn, 'getText'):
            return self.dn.getText()
        return str(self.dn)
    
    def _ensure_loaded(self):
        """Ensure attributes are loaded from lazy reference if needed."""
        if not self._lazy_loaded and self._lazy_ref:
            try:
                attrs = self._lazy_ref.get_attributes(self._cache)
                # Convert to the format expected by LDIFTreeEntry
                for key, values in attrs.items():
                    self._attributes[key] = [str(v).encode('utf-8') for v in values]
                self._lazy_loaded = True
                logging.debug(f"Lazy loaded attributes for {self._get_dn_text()}")
            except Exception as e:
                logging.error(f"Failed to lazy load attributes for {self._get_dn_text()}: {e}")
                self._lazy_loaded = True  # Prevent infinite retry
    
    def get(self, key: str, default=None):
        """Get attribute value, loading lazily if needed."""
        self._ensure_loaded()
        return super().get(key, default)
    
    def __getitem__(self, key):
        """Get attribute value, loading lazily if needed."""
        self._ensure_loaded()
        return super().__getitem__(key)
    
    def __contains__(self, key):
        """Check if attribute exists, loading lazily if needed."""
        self._ensure_loaded()
        return super().__contains__(key)
    
    def keys(self):
        """Get attribute keys, loading lazily if needed."""
        self._ensure_loaded()
        return super().keys()
    
    def items(self):
        """Get attribute items, loading lazily if needed."""
        self._ensure_loaded()
        return super().items()
    
    def values(self):
        """Get attribute values, loading lazily if needed."""
        self._ensure_loaded()
        return super().values()
    
    def is_lazy_loaded(self) -> bool:
        """Check if this entry uses lazy loading."""
        return self._lazy_ref is not None
    
    def is_loaded(self) -> bool:
        """Check if lazy attributes have been loaded."""
        return self._lazy_loaded
    
    def unload_lazy_attributes(self):
        """Unload lazy attributes to save memory."""
        if self._lazy_ref and self._lazy_loaded:
            self._attributes.clear()
            self._lazy_loaded = False
            if self._lazy_ref:
                self._lazy_ref.unload()
            logging.debug(f"Unloaded lazy attributes for {self._get_dn_text()}")


class PaginatedSearchResult:
    """Paginated search result for lazy loading."""
    
    def __init__(self, entries: List[LDIFTreeEntry], page_size: int = 100, total_count: Optional[int] = None):
        self.entries = entries
        self.page_size = page_size
        self.total_count = total_count or len(entries)
        self.current_page = 0
        self.total_pages = (self.total_count + page_size - 1) // page_size
    
    def get_page(self, page_num: int) -> List[LDIFTreeEntry]:
        """Get a specific page of results."""
        if page_num < 0 or page_num >= self.total_pages:
            return []
        
        start_idx = page_num * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.entries))
        
        return self.entries[start_idx:end_idx]
    
    def get_next_page(self) -> List[LDIFTreeEntry]:
        """Get the next page of results."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            return self.get_page(self.current_page)
        return []
    
    def get_previous_page(self) -> List[LDIFTreeEntry]:
        """Get the previous page of results."""
        if self.current_page > 0:
            self.current_page -= 1
            return self.get_page(self.current_page)
        return []
    
    def has_next_page(self) -> bool:
        """Check if there's a next page."""
        return self.current_page < self.total_pages - 1
    
    def has_previous_page(self) -> bool:
        """Check if there's a previous page."""
        return self.current_page > 0
    
    def get_page_info(self) -> Dict[str, Any]:
        """Get pagination information."""
        return {
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'page_size': self.page_size,
            'total_count': self.total_count,
            'has_next': self.has_next_page(),
            'has_previous': self.has_previous_page()
        }


class LazySearchIterator:
    """Iterator for lazy searching through large datasets."""
    
    def __init__(self, storage: 'FederatedJSONStorage', base_dn: str = "", 
                 filter_func: Optional[callable] = None, page_size: int = 100):
        self.storage = storage
        self.base_dn = base_dn
        self.filter_func = filter_func
        self.page_size = page_size
        self.current_position = 0
        self._all_dns = None
        self._loaded_count = 0
    
    def _get_all_dns(self) -> List[str]:
        """Get all DNs that match the base DN."""
        if self._all_dns is None:
            all_dns = set()
            
            # Collect DNs from all indexed files
            for indexed_file in self.storage._indexed_files.values():
                file_dns = indexed_file.get_all_dns()
                all_dns.update(file_dns)
            
            # Filter by base DN if specified
            if self.base_dn:
                filtered_dns = []
                for dn in all_dns:
                    if dn.endswith(self.base_dn) or dn == self.base_dn:
                        filtered_dns.append(dn)
                self._all_dns = sorted(filtered_dns)
            else:
                self._all_dns = sorted(all_dns)
        
        return self._all_dns
    
    def __iter__(self):
        return self
    
    def __next__(self) -> LDIFTreeEntry:
        """Get the next matching entry."""
        all_dns = self._get_all_dns()
        
        while self.current_position < len(all_dns):
            dn = all_dns[self.current_position]
            self.current_position += 1
            
            try:
                # Get lazy reference and load the entry
                lazy_ref = self.storage._get_lazy_reference_for_dn(dn)
                if lazy_ref:
                    # Create a temporary LazyLDIFTreeEntry
                    temp_entry = LazyLDIFTreeEntry(
                        self.storage._temp_dir, 
                        dn, 
                        lazy_ref
                    )
                    temp_entry.set_cache(self.storage._lazy_cache)
                    
                    # Apply filter if provided
                    if self.filter_func is None or self.filter_func(temp_entry):
                        self._loaded_count += 1
                        return temp_entry
            
            except Exception as e:
                logging.error(f"Error loading entry {dn}: {e}")
                continue
        
        raise StopIteration
    
    def get_page(self, page_num: int = 0) -> PaginatedSearchResult:
        """Get a specific page of results."""
        all_dns = self._get_all_dns()
        start_idx = page_num * self.page_size
        end_idx = min(start_idx + self.page_size, len(all_dns))
        
        page_entries = []
        for i in range(start_idx, end_idx):
            if i < len(all_dns):
                dn = all_dns[i]
                try:
                    lazy_ref = self.storage._get_lazy_reference_for_dn(dn)
                    if lazy_ref:
                        temp_entry = LazyLDIFTreeEntry(
                            self.storage._temp_dir,
                            dn,
                            lazy_ref
                        )
                        temp_entry.set_cache(self.storage._lazy_cache)
                        
                        if self.filter_func is None or self.filter_func(temp_entry):
                            page_entries.append(temp_entry)
                
                except Exception as e:
                    logging.error(f"Error loading entry {dn}: {e}")
                    continue
        
        return PaginatedSearchResult(page_entries, self.page_size, len(all_dns))
    
    def get_total_count(self) -> int:
        """Get total count of matching entries."""
        return len(self._get_all_dns())


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
                 debounce_time: float = 0.5,
                 enable_lazy_loading: bool = False,
                 lazy_cache_max_entries: int = 1000,
                 lazy_cache_max_memory_mb: int = 100):
        """
        Initialize federated JSON storage.
        
        Args:
            json_files: Single file path or list of JSON file paths
            merge_strategy: How to handle conflicts ("last_wins", "first_wins", "error")
            hash_plain_passwords: Whether to hash plain text passwords
            enable_watcher: Enable automatic file watching and reloading
            debounce_time: Debounce time for file change detection
            enable_lazy_loading: Enable lazy loading for large files
            lazy_cache_max_entries: Maximum number of entries in lazy loading cache
            lazy_cache_max_memory_mb: Maximum memory usage for lazy loading cache (MB)
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
        
        # Lazy loading configuration
        self.enable_lazy_loading = enable_lazy_loading
        self.lazy_cache_max_entries = lazy_cache_max_entries
        self.lazy_cache_max_memory_mb = lazy_cache_max_memory_mb
        
        # Storage state
        self._temp_dir = tempfile.mkdtemp(prefix="ldap_federated_json_")
        self.root_ref: Dict[str, LDIFTreeEntry] = {"root": None}
        self._lock = threading.RLock()
        self._observer = None
        self._file_handler = None
        
        # Lazy loading components
        self._indexed_files: Dict[Path, IndexedJSONFile] = {}
        self._lazy_cache: Optional[LazyEntryCache] = None
        
        if self.enable_lazy_loading:
            self._lazy_cache = LazyEntryCache(
                max_entries=self.lazy_cache_max_entries,
                max_memory_mb=self.lazy_cache_max_memory_mb
            )
            logging.info(f"Lazy loading enabled with cache: {lazy_cache_max_entries} entries, {lazy_cache_max_memory_mb}MB")
        
        # Statistics
        self.load_stats = {
            'last_load_time': None,
            'total_entries': 0,
            'files_loaded': 0,
            'merge_conflicts': 0,
            'load_duration': 0.0,
            'lazy_loading_enabled': self.enable_lazy_loading
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
                
                if self.enable_lazy_loading:
                    # Use lazy loading approach
                    root = self._load_with_lazy_loading()
                else:
                    # Use traditional full loading approach
                    merged_data = self._load_and_merge_files()
                    root = self._build_ldif_tree(merged_data)
                
                self.root_ref["root"] = root
                
                # Update statistics
                load_duration = time.time() - start_time
                if not self.enable_lazy_loading:
                    self._update_load_stats(merged_data, load_duration)
                else:
                    self._update_lazy_load_stats(load_duration)
                
                logging.info(f"Federation load completed: {self.load_stats['total_entries']} entries "
                           f"from {self.load_stats['files_loaded']} files in {load_duration:.3f}s "
                           f"{'(lazy loading)' if self.enable_lazy_loading else ''}")
                
            except Exception as e:
                logging.error(f"Failed to reload JSON federation: {e}")
                raise
    
    def _load_with_lazy_loading(self) -> LDIFTreeEntry:
        """Load JSON files using lazy loading approach."""
        logging.info("Using lazy loading approach")
        
        # Clear existing indexed files
        self._indexed_files.clear()
        if self._lazy_cache:
            self._lazy_cache.clear()
        
        # Build indexes for all files
        all_dns = set()
        files_loaded = 0
        
        for json_file in self.json_files:
            try:
                if not json_file.exists():
                    logging.warning(f"JSON file not found: {json_file}")
                    continue
                
                indexed_file = IndexedJSONFile(json_file)
                indexed_file.build_index()
                self._indexed_files[json_file] = indexed_file
                
                file_dns = indexed_file.get_all_dns()
                all_dns.update(file_dns)
                files_loaded += 1
                
                logging.debug(f"Indexed {len(file_dns)} entries from {json_file}")
                
            except Exception as e:
                logging.error(f"Error indexing file {json_file}: {e}")
                if len(self.json_files) == 1:
                    raise
        
        if files_loaded == 0:
            raise ValueError("No JSON files could be loaded")
        
        # Create directory tree with lazy entries
        root = self._build_lazy_ldif_tree(all_dns)
        
        # Store stats for later use
        self._temp_files_loaded = files_loaded
        self._temp_total_entries = len(all_dns)
        
        return root
    
    def _build_lazy_ldif_tree(self, all_dns: Set[str]) -> LDIFTreeEntry:
        """Build LDAP tree with lazy-loaded entries."""
        # Create root entry
        root = LDIFTreeEntry(self._temp_dir)
        created_entries = {"": root}  # Root entry with empty DN
        
        # Process entries in order of DN depth (shortest first)
        sorted_dns = sorted(all_dns, key=lambda dn: dn.count(','))
        
        for dn_str in sorted_dns:
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
                    parent_components = dn_components[1:]
                    parent_dn_str = ",".join([comp.getText() for comp in parent_components])
                else:
                    parent_dn_str = ""
                
                # Get or create parent entry
                parent_entry = created_entries.get(parent_dn_str)
                if parent_entry is None:
                    parent_entry = self._ensure_parent_exists(parent_dn_str, created_entries, root)
                
                # Get lazy reference for this entry
                lazy_ref = self._get_lazy_reference_for_dn(dn_str)
                
                # Create lazy LDIF entry
                if lazy_ref:
                    # Create with minimal initial attributes for lazy loading
                    temp_attrs = self._get_minimal_attributes_for_dn(dn_str)
                    child_entry = parent_entry.addChild(rdn, temp_attrs)
                    
                    # Convert to lazy entry
                    if isinstance(child_entry, LDIFTreeEntry):
                        # Replace with lazy version
                        lazy_entry = LazyLDIFTreeEntry(child_entry.path, dn_str, lazy_ref)
                        lazy_entry.set_cache(self._lazy_cache)
                        
                        # Update parent's child reference
                        parent_entry._children[rdn] = lazy_entry
                        created_entries[dn_str] = lazy_entry
                else:
                    # Fallback for entries not found in any indexed file
                    temp_attrs = {"objectClass": ["top"]}
                    child_entry = parent_entry.addChild(rdn, temp_attrs)
                    created_entries[dn_str] = child_entry
                
                logging.debug(f"Created lazy entry: {dn_str}")
                
            except Exception as e:
                logging.error(f"Failed to create lazy entry {dn_str}: {e}")
                import traceback
                traceback.print_exc()
        
        return root
    
    def _get_lazy_reference_for_dn(self, dn: str) -> Optional[LazyEntryReference]:
        """Get a lazy reference for a DN from indexed files."""
        # Use merge strategy to determine which file to use
        if self.merge_strategy == "last_wins":
            # Check files in reverse order
            for json_file in reversed(self.json_files):
                if json_file in self._indexed_files:
                    lazy_ref = self._indexed_files[json_file].get_entry_reference(dn)
                    if lazy_ref:
                        return lazy_ref
        elif self.merge_strategy == "first_wins":
            # Check files in order
            for json_file in self.json_files:
                if json_file in self._indexed_files:
                    lazy_ref = self._indexed_files[json_file].get_entry_reference(dn)
                    if lazy_ref:
                        return lazy_ref
        else:
            # For "error" strategy, just use first found
            for json_file in self.json_files:
                if json_file in self._indexed_files:
                    lazy_ref = self._indexed_files[json_file].get_entry_reference(dn)
                    if lazy_ref:
                        return lazy_ref
        
        return None
    
    def _get_minimal_attributes_for_dn(self, dn: str) -> Dict[str, List[str]]:
        """Get minimal attributes needed for DN parsing."""
        # Parse DN to get RDN attribute
        try:
            parsed_dn = distinguishedname.DistinguishedName(stringValue=dn)
            dn_components = list(parsed_dn.split())
            if dn_components:
                rdn = dn_components[0].getText()
                if "=" in rdn:
                    rdn_attr = rdn.split("=")[0]
                    rdn_value = rdn.split("=", 1)[1]
                    
                    attrs = {
                        "objectClass": ["top"],
                        rdn_attr: [rdn_value]
                    }
                    
                    # Add appropriate object classes based on attribute
                    if rdn_attr == "dc":
                        attrs["objectClass"].append("domain")
                    elif rdn_attr == "ou":
                        attrs["objectClass"].append("organizationalUnit")
                    elif rdn_attr == "cn":
                        attrs["objectClass"].append("person")
                    elif rdn_attr == "uid":
                        attrs["objectClass"].extend(["person", "organizationalPerson", "inetOrgPerson"])
                    
                    return attrs
        except Exception as e:
            logging.debug(f"Could not parse DN {dn}: {e}")
        
        # Fallback
        return {"objectClass": ["top"]}
    
    def _update_lazy_load_stats(self, load_duration: float):
        """Update loading statistics for lazy loading."""
        self.load_stats.update({
            'last_load_time': time.time(),
            'total_entries': self._temp_total_entries,
            'files_loaded': self._temp_files_loaded,
            'merge_conflicts': 0,  # No conflicts calculated in lazy mode
            'load_duration': load_duration,
            'lazy_loading_enabled': True
        })
    
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
            grandparent_entry = self._ensure_parent_exists(grandparent_dn_str, created_entries, root)
        else:
            grandparent_entry = root
        
        # Create the parent entry only if it doesn't exist
        if parent_dn_str not in created_entries:
            rdn = parent_components[0].getText()
            rdn_attr = rdn.split("=")[0] if "=" in rdn else "cn"
            rdn_value = rdn.split("=")[1] if "=" in rdn else rdn
            
            attrs = {
                rdn_attr: [rdn_value],
                "objectClass": ["top"]
            }
            
            # Add appropriate object classes
            if rdn_attr == "dc":
                attrs["objectClass"].append("domain")
            elif rdn_attr == "ou":
                attrs["objectClass"].append("organizationalUnit")
            elif rdn_attr == "cn":
                attrs["objectClass"].append("organizationalRole")
            
            try:
                parent_entry = grandparent_entry.addChild(rdn, attrs)
                created_entries[parent_dn_str] = parent_entry
                logging.debug(f"Created intermediate entry: {parent_dn_str}")
            except Exception as e:
                # If entry already exists in the tree, try to find it
                logging.debug(f"Failed to create parent {parent_dn_str}: {e}")
                if hasattr(grandparent_entry, '_children') and rdn in grandparent_entry._children:
                    parent_entry = grandparent_entry._children[rdn]
                    created_entries[parent_dn_str] = parent_entry
                    logging.debug(f"Using existing intermediate entry: {parent_dn_str}")
                else:
                    # Fallback to grandparent
                    return grandparent_entry
        
        return created_entries[parent_dn_str]
    
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
        base_stats = {
            **self.load_stats,
            'json_files': [str(f) for f in self.json_files],
            'merge_strategy': self.merge_strategy,
            'hash_plain_passwords': self.hash_plain_passwords,
            'enable_watcher': self.enable_watcher,
            'file_watching_active': self._observer is not None and self._observer.is_alive()
        }
        
        # Add lazy loading statistics if enabled
        if self.enable_lazy_loading and self._lazy_cache:
            cache_stats = self._lazy_cache.get_stats()
            base_stats.update({
                'lazy_loading': {
                    'enabled': True,
                    'cache_stats': cache_stats,
                    'indexed_files': len(self._indexed_files),
                    'cache_max_entries': self.lazy_cache_max_entries,
                    'cache_max_memory_mb': self.lazy_cache_max_memory_mb
                }
            })
        else:
            base_stats['lazy_loading'] = {'enabled': False}
        
        return base_stats
    
    def search_paginated(self, base_dn: str = "", filter_func: Optional[callable] = None, 
                        page_size: int = 100, page_num: int = 0) -> PaginatedSearchResult:
        """Perform a paginated search with lazy loading."""
        if not self.enable_lazy_loading:
            raise ValueError("Paginated search requires lazy loading to be enabled")
        
        iterator = LazySearchIterator(self, base_dn, filter_func, page_size)
        return iterator.get_page(page_num)
    
    def create_search_iterator(self, base_dn: str = "", filter_func: Optional[callable] = None, 
                              page_size: int = 100) -> LazySearchIterator:
        """Create an iterator for lazy searching."""
        if not self.enable_lazy_loading:
            raise ValueError("Search iterator requires lazy loading to be enabled")
        
        return LazySearchIterator(self, base_dn, filter_func, page_size)
    
    def get_entry_count(self, base_dn: str = "") -> int:
        """Get total count of entries matching base DN."""
        if self.enable_lazy_loading:
            iterator = LazySearchIterator(self, base_dn)
            return iterator.get_total_count()
        else:
            # Fallback for non-lazy mode - count entries in tree
            root = self.get_root()
            if not base_dn:
                return self._count_entries_recursive(root)
            else:
                # Find base entry and count from there
                try:
                    base_entry = self._find_entry_by_dn(root, base_dn)
                    if base_entry:
                        return self._count_entries_recursive(base_entry)
                except:
                    pass
                return 0
    
    def _count_entries_recursive(self, entry: LDIFTreeEntry) -> int:
        """Recursively count entries in the tree."""
        count = 1  # Count this entry
        if hasattr(entry, '_children'):
            for child in entry._children.values():
                count += self._count_entries_recursive(child)
        return count
    
    def _find_entry_by_dn(self, root: LDIFTreeEntry, target_dn: str) -> Optional[LDIFTreeEntry]:
        """Find an entry by DN in the tree."""
        # This is a simplified implementation
        # In practice, you'd want to implement proper DN traversal
        if hasattr(root, 'dn') and root.dn == target_dn:
            return root
        
        if hasattr(root, '_children'):
            for child in root._children.values():
                result = self._find_entry_by_dn(child, target_dn)
                if result:
                    return result
        
        return None
    
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
    
    def __init__(self, json_path: str, hash_plain_passwords: bool = True, enable_watcher: bool = True, enable_lazy_loading: bool = False):
        """Initialize JSON storage with single file (legacy interface)."""
        self.json_path = json_path
        
        # Use federated storage internally for consistency
        self._federated = FederatedJSONStorage(
            json_files=[json_path],
            merge_strategy="last_wins",
            hash_plain_passwords=hash_plain_passwords,
            enable_watcher=enable_watcher,
            enable_lazy_loading=enable_lazy_loading
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
