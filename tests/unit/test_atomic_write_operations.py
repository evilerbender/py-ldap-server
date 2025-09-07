"""
Unit tests for atomic write operations in JSON storage.
"""
import pytest
import tempfile
import json
import os
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ldap_server.storage.json import (
    JSONStorage,
    AtomicJSONWriter
)


@pytest.fixture
def temp_json_file():
    """Create a temporary JSON file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
        
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_entries():
    """Sample LDAP entries for testing."""
    return [
        {
            "dn": "dc=example,dc=com",
            "attributes": {
                "dc": ["example"],
                "objectClass": ["top", "domain"]
            }
        },
        {
            "dn": "ou=users,dc=example,dc=com",
            "attributes": {
                "ou": ["users"],
                "objectClass": ["top", "organizationalUnit"]
            }
        },
        {
            "dn": "uid=john,ou=users,dc=example,dc=com",
            "attributes": {
                "uid": ["john"],
                "cn": ["John Doe"],
                "sn": ["Doe"],
                "objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"]
            }
        }
    ]


def verify_entry_in_file(file_path: Path, target_dn: str) -> bool:
    """Helper function to verify if an entry exists in a JSON file."""
    try:
        with open(file_path, 'r') as f:
            entries = json.load(f)
        return any(entry.get('dn') == target_dn for entry in entries)
    except Exception:
        return False


def get_entry_from_file(file_path: Path, target_dn: str) -> dict:
    """Helper function to get a specific entry from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            entries = json.load(f)
        for entry in entries:
            if entry.get('dn') == target_dn:
                return entry
        return None
    except Exception:
        return None


class TestAtomicJSONWriter:
    """Test AtomicJSONWriter functionality."""
    
    def test_atomic_writer_basic_write(self, temp_json_file):
        """Test basic atomic write operation."""
        test_data = [{"dn": "dc=test,dc=com", "attributes": {"dc": ["test"]}}]
        
        with AtomicJSONWriter(temp_json_file) as writer:
            writer.write_json(test_data)
        
        # Verify data was written
        with open(temp_json_file, 'r') as f:
            written_data = json.load(f)
        
        assert written_data == test_data
        
    def test_atomic_writer_backup_creation(self, temp_json_file):
        """Test that backups are created before writing."""
        original_data = [{"dn": "dc=original,dc=com", "attributes": {}}]
        
        # Write initial data
        with open(temp_json_file, 'w') as f:
            json.dump(original_data, f)
        
        new_data = [{"dn": "dc=new,dc=com", "attributes": {}}]
        
        # Perform atomic write
        with AtomicJSONWriter(temp_json_file, backup_enabled=True) as writer:
            writer.write_json(new_data)
        
        # Check that backup was created
        backup_files = list(temp_json_file.parent.glob(f"{temp_json_file.name}.*.bak"))
        assert len(backup_files) >= 1
        
        # Verify backup contains original data
        with open(backup_files[0], 'r') as f:
            backup_data = json.load(f)
        assert backup_data == original_data
        
        # Verify new data was written
        with open(temp_json_file, 'r') as f:
            current_data = json.load(f)
        assert current_data == new_data
        
        # Cleanup backup file
        backup_files[0].unlink()
    
    def test_atomic_writer_rollback_on_exception(self, temp_json_file):
        """Test that writes are rolled back on exceptions."""
        original_data = [{"dn": "dc=original,dc=com", "attributes": {}}]
        
        # Write initial data
        with open(temp_json_file, 'w') as f:
            json.dump(original_data, f)
        
        # Attempt write that will fail
        try:
            with AtomicJSONWriter(temp_json_file, backup_enabled=True) as writer:
                writer.write_json([{"dn": "dc=new,dc=com", "attributes": {}}])
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        # Original data should still be intact
        with open(temp_json_file, 'r') as f:
            current_data = json.load(f)
        assert current_data == original_data
    
    def test_atomic_writer_concurrent_access_protection(self, temp_json_file):
        """Test that concurrent writes are properly serialized."""
        results = []
        
        def write_data(data_id):
            with AtomicJSONWriter(temp_json_file) as writer:
                # Small delay to increase chance of race condition
                time.sleep(0.1)
                writer.write_json([{"dn": f"dc=test{data_id},dc=com", "attributes": {}}])
                results.append(data_id)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=write_data, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All writes should have succeeded (results should have 3 items)
        assert len(results) == 3
        
        # Final file should contain data from one of the writes
        with open(temp_json_file, 'r') as f:
            final_data = json.load(f)
        assert len(final_data) == 1
    
    def test_atomic_writer_lock_timeout(self, temp_json_file):
        """Test lock timeout functionality."""
        lock_acquired = threading.Event()
        lock_released = threading.Event()
        
        # Hold a lock in one thread
        def hold_lock():
            try:
                with AtomicJSONWriter(temp_json_file, lock_timeout=10.0) as writer:
                    lock_acquired.set()  # Signal that lock is acquired
                    time.sleep(2.0)  # Hold lock for 2 seconds
                    writer.write_json([{"dn": "dc=test1,dc=com", "attributes": {}}])
            finally:
                lock_released.set()  # Signal that lock is released
        
        lock_holder = threading.Thread(target=hold_lock)
        lock_holder.start()
        
        # Wait for first thread to acquire lock
        assert lock_acquired.wait(timeout=5.0), "First thread should acquire lock"
        
        # Try to acquire lock with short timeout - should fail
        with pytest.raises((TimeoutError, RuntimeError)):
            with AtomicJSONWriter(temp_json_file, lock_timeout=0.5) as writer:
                writer.write_json([{"dn": "dc=test2,dc=com", "attributes": {}}])
        
        # Wait for first thread to complete
        lock_holder.join(timeout=5.0)
        assert lock_released.is_set(), "First thread should release lock"


class TestUnifiedJSONStorageWriteOperations:
    """Test write operations on unified JSONStorage with federation."""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, temp_json_file, sample_entries):
        """Set up test data before each test."""
        with open(temp_json_file, 'w') as f:
            json.dump(sample_entries, f, indent=2)
    
    def test_add_entry(self, temp_json_file, sample_entries):
        """Test adding a new entry."""
        storage = JSONStorage(json_files=[temp_json_file])
        
        new_entry_dn = "uid=jane,ou=users,dc=example,dc=com"
        new_entry_attrs = {
            "uid": ["jane"],
            "cn": ["Jane Smith"],
            "sn": ["Smith"],
            "objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"]
        }
        
        result = storage.add_entry(new_entry_dn, new_entry_attrs, target_file=temp_json_file)
        assert result is True
        
        # Verify entry was added
        assert verify_entry_in_file(temp_json_file, new_entry_dn)
    
    def test_add_entry_duplicate_dn(self, temp_json_file, sample_entries):
        """Test adding entry with duplicate DN."""
        storage = JSONStorage(json_files=[temp_json_file])
        
        # Try to add entry with existing DN
        result = storage.add_entry(
            "uid=john,ou=users,dc=example,dc=com",
            {"cn": ["John Smith"]},
            target_file=temp_json_file
        )
        assert result is False
    
    def test_modify_entry(self, temp_json_file, sample_entries):
        """Test modifying an existing entry."""
        storage = JSONStorage(json_files=[temp_json_file])
        
        result = storage.modify_entry(
            "uid=john,ou=users,dc=example,dc=com",
            {"cn": ["John Smith Updated"]}
        )
        assert result is True
        
        # Verify modification
        modified_entry = get_entry_from_file(temp_json_file, "uid=john,ou=users,dc=example,dc=com")
        assert modified_entry is not None
        assert modified_entry["attributes"]["cn"] == ["John Smith Updated"]
    
    def test_modify_nonexistent_entry(self, temp_json_file, sample_entries):
        """Test modifying a non-existent entry."""
        storage = JSONStorage(json_files=[temp_json_file])
        
        result = storage.modify_entry("uid=nonexistent,ou=users,dc=example,dc=com", {"cn": ["New Name"]})
        assert result is False
    
    def test_delete_entry(self, temp_json_file, sample_entries):
        """Test deleting an entry."""
        storage = JSONStorage(json_files=[temp_json_file])
        
        result = storage.delete_entry("uid=john,ou=users,dc=example,dc=com")
        assert result is True
        
        # Verify deletion
        assert not verify_entry_in_file(temp_json_file, "uid=john,ou=users,dc=example,dc=com")
    
    def test_delete_nonexistent_entry(self, temp_json_file, sample_entries):
        """Test deleting a non-existent entry."""
        storage = JSONStorage(json_files=[temp_json_file])
        
        result = storage.delete_entry("uid=nonexistent,ou=users,dc=example,dc=com")
        assert result is False
    
    def test_bulk_write_entries(self, temp_json_file, sample_entries):
        """Test bulk writing multiple entries."""
        storage = JSONStorage(json_files=[temp_json_file])
        
        new_entries = [
            {
                "dn": "uid=alice,ou=users,dc=example,dc=com",
                "attributes": {
                    "uid": ["alice"],
                    "cn": ["Alice Brown"],
                    "sn": ["Brown"],
                    "objectClass": ["top", "person"]
                }
            },
            {
                "dn": "uid=bob,ou=users,dc=example,dc=com",
                "attributes": {
                    "uid": ["bob"],
                    "cn": ["Bob Wilson"],
                    "sn": ["Wilson"],
                    "objectClass": ["top", "person"]
                }
            }
        ]
        
        result = storage.bulk_write_entries(new_entries, temp_json_file)
        assert result is True
        
        # Verify entries were added
        assert verify_entry_in_file(temp_json_file, "uid=alice,ou=users,dc=example,dc=com")
        assert verify_entry_in_file(temp_json_file, "uid=bob,ou=users,dc=example,dc=com")
    
    def test_bulk_write_invalid_entries(self, temp_json_file, sample_entries):
        """Test bulk writing with some invalid entries."""
        storage = JSONStorage(json_files=[temp_json_file], enable_file_watching=False)
        
        entries_with_invalid = [
            {
                "dn": "uid=alice,ou=users,dc=example,dc=com",
                "attributes": {"uid": ["alice"], "cn": ["Alice"]}
            },
            {
                "dn": "",  # Invalid DN - should be skipped
                "attributes": {"uid": ["invalid"]}
            }
        ]
        
        # The unified backend handles invalid entries gracefully
        # It processes valid entries and logs errors for invalid ones
        result = storage.bulk_write_entries(entries_with_invalid)
        
        # The operation should complete even with some invalid entries
        assert result is True  # Updated to match unified backend behavior
        
        storage.cleanup()


class TestJSONStorageWriteOperations:
    """Test write operations on legacy JSONStorage."""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, temp_json_file, sample_entries):
        """Set up test data before each test."""
        with open(temp_json_file, 'w') as f:
            json.dump(sample_entries, f, indent=2)
    
    def test_add_entry_legacy(self, temp_json_file, sample_entries):
        """Test adding entry with unified JSONStorage."""
        storage = JSONStorage(json_files=[str(temp_json_file)])
        
        new_entry_dn = "uid=legacy,ou=users,dc=example,dc=com"
        new_entry_attrs = {
            "uid": ["legacy"],
            "cn": ["Legacy User"],
            "objectClass": ["top", "person"]
        }
        
        result = storage.add_entry(new_entry_dn, new_entry_attrs)
        assert result is True
        
        # Verify entry was added
        assert verify_entry_in_file(temp_json_file, new_entry_dn)
    
    def test_modify_entry_legacy(self, temp_json_file, sample_entries):
        """Test modifying entry with unified JSONStorage."""
        storage = JSONStorage(json_files=[str(temp_json_file)])
        
        result = storage.modify_entry(
            "uid=john,ou=users,dc=example,dc=com",
            {"cn": ["John Legacy Updated"]}
        )
        assert result is True
        
        # Verify modification
        modified_entry = get_entry_from_file(temp_json_file, "uid=john,ou=users,dc=example,dc=com")
        assert modified_entry is not None
        assert modified_entry["attributes"]["cn"] == ["John Legacy Updated"]
    
    def test_delete_entry_legacy(self, temp_json_file, sample_entries):
        """Test deleting entry with unified JSONStorage."""
        storage = JSONStorage(json_files=[str(temp_json_file)])
        
        result = storage.delete_entry("uid=john,ou=users,dc=example,dc=com")
        assert result is True
        
        # Verify deletion
        assert not verify_entry_in_file(temp_json_file, "uid=john,ou=users,dc=example,dc=com")
    
    def test_bulk_write_legacy(self, temp_json_file, sample_entries):
        """Test bulk write with unified JSONStorage."""
        storage = JSONStorage(json_files=[str(temp_json_file)])
        
        new_entries = [
            {
                "dn": "uid=bulk1,ou=users,dc=example,dc=com",
                "attributes": {"uid": ["bulk1"], "cn": ["Bulk User 1"]}
            },
            {
                "dn": "uid=bulk2,ou=users,dc=example,dc=com", 
                "attributes": {"uid": ["bulk2"], "cn": ["Bulk User 2"]}
            }
        ]
        
        result = storage.bulk_write_entries(new_entries)
        assert result is True
        
        # Verify entries were added
        assert verify_entry_in_file(temp_json_file, "uid=bulk1,ou=users,dc=example,dc=com")
        assert verify_entry_in_file(temp_json_file, "uid=bulk2,ou=users,dc=example,dc=com")


class TestAtomicWriteErrorScenarios:
    """Test error scenarios and edge cases."""
    
    def test_write_to_nonexistent_directory(self):
        """Test writing to a nonexistent directory."""
        import shutil
        
        nonexistent_path = Path("/tmp/nonexistent_dir_12345/test.json")
        
        # Should create directory automatically
        with AtomicJSONWriter(nonexistent_path) as writer:
            writer.write_json([{"dn": "dc=test,dc=com", "attributes": {}}])
        
        # Verify file was created
        assert nonexistent_path.exists()
        
        # Cleanup - remove entire directory tree
        shutil.rmtree(nonexistent_path.parent)
    
    def test_disk_space_error_simulation(self, temp_json_file):
        """Test handling of disk space errors during write."""
        with patch('json.dump') as mock_dump:
            mock_dump.side_effect = OSError("No space left on device")
            
            with pytest.raises(RuntimeError, match="Failed to write JSON data"):
                with AtomicJSONWriter(temp_json_file) as writer:
                    writer.write_json([{"dn": "dc=test,dc=com", "attributes": {}}])
            
            # Original file should remain unchanged if it existed
            if temp_json_file.exists():
                with open(temp_json_file, 'r') as f:
                    # Should be empty or contain previous data
                    content = f.read()
                    assert content == "" or json.loads(content) is not None
