#!/usr/bin/env python3
"""
Simple lazy loading demonstration script.
"""
import json
import tempfile
import time
import os
from pathlib import Path

from src.ldap_server.storage.json import FederatedJSONStorage


def create_test_data(filename: str, num_users: int = 10):
    """Create a small test JSON file."""
    entries = []
    
    # Root domain
    entries.append({
        "dn": "dc=example,dc=com",
        "attributes": {
            "objectClass": ["top", "domain"],
            "dc": ["example"]
        }
    })
    
    # Users OU
    entries.append({
        "dn": "ou=users,dc=example,dc=com",
        "attributes": {
            "objectClass": ["top", "organizationalUnit"],
            "ou": ["users"]
        }
    })
    
    # Generate users
    for i in range(num_users):
        user_dn = f"uid=user{i:03d},ou=users,dc=example,dc=com"
        entries.append({
            "dn": user_dn,
            "attributes": {
                "objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"],
                "uid": [f"user{i:03d}"],
                "cn": [f"User {i:03d}"],
                "sn": [f"Surname{i:03d}"],
                "mail": [f"user{i:03d}@example.com"]
            }
        })
    
    with open(filename, 'w') as f:
        json.dump(entries, f, indent=2)
    
    print(f"Created test file {filename} with {len(entries)} entries")
    return len(entries)


def test_traditional_loading(json_file: str):
    """Test traditional loading."""
    print("\n=== Traditional Loading ===")
    
    start_time = time.time()
    storage = FederatedJSONStorage(
        json_files=[json_file],
        enable_lazy_loading=False
    )
    load_time = time.time() - start_time
    
    stats = storage.get_stats()
    print(f"Load time: {load_time:.3f} seconds")
    print(f"Total entries: {stats['total_entries']}")
    print(f"Lazy loading: {stats.get('lazy_loading', {}).get('enabled', False)}")
    
    storage.cleanup()
    return load_time


def test_lazy_loading(json_file: str):
    """Test lazy loading."""
    print("\n=== Lazy Loading ===")
    
    start_time = time.time()
    storage = FederatedJSONStorage(
        json_files=[json_file],
        enable_lazy_loading=True,
        lazy_cache_max_entries=5,
        lazy_cache_max_memory_mb=1
    )
    load_time = time.time() - start_time
    
    stats = storage.get_stats()
    print(f"Initial load time: {load_time:.3f} seconds")
    print(f"Total entries indexed: {stats['total_entries']}")
    print(f"Lazy loading enabled: {stats['lazy_loading']['enabled']}")
    
    # Test paginated search
    print("\n--- Testing Paginated Search ---")
    search_start = time.time()
    
    try:
        result = storage.search_paginated(
            base_dn="ou=users,dc=example,dc=com",
            page_size=3,
            page_num=0
        )
        search_time = time.time() - search_start
        
        print(f"Search time: {search_time:.3f} seconds")
        print(f"Entries in page: {len(result.entries)}")
        print(f"Total pages: {result.total_pages}")
        
        # Test cache statistics
        cache_stats = storage.get_stats()['lazy_loading']['cache_stats']
        print(f"\nCache statistics:")
        print(f"  Cache hits: {cache_stats['hits']}")
        print(f"  Cache misses: {cache_stats['misses']}")
        print(f"  Cached entries: {cache_stats['cached_entries']}")
    
    except Exception as e:
        print(f"Search failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test iterator
    print("\n--- Testing Search Iterator ---")
    try:
        iterator = storage.create_search_iterator(
            base_dn="dc=example,dc=com",
            page_size=2
        )
        
        print(f"Total entries to iterate: {iterator.get_total_count()}")
        
        # Get first page
        page_result = iterator.get_page(0)
        print(f"First page entries: {len(page_result.entries)}")
        
    except Exception as e:
        print(f"Iterator failed: {e}")
        import traceback
        traceback.print_exc()
    
    storage.cleanup()
    return load_time


def main():
    """Run simple lazy loading demonstration."""
    print("Simple Lazy Loading Demo")
    print("=" * 40)
    
    # Create test data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_file = f.name
    
    try:
        num_entries = create_test_data(test_file, 10)
        file_size = os.path.getsize(test_file) / 1024  # KB
        print(f"Test file size: {file_size:.1f} KB")
        
        # Test traditional loading
        trad_time = test_traditional_loading(test_file)
        
        # Test lazy loading
        lazy_time = test_lazy_loading(test_file)
        
        # Summary
        print(f"\n{'=' * 40}")
        print("SUMMARY")
        print(f"{'=' * 40}")
        print(f"Traditional loading: {trad_time:.3f}s")
        print(f"Lazy loading: {lazy_time:.3f}s")
        if trad_time > 0:
            improvement = ((trad_time - lazy_time) / trad_time * 100)
            print(f"Time improvement: {improvement:.1f}%")
    
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.unlink(test_file)


if __name__ == "__main__":
    main()
