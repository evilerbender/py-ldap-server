"""
Unit tests for lazy loading functionality in JSON storage.
"""
import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ldap_server.storage.json import (
    FederatedJSONStorage,
    LazyEntryReference,
    LazyEntryCache,
    IndexedJSONFile,
    LazyLDIFTreeEntry,
    PaginatedSearchResult,
    LazySearchIterator
)


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return [
        {
            "dn": "dc=example,dc=com",
            "attributes": {
                "objectClass": ["top", "domain"],
                "dc": ["example"]
            }
        },
        {
            "dn": "ou=users,dc=example,dc=com",
            "attributes": {
                "objectClass": ["top", "organizationalUnit"],
                "ou": ["users"]
            }
        },
        {
            "dn": "uid=john,ou=users,dc=example,dc=com",
            "attributes": {
                "objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"],
                "uid": ["john"],
                "cn": ["John Doe"],
                "sn": ["Doe"],
                "mail": ["john.doe@example.com"]
            }
        },
        {
            "dn": "uid=jane,ou=users,dc=example,dc=com",
            "attributes": {
                "objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"],
                "uid": ["jane"],
                "cn": ["Jane Smith"],
                "sn": ["Smith"],
                "mail": ["jane.smith@example.com"]
            }
        }
    ]


@pytest.fixture
def temp_json_file(sample_json_data):
    """Create a temporary JSON file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_json_data, f, indent=2)
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestLazyEntryCache:
    """Test the lazy entry cache."""
    
    def test_cache_creation(self):
        """Test cache creation with parameters."""
        cache = LazyEntryCache(max_entries=500, max_memory_mb=50)
        
        assert cache.max_entries == 500
        assert cache.max_memory_bytes == 50 * 1024 * 1024
        assert len(cache._cache) == 0
    
    def test_cache_put_and_get(self, temp_json_file):
        """Test putting and getting entries from cache."""
        cache = LazyEntryCache(max_entries=10, max_memory_mb=10)
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        # Create a lazy reference
        lazy_ref = LazyEntryReference("uid=john,ou=users,dc=example,dc=com", temp_json_file, 0, indexed_file)
        
        # Test cache miss
        result = cache.get("uid=john,ou=users,dc=example,dc=com")
        assert result is None
        assert cache.stats['misses'] == 1
        
        # Put in cache
        cache.put("uid=john,ou=users,dc=example,dc=com", lazy_ref)
        
        # Test cache hit
        result = cache.get("uid=john,ou=users,dc=example,dc=com")
        assert result is not None
        assert result.dn == "uid=john,ou=users,dc=example,dc=com"
        assert cache.stats['hits'] == 1
    
    def test_cache_eviction(self, temp_json_file):
        """Test cache eviction when limits are exceeded."""
        cache = LazyEntryCache(max_entries=2, max_memory_mb=10)
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        # Add entries to exceed limit
        for i in range(3):
            dn = f"uid=user{i},ou=users,dc=example,dc=com"
            lazy_ref = LazyEntryReference(dn, temp_json_file, i, indexed_file)
            cache.put(dn, lazy_ref)
        
        # Should have evicted the first entry
        assert len(cache._cache) == 2
        assert cache.stats['evictions'] >= 1
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = LazyEntryCache()
        stats = cache.get_stats()
        
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'evictions' in stats
        assert 'cached_entries' in stats
        assert 'memory_usage_bytes' in stats
        assert 'hit_rate' in stats


class TestIndexedJSONFile:
    """Test the indexed JSON file reader."""
    
    def test_index_building(self, temp_json_file, sample_json_data):
        """Test building index for JSON file."""
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        assert indexed_file.total_entries == len(sample_json_data)
        assert "dc=example,dc=com" in indexed_file.entry_index
        assert "uid=john,ou=users,dc=example,dc=com" in indexed_file.entry_index
    
    def test_get_entry_reference(self, temp_json_file):
        """Test getting lazy entry references."""
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        # Test existing entry
        lazy_ref = indexed_file.get_entry_reference("uid=john,ou=users,dc=example,dc=com")
        assert lazy_ref is not None
        assert lazy_ref.dn == "uid=john,ou=users,dc=example,dc=com"
        
        # Test non-existing entry
        lazy_ref = indexed_file.get_entry_reference("uid=nonexistent,ou=users,dc=example,dc=com")
        assert lazy_ref is None
    
    def test_get_all_dns(self, temp_json_file, sample_json_data):
        """Test getting all DNs from indexed file."""
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        all_dns = indexed_file.get_all_dns()
        expected_dns = {entry["dn"] for entry in sample_json_data}
        
        assert all_dns == expected_dns
    
    def test_load_entry_by_index(self, temp_json_file, sample_json_data):
        """Test loading entry by index."""
        indexed_file = IndexedJSONFile(temp_json_file)
        
        # Test valid index
        entry = indexed_file.load_entry_by_index(0)
        assert entry is not None
        assert entry["dn"] == sample_json_data[0]["dn"]
        
        # Test invalid index
        entry = indexed_file.load_entry_by_index(999)
        assert entry is None


class TestLazyEntryReference:
    """Test lazy entry reference functionality."""
    
    def test_lazy_loading(self, temp_json_file):
        """Test lazy loading of entry attributes."""
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        lazy_ref = LazyEntryReference("uid=john,ou=users,dc=example,dc=com", temp_json_file, 2, indexed_file)
        
        # Initially not loaded
        assert not lazy_ref.is_loaded()
        
        # Load attributes
        attrs = lazy_ref.get_attributes()
        
        # Now should be loaded
        assert lazy_ref.is_loaded()
        assert "uid" in attrs
        assert attrs["uid"] == ["john"]
        assert attrs["cn"] == ["John Doe"]
    
    def test_memory_estimation(self, temp_json_file):
        """Test memory usage estimation."""
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        lazy_ref = LazyEntryReference("uid=john,ou=users,dc=example,dc=com", temp_json_file, 2, indexed_file)
        
        # Initially no memory usage
        assert lazy_ref.get_memory_size() == 0
        
        # Load attributes
        lazy_ref.get_attributes()
        
        # Now should have memory usage
        assert lazy_ref.get_memory_size() > 0
    
    def test_unload(self, temp_json_file):
        """Test unloading of lazy attributes."""
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        lazy_ref = LazyEntryReference("uid=john,ou=users,dc=example,dc=com", temp_json_file, 2, indexed_file)
        
        # Load and then unload
        lazy_ref.get_attributes()
        assert lazy_ref.is_loaded()
        
        lazy_ref.unload()
        assert not lazy_ref.is_loaded()


class TestFederatedJSONStorageLazyLoading:
    """Test lazy loading in FederatedJSONStorage."""
    
    def test_lazy_loading_enabled(self, temp_json_file):
        """Test creating storage with lazy loading enabled."""
        storage = FederatedJSONStorage(
            json_files=[temp_json_file],
            enable_lazy_loading=True,
            lazy_cache_max_entries=100,
            lazy_cache_max_memory_mb=10
        )
        
        assert storage.enable_lazy_loading is True
        assert storage._lazy_cache is not None
        assert storage.lazy_cache_max_entries == 100
        
        # Check statistics
        stats = storage.get_stats()
        assert stats['lazy_loading']['enabled'] is True
        assert 'cache_stats' in stats['lazy_loading']
    
    def test_lazy_loading_disabled(self, temp_json_file):
        """Test creating storage with lazy loading disabled."""
        storage = FederatedJSONStorage(
            json_files=[temp_json_file],
            enable_lazy_loading=False
        )
        
        assert storage.enable_lazy_loading is False
        assert storage._lazy_cache is None
        
        # Check statistics
        stats = storage.get_stats()
        assert stats['lazy_loading']['enabled'] is False
    
    def test_indexed_files_creation(self, temp_json_file):
        """Test that indexed files are created with lazy loading."""
        storage = FederatedJSONStorage(
            json_files=[temp_json_file],
            enable_lazy_loading=True
        )
        
        assert len(storage._indexed_files) == 1
        assert temp_json_file in storage._indexed_files
        
        indexed_file = storage._indexed_files[temp_json_file]
        assert indexed_file.total_entries > 0
    
    def test_get_entry_count(self, temp_json_file, sample_json_data):
        """Test getting entry count with lazy loading."""
        storage = FederatedJSONStorage(
            json_files=[temp_json_file],
            enable_lazy_loading=True
        )
        
        # Test total count
        total_count = storage.get_entry_count()
        assert total_count == len(sample_json_data)
        
        # Test count with base DN
        user_count = storage.get_entry_count("ou=users,dc=example,dc=com")
        assert user_count >= 2  # Should include at least the user entries


class TestPaginatedSearchResult:
    """Test paginated search results."""
    
    def test_pagination_basic(self):
        """Test basic pagination functionality."""
        # Create mock entries
        entries = [MagicMock() for _ in range(25)]
        
        paginated = PaginatedSearchResult(entries, page_size=10)
        
        assert paginated.total_count == 25
        assert paginated.total_pages == 3
        assert paginated.page_size == 10
        
        # Test getting pages
        page_0 = paginated.get_page(0)
        assert len(page_0) == 10
        
        page_2 = paginated.get_page(2)
        assert len(page_2) == 5  # Last page with remaining entries
    
    def test_pagination_navigation(self):
        """Test pagination navigation."""
        entries = [MagicMock() for _ in range(15)]
        paginated = PaginatedSearchResult(entries, page_size=5)
        
        # Test navigation
        assert not paginated.has_previous_page()
        assert paginated.has_next_page()
        
        next_page = paginated.get_next_page()
        assert len(next_page) == 5
        assert paginated.current_page == 1
        
        prev_page = paginated.get_previous_page()
        assert len(prev_page) == 5
        assert paginated.current_page == 0
    
    def test_page_info(self):
        """Test page information."""
        entries = [MagicMock() for _ in range(20)]
        paginated = PaginatedSearchResult(entries, page_size=7)
        
        info = paginated.get_page_info()
        
        assert info['current_page'] == 0
        assert info['total_pages'] == 3
        assert info['page_size'] == 7
        assert info['total_count'] == 20
        assert info['has_next'] is True
        assert info['has_previous'] is False


class TestLazySearchIterator:
    """Test lazy search iterator functionality."""
    
    def test_search_iterator_creation(self, temp_json_file):
        """Test creating search iterator."""
        storage = FederatedJSONStorage(
            json_files=[temp_json_file],
            enable_lazy_loading=True
        )
        
        iterator = storage.create_search_iterator(
            base_dn="ou=users,dc=example,dc=com",
            page_size=2
        )
        
        assert iterator.base_dn == "ou=users,dc=example,dc=com"
        assert iterator.page_size == 2
    
    def test_paginated_search(self, temp_json_file):
        """Test paginated search functionality."""
        storage = FederatedJSONStorage(
            json_files=[temp_json_file],
            enable_lazy_loading=True
        )
        
        # Test paginated search
        result = storage.search_paginated(
            base_dn="dc=example,dc=com",
            page_size=2,
            page_num=0
        )
        
        assert isinstance(result, PaginatedSearchResult)
        assert result.page_size == 2
        assert len(result.entries) <= 2
    
    def test_search_iterator_requires_lazy_loading(self, temp_json_file):
        """Test that search iterator requires lazy loading."""
        storage = FederatedJSONStorage(
            json_files=[temp_json_file],
            enable_lazy_loading=False
        )
        
        with pytest.raises(ValueError, match="requires lazy loading"):
            storage.create_search_iterator()
        
        with pytest.raises(ValueError, match="requires lazy loading"):
            storage.search_paginated()


class TestLazyLDIFTreeEntry:
    """Test lazy LDIF tree entry functionality."""
    
    def test_lazy_entry_creation(self, temp_json_file):
        """Test creating lazy LDIF tree entries."""
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        lazy_ref = LazyEntryReference("uid=john,ou=users,dc=example,dc=com", temp_json_file, 2, indexed_file)
        
        lazy_entry = LazyLDIFTreeEntry(
            "/tmp/test",
            "uid=john,ou=users,dc=example,dc=com",
            lazy_ref
        )
        
        assert lazy_entry.is_lazy_loaded()
        assert not lazy_entry.is_loaded()
    
    def test_lazy_attribute_access(self, temp_json_file):
        """Test lazy loading on attribute access."""
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        lazy_ref = LazyEntryReference("uid=john,ou=users,dc=example,dc=com", temp_json_file, 2, indexed_file)
        cache = LazyEntryCache()
        
        lazy_entry = LazyLDIFTreeEntry(
            "/tmp/test",
            "uid=john,ou=users,dc=example,dc=com",
            lazy_ref
        )
        lazy_entry.set_cache(cache)
        
        # Initially not loaded
        assert not lazy_entry.is_loaded()
        
        # Access attribute should trigger lazy loading
        if 'uid' in lazy_entry:
            # Should now be loaded
            assert lazy_entry.is_loaded()
    
    def test_lazy_entry_unloading(self, temp_json_file):
        """Test unloading lazy entry attributes."""
        indexed_file = IndexedJSONFile(temp_json_file)
        indexed_file.build_index()
        
        lazy_ref = LazyEntryReference("uid=john,ou=users,dc=example,dc=com", temp_json_file, 2, indexed_file)
        cache = LazyEntryCache()
        
        lazy_entry = LazyLDIFTreeEntry(
            "/tmp/test",
            "uid=john,ou=users,dc=example,dc=com",
            lazy_ref
        )
        lazy_entry.set_cache(cache)
        
        # Load attributes
        _ = lazy_entry.keys()  # This should trigger loading
        assert lazy_entry.is_loaded()
        
        # Unload attributes
        lazy_entry.unload_lazy_attributes()
        assert not lazy_entry.is_loaded()


if __name__ == "__main__":
    pytest.main([__file__])
