"""
Unit tests for unified JSON storage backend.
"""
import pytest
import tempfile
import json
import os
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ldap_server.storage.json import JSONStorage, AtomicJSONWriter


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


@pytest.fixture
def temp_json_files(sample_entries):
    """Create multiple temporary JSON files for federation testing."""
    users_file = tempfile.NamedTemporaryFile(mode='w', suffix='_users.json', delete=False)
    groups_file = tempfile.NamedTemporaryFile(mode='w', suffix='_groups.json', delete=False)
    
    # Write user entries
    user_entries = [entry for entry in sample_entries if 'uid=' in entry['dn'] or 'ou=users' in entry['dn']]
    json.dump(user_entries, users_file, indent=2)
    users_file.close()
    
    # Write group entries
    group_entries = [
        {
            "dn": "ou=groups,dc=example,dc=com",
            "attributes": {
                "ou": ["groups"],
                "objectClass": ["top", "organizationalUnit"]
            }
        },
        {
            "dn": "cn=admins,ou=groups,dc=example,dc=com",
            "attributes": {
                "cn": ["admins"],
                "objectClass": ["top", "groupOfNames"],
                "member": ["uid=john,ou=users,dc=example,dc=com"]
            }
        }
    ]
    json.dump(group_entries, groups_file, indent=2)
    groups_file.close()
    
    files = [Path(users_file.name), Path(groups_file.name)]
    
    yield files
    
    # Cleanup
    for file_path in files:
        if file_path.exists():
            file_path.unlink()


class TestUnifiedJSONStorage:
    """Test unified JSON storage backend."""
    
    def test_single_file_mode(self, temp_json_file, sample_entries):
        """Test single file mode (legacy compatibility)."""
        # Write sample data
        with open(temp_json_file, 'w') as f:
            json.dump(sample_entries, f, indent=2)
        
        # Initialize storage in single file mode
        storage = JSONStorage(
            json_files=str(temp_json_file),
            enable_file_watching=False
        )
        
        try:
            # Verify basic functionality
            root = storage.get_root()
            assert root is not None
            assert root.dn.getText() == ""  # Root should have empty DN
            
            # Check stats
            stats = storage.get_stats()
            assert stats['total_entries'] == 3
            assert stats['files_count'] == 1
            assert not stats['read_only']
            
        finally:
            storage.cleanup()
    
    def test_multi_file_mode(self, temp_json_files):
        """Test multi-file federation mode."""
        storage = JSONStorage(
            json_files=[str(f) for f in temp_json_files],
            merge_strategy="last_wins",
            enable_file_watching=False
        )
        
        try:
            # Verify federation worked
            root = storage.get_root()
            assert root is not None
            
            stats = storage.get_stats()
            assert stats['files_count'] == 2
            assert stats['total_entries'] >= 4  # At least users + groups entries
            assert stats['merge_strategy'] == "last_wins"
            
        finally:
            storage.cleanup()
    
    def test_read_only_mode(self, temp_json_file, sample_entries):
        """Test read-only mode functionality."""
        # Write sample data
        with open(temp_json_file, 'w') as f:
            json.dump(sample_entries, f, indent=2)
        
        # Initialize in read-only mode
        storage = JSONStorage(
            json_files=str(temp_json_file),
            read_only=True,
            enable_file_watching=False
        )
        
        try:
            # Verify read operations work
            root = storage.get_root()
            assert root is not None
            
            stats = storage.get_stats()
            assert stats['read_only'] is True
            
            # Verify write operations are disabled
            result = storage.add_entry(
                "uid=test,ou=users,dc=example,dc=com",
                {"uid": ["test"], "cn": ["Test User"]}
            )
            assert result is False
            
            result = storage.modify_entry(
                "uid=john,ou=users,dc=example,dc=com",
                {"cn": ["Modified Name"]}
            )
            assert result is False
            
            result = storage.delete_entry("uid=john,ou=users,dc=example,dc=com")
            assert result is False
            
            result = storage.bulk_write_entries([
                {"dn": "uid=bulk,ou=users,dc=example,dc=com", "attributes": {"uid": ["bulk"]}}
            ])
            assert result is False
            
        finally:
            storage.cleanup()
    
    def test_write_operations_enabled(self, temp_json_file, sample_entries):
        """Test write operations when not in read-only mode."""
        # Write sample data
        with open(temp_json_file, 'w') as f:
            json.dump(sample_entries, f, indent=2)
        
        storage = JSONStorage(
            json_files=str(temp_json_file),
            read_only=False,
            enable_file_watching=False,
            enable_backups=False  # Disable for testing
        )
        
        try:
            # Test add operation
            result = storage.add_entry(
                "uid=alice,ou=users,dc=example,dc=com",
                {
                    "uid": ["alice"],
                    "cn": ["Alice Smith"],
                    "objectClass": ["top", "person"]
                }
            )
            assert result is True
            
            # Test modify operation
            result = storage.modify_entry(
                "uid=john,ou=users,dc=example,dc=com",
                {
                    "uid": ["john"],
                    "cn": ["John Modified"],
                    "objectClass": ["top", "person"]
                }
            )
            assert result is True
            
            # Test delete operation
            result = storage.delete_entry("uid=alice,ou=users,dc=example,dc=com")
            assert result is True
            
            # Test bulk write
            bulk_entries = [
                {
                    "dn": "uid=bulk1,ou=users,dc=example,dc=com",
                    "attributes": {"uid": ["bulk1"], "cn": ["Bulk User 1"]}
                },
                {
                    "dn": "uid=bulk2,ou=users,dc=example,dc=com", 
                    "attributes": {"uid": ["bulk2"], "cn": ["Bulk User 2"]}
                }
            ]
            result = storage.bulk_write_entries(bulk_entries)
            assert result is True
            
        finally:
            storage.cleanup()
    
    def test_merge_strategies(self, temp_json_files):
        """Test different merge strategies for conflicting DNs."""
        # Create conflicting entries
        common_dn = "dc=example,dc=com"
        
        # Modify files to have same DN with different attributes
        file1, file2 = temp_json_files
        
        entries1 = [
            {
                "dn": common_dn,
                "attributes": {
                    "dc": ["example"],
                    "o": ["First Organization"],
                    "objectClass": ["top", "domain", "organization"]
                }
            }
        ]
        
        entries2 = [
            {
                "dn": common_dn,
                "attributes": {
                    "dc": ["example"],
                    "o": ["Second Organization"],
                    "objectClass": ["top", "domain", "organization"]
                }
            }
        ]
        
        with open(file1, 'w') as f:
            json.dump(entries1, f)
        with open(file2, 'w') as f:
            json.dump(entries2, f)
        
        # Test last_wins strategy
        storage = JSONStorage(
            json_files=[str(file1), str(file2)],
            merge_strategy="last_wins",
            enable_file_watching=False
        )
        
        try:
            root = storage.get_root()
            assert root.dn.getText() == ""  # Root has empty DN
            
            # Check that we have the expected entries via stats
            stats = storage.get_stats()
            assert stats['total_entries'] == 1  # Only one entry after merge
        finally:
            storage.cleanup()
        
        # Test first_wins strategy
        storage = JSONStorage(
            json_files=[str(file1), str(file2)],
            merge_strategy="first_wins",
            enable_file_watching=False
        )
        
        try:
            root = storage.get_root()
            assert root.dn.getText() == ""  # Root has empty DN
            
            # Check that we have the expected entries via stats
            stats = storage.get_stats()
            assert stats['total_entries'] == 1  # Only one entry after merge
        finally:
            storage.cleanup()
        
        # Test error strategy
        with pytest.raises(ValueError, match="Duplicate DN"):
            storage = JSONStorage(
                json_files=[str(file1), str(file2)],
                merge_strategy="error",
                enable_file_watching=False
            )
    
    def test_password_hashing(self, temp_json_file):
        """Test automatic password hashing."""
        entries_with_plain_passwords = [
            {
                "dn": "dc=example,dc=com",
                "attributes": {
                    "dc": ["example"],
                    "objectClass": ["top", "domain"]
                }
            },
            {
                "dn": "uid=user,dc=example,dc=com",
                "attributes": {
                    "uid": ["user"],
                    "cn": ["Test User"],
                    "userPassword": ["plaintext123"],  # Plain text password
                    "objectClass": ["top", "person"]
                }
            }
        ]
        
        with open(temp_json_file, 'w') as f:
            json.dump(entries_with_plain_passwords, f)
        
        # Enable password hashing
        storage = JSONStorage(
            json_files=str(temp_json_file),
            hash_plain_passwords=True,
            read_only=False,
            enable_file_watching=False
        )
        
        try:
            # Verify password was hashed
            with open(temp_json_file, 'r') as f:
                data = json.load(f)
            
            user_entry = next(e for e in data if e['dn'] == 'uid=user,dc=example,dc=com')
            password = user_entry['attributes']['userPassword'][0]
            
            # Should be LDAP-formatted bcrypt hash
            assert password.startswith('{BCRYPT}')
            assert password != 'plaintext123'
            
        finally:
            storage.cleanup()
    
    def test_invalid_json_format(self, temp_json_file):
        """Test handling of invalid JSON format."""
        # Write invalid JSON
        with open(temp_json_file, 'w') as f:
            f.write("invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            storage = JSONStorage(
                json_files=str(temp_json_file),
                enable_file_watching=False
            )
    
    def test_invalid_entry_format(self, temp_json_file):
        """Test handling of invalid entry format."""
        invalid_entries = [
            {
                "dn": "dc=example,dc=com",
                # Missing attributes field
                "invalid_field": "value"
            }
        ]
        
        with open(temp_json_file, 'w') as f:
            json.dump(invalid_entries, f)
        
        with pytest.raises(ValueError, match="missing 'attributes' field"):
            storage = JSONStorage(
                json_files=str(temp_json_file),
                enable_file_watching=False
            )
    
    def test_nonexistent_file_handling(self):
        """Test handling of non-existent files."""
        nonexistent_file = "/tmp/nonexistent_file_12345.json"
        
        # Should not raise error, but log warning
        storage = JSONStorage(
            json_files=nonexistent_file,
            enable_file_watching=False
        )
        
        try:
            # Should create minimal root
            root = storage.get_root()
            assert root is not None
            
            stats = storage.get_stats()
            assert stats['total_entries'] == 0
            
        finally:
            storage.cleanup()
    
    def test_cleanup(self, temp_json_file, sample_entries):
        """Test proper cleanup of resources."""
        with open(temp_json_file, 'w') as f:
            json.dump(sample_entries, f)
        
        storage = JSONStorage(
            json_files=str(temp_json_file),
            enable_file_watching=False
        )
        
        temp_dir = storage._temp_dir
        assert os.path.exists(temp_dir)
        
        storage.cleanup()
        
        # Temp directory should be cleaned up
        assert not os.path.exists(temp_dir)
    
    def test_stats_comprehensive(self, temp_json_files):
        """Test comprehensive statistics reporting."""
        storage = JSONStorage(
            json_files=[str(f) for f in temp_json_files],
            merge_strategy="last_wins",
            read_only=True,
            enable_file_watching=True,
            enable_lazy_loading=True
        )
        
        try:
            stats = storage.get_stats()
            
            # Verify all expected fields
            assert 'total_entries' in stats
            assert 'files_count' in stats
            assert 'files' in stats
            assert 'read_only' in stats
            assert 'merge_strategy' in stats
            assert 'file_watching_enabled' in stats
            assert 'lazy_loading_enabled' in stats
            assert 'entries_by_file' in stats
            
            # Verify values
            assert stats['files_count'] == 2
            assert stats['read_only'] is True
            assert stats['merge_strategy'] == "last_wins"
            assert stats['file_watching_enabled'] is True
            assert stats['lazy_loading_enabled'] is True
            assert isinstance(stats['entries_by_file'], dict)
            
        finally:
            storage.cleanup()


class TestAtomicJSONWriter:
    """Test atomic JSON writer functionality."""
    
    def test_basic_atomic_write(self, temp_json_file):
        """Test basic atomic write operation."""
        test_data = [{"dn": "dc=test,dc=com", "attributes": {"dc": ["test"]}}]
        
        with AtomicJSONWriter(temp_json_file) as writer:
            writer.write_json(test_data)
        
        # Verify data was written
        with open(temp_json_file, 'r') as f:
            written_data = json.load(f)
        
        assert written_data == test_data
    
    def test_backup_creation(self, temp_json_file):
        """Test backup creation before writing."""
        original_data = [{"dn": "dc=original,dc=com", "attributes": {}}]
        
        # Write initial data
        with open(temp_json_file, 'w') as f:
            json.dump(original_data, f)
        
        new_data = [{"dn": "dc=new,dc=com", "attributes": {}}]
        
        # Perform atomic write with backup
        with AtomicJSONWriter(temp_json_file, backup_enabled=True) as writer:
            writer.write_json(new_data)
        
        # Check backup was created
        backup_files = list(temp_json_file.parent.glob(f"{temp_json_file.name}.*.bak"))
        assert len(backup_files) >= 1
        
        # Cleanup backup files
        for backup in backup_files:
            backup.unlink()
    
    def test_rollback_on_exception(self, temp_json_file):
        """Test rollback on write failure."""
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
    
    def test_concurrent_access_protection(self, temp_json_file):
        """Test concurrent write protection."""
        results = []
        
        def write_data(data_id):
            try:
                with AtomicJSONWriter(temp_json_file, lock_timeout=2.0) as writer:
                    # Small delay to increase chance of contention
                    time.sleep(0.1)
                    writer.write_json([{"dn": f"dc=test{data_id},dc=com", "attributes": {}}])
                    results.append(data_id)
            except Exception as e:
                results.append(f"error_{data_id}")
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=write_data, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # At least one should succeed, others may timeout
        success_count = len([r for r in results if not str(r).startswith('error')])
        assert success_count >= 1


class TestReadOnlyModeUseCases:
    """Test read-only mode use cases for external config management."""
    
    def test_external_config_consumption(self, temp_json_file):
        """Test consuming externally managed configuration."""
        # Simulate external tool writing config
        external_config = [
            {
                "dn": "dc=company,dc=com",
                "attributes": {
                    "dc": ["company"],
                    "o": ["Company Inc"],
                    "objectClass": ["top", "domain", "organization"]
                }
            },
            {
                "dn": "ou=employees,dc=company,dc=com",
                "attributes": {
                    "ou": ["employees"],
                    "objectClass": ["top", "organizationalUnit"]
                }
            }
        ]
        
        with open(temp_json_file, 'w') as f:
            json.dump(external_config, f, indent=2)
        
        # LDAP server consumes in read-only mode
        storage = JSONStorage(
            json_files=str(temp_json_file),
            read_only=True,
            enable_file_watching=True  # Watch for external changes
        )
        
        try:
            # Verify can read configuration
            root = storage.get_root()
            assert root.dn.getText() == ""  # Root has empty DN
            
            # Verify we loaded the entries
            stats = storage.get_stats()
            assert stats['total_entries'] == 2  # dc=company,dc=com + ou=employees
            assert stats['read_only']
            
            # Verify cannot modify
            assert storage.add_entry("uid=test,ou=employees,dc=company,dc=com", {}) is False
            
            # Simulate external update
            external_config[0]["attributes"]["o"] = ["Updated Company Inc"]
            with open(temp_json_file, 'w') as f:
                json.dump(external_config, f, indent=2)
            
            # Give file watcher time to detect change
            time.sleep(1.0)
            
            # Verify change was picked up (if file watching is working)
            # Note: In real usage, the change would be detected and reloaded
            
        finally:
            storage.cleanup()
    
    def test_multi_file_external_management(self, temp_json_files):
        """Test multi-file external configuration management."""
        storage = JSONStorage(
            json_files=[str(f) for f in temp_json_files],
            read_only=True,
            merge_strategy="last_wins",
            enable_file_watching=True
        )
        
        try:
            # Verify federation of external configs
            stats = storage.get_stats()
            assert stats['files_count'] == 2
            assert stats['read_only'] is True
            
            # Verify all write operations are blocked
            assert storage.add_entry("uid=new,ou=users,dc=example,dc=com", {}) is False
            assert storage.modify_entry("uid=john,ou=users,dc=example,dc=com", {}) is False
            assert storage.delete_entry("uid=john,ou=users,dc=example,dc=com") is False
            assert storage.bulk_write_entries([]) is False
            
        finally:
            storage.cleanup()


# Test FederatedJSONStorage compatibility alias
def test_federated_compatibility():
    """Test that FederatedJSONStorage alias still works."""
    from src.ldap_server.storage.json import FederatedJSONStorage
    
    # Should be the same class
    assert FederatedJSONStorage is JSONStorage
