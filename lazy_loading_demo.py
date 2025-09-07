#!/usr/bin/env python3
"""
Performance demonstration and testing for lazy loading functionality.
"""
import json
import tempfile
import time
import os
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available, memory monitoring disabled")

from src.ldap_server.storage.json import FederatedJSONStorage


def create_large_test_data(filename: str, num_users: int = 1000):
    """Create a large JSON file for testing."""
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
        user_dn = f"uid=user{i:04d},ou=users,dc=example,dc=com"
        entries.append({
            "dn": user_dn,
            "attributes": {
                "objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"],
                "uid": [f"user{i:04d}"],
                "cn": [f"User {i:04d}"],
                "sn": [f"Surname{i:04d}"],
                "mail": [f"user{i:04d}@example.com"],
                "telephoneNumber": [f"+1-555-{i:04d}"],
                "description": [f"Test user account number {i:04d} for performance testing"],
                "userPassword": [f"password{i:04d}"]
            }
        })
    
    with open(filename, 'w') as f:
        json.dump(entries, f, indent=2)
    
    print(f"Created test file {filename} with {len(entries)} entries")
    return len(entries)


def get_memory_usage():
    """Get current memory usage in MB."""
    if PSUTIL_AVAILABLE:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    else:
        return 0.0  # Return 0 if psutil not available


def benchmark_traditional_loading(json_file: str):
    """Benchmark traditional (non-lazy) loading."""
    print("\n=== Traditional Loading Benchmark ===")
    
    start_memory = get_memory_usage()
    start_time = time.time()
    
    storage = FederatedJSONStorage(
        json_files=[json_file],
        enable_lazy_loading=False
    )
    
    load_time = time.time() - start_time
    end_memory = get_memory_usage()
    memory_used = end_memory - start_memory
    
    print(f"Load time: {load_time:.3f} seconds")
    print(f"Memory used: {memory_used:.1f} MB")
    print(f"Total entries: {storage.get_stats()['total_entries']}")
    
    storage.cleanup()
    return load_time, memory_used


def benchmark_lazy_loading(json_file: str):
    """Benchmark lazy loading."""
    print("\n=== Lazy Loading Benchmark ===")
    
    start_memory = get_memory_usage()
    start_time = time.time()
    
    storage = FederatedJSONStorage(
        json_files=[json_file],
        enable_lazy_loading=True,
        lazy_cache_max_entries=100,  # Small cache for testing
        lazy_cache_max_memory_mb=10
    )
    
    load_time = time.time() - start_time
    end_memory = get_memory_usage()
    memory_used = end_memory - start_memory
    
    print(f"Initial load time: {load_time:.3f} seconds")
    print(f"Initial memory used: {memory_used:.1f} MB")
    print(f"Total entries indexed: {storage.get_stats()['total_entries']}")
    
    # Test search operations
    print("\n--- Testing Search Operations ---")
    
    # Test paginated search
    search_start = time.time()
    result = storage.search_paginated(
        base_dn="ou=users,dc=example,dc=com",
        page_size=10,
        page_num=0
    )
    search_time = time.time() - search_start
    search_memory = get_memory_usage()
    
    print(f"Paginated search time: {search_time:.3f} seconds")
    print(f"Memory after search: {search_memory:.1f} MB")
    print(f"Entries in page: {len(result.entries)}")
    print(f"Page info: {result.get_page_info()}")
    
    # Test cache statistics
    cache_stats = storage.get_stats()['lazy_loading']['cache_stats']
    print(f"\nCache statistics:")
    print(f"  Cache hits: {cache_stats['hits']}")
    print(f"  Cache misses: {cache_stats['misses']}")
    print(f"  Hit rate: {cache_stats['hit_rate']:.1%}")
    print(f"  Cached entries: {cache_stats['cached_entries']}")
    print(f"  Cache memory usage: {cache_stats['memory_usage_mb']:.1f} MB")
    
    storage.cleanup()
    return load_time, memory_used, search_time


def benchmark_iterator(json_file: str):
    """Benchmark lazy iterator functionality."""
    print("\n=== Lazy Iterator Benchmark ===")
    
    storage = FederatedJSONStorage(
        json_files=[json_file],
        enable_lazy_loading=True,
        lazy_cache_max_entries=50
    )
    
    # Create iterator
    iterator = storage.create_search_iterator(
        base_dn="ou=users,dc=example,dc=com",
        page_size=20
    )
    
    print(f"Total entries to iterate: {iterator.get_total_count()}")
    
    # Iterate through first few pages
    start_time = time.time()
    start_memory = get_memory_usage()
    
    entries_processed = 0
    for i, page_result in enumerate([iterator.get_page(p) for p in range(3)]):
        entries_processed += len(page_result.entries)
        if i == 0:
            first_page_time = time.time() - start_time
            first_page_memory = get_memory_usage()
    
    end_time = time.time() - start_time
    end_memory = get_memory_usage()
    
    print(f"First page time: {first_page_time:.3f} seconds")
    print(f"First page memory: {first_page_memory:.1f} MB")
    print(f"Total processing time: {end_time:.3f} seconds")
    print(f"Final memory usage: {end_memory:.1f} MB")
    print(f"Entries processed: {entries_processed}")
    
    storage.cleanup()


def main():
    """Run performance benchmarks."""
    print("Lazy Loading Performance Benchmark")
    print("=" * 50)
    
    # Create test data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_file = f.name
    
    try:
        # Create test data with different sizes
        sizes = [100, 500, 1000]
        
        for size in sizes:
            print(f"\n{'=' * 60}")
            print(f"TESTING WITH {size} USERS")
            print(f"{'=' * 60}")
            
            create_large_test_data(test_file, size)
            file_size = os.path.getsize(test_file) / 1024 / 1024  # MB
            print(f"Test file size: {file_size:.1f} MB")
            
            # Benchmark traditional loading
            trad_time, trad_memory = benchmark_traditional_loading(test_file)
            
            # Benchmark lazy loading
            lazy_time, lazy_memory, search_time = benchmark_lazy_loading(test_file)
            
            # Benchmark iterator
            benchmark_iterator(test_file)
            
            # Summary
            print(f"\n--- Summary for {size} users ---")
            print(f"Traditional loading: {trad_time:.3f}s, {trad_memory:.1f} MB")
            print(f"Lazy loading: {lazy_time:.3f}s, {lazy_memory:.1f} MB")
            print(f"Memory savings: {((trad_memory - lazy_memory) / trad_memory * 100):.1f}%")
            print(f"Time improvement: {((trad_time - lazy_time) / trad_time * 100):.1f}%")
    
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.unlink(test_file)


if __name__ == "__main__":
    main()
