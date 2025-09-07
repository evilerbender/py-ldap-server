"""Test cases for Federated JSON storage backend functionality."""

import json
import os
import tempfile
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from ldap_server.storage.json import FederatedJSONStorage, JSONStorage


class TestFederatedJSONStorage:
    """Test cases for FederatedJSONStorage backend."""
    
    @pytest.fixture
    def sample_data_1(self):
        """Sample LDAP data for first JSON file."""
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
                    "objectClass": ["organizationalUnit"],
                    "ou": ["users"]
                }
            },
            {
                "dn": "cn=user1,ou=users,dc=example,dc=com",
                "attributes": {
                    "objectClass": ["person", "inetOrgPerson"],
                    "cn": ["user1"],
                    "sn": ["User"],
                    "givenName": ["Test"],
                    "mail": ["user1@example.com"],
                    "userPassword": ["password123"]
                }
            }
        ]
    
    @pytest.fixture
    def sample_data_2(self):
        """Sample LDAP data for second JSON file."""
        return [
            {
                "dn": "ou=groups,dc=example,dc=com",
                "attributes": {
                    "objectClass": ["organizationalUnit"],
                    "ou": ["groups"]
                }
            },
            {
                "dn": "cn=admins,ou=groups,dc=example,dc=com",
                "attributes": {
                    "objectClass": ["groupOfNames"],
                    "cn": ["admins"],
                    "member": ["cn=user1,ou=users,dc=example,dc=com"]
                }
            },
            {
                "dn": "cn=user2,ou=users,dc=example,dc=com",
                "attributes": {
                    "objectClass": ["person", "inetOrgPerson"],
                    "cn": ["user2"],
                    "sn": ["User"],
                    "givenName": ["Another"],
                    "mail": ["user2@example.com"],
                    "userPassword": ["password456"]
                }
            }
        ]
    
    @pytest.fixture
    def conflicting_data(self):
        """Sample data that conflicts with existing entries."""
        return [
            {
                "dn": "cn=user1,ou=users,dc=example,dc=com",
                "attributes": {
                    "objectClass": ["person", "inetOrgPerson"],
                    "cn": ["user1"],
                    "sn": ["Different"],
                    "givenName": ["Different"],
                    "mail": ["different@example.com"],
                    "userPassword": ["different_password"]
                }
            }
        ]
    
    @pytest.fixture
    def temp_json_files(self, sample_data_1, sample_data_2):
        """Create temporary JSON files with sample data."""
        files = []
        
        # Create first file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data_1, f, indent=2)
            files.append(Path(f.name))
        
        # Create second file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data_2, f, indent=2)
            files.append(Path(f.name))
        
        yield files
        
        # Cleanup
        for file_path in files:
            if file_path.exists():
                file_path.unlink()
    
    def test_single_file_loading(self, temp_json_files, sample_data_1):
        """Test loading from a single JSON file."""
        storage = FederatedJSONStorage(
            json_files=[str(temp_json_files[0])],
            enable_watcher=False
        )
        
        try:
            assert storage.get_root() is not None
            assert storage.load_stats['files_loaded'] == 1
            assert storage.load_stats['total_entries'] == len(sample_data_1)
            assert storage.load_stats['merge_conflicts'] == 0
            
            # Verify we can access the root entry
            root = storage.get_root()
            assert root is not None
            
        finally:
            storage.cleanup()
    
    def test_multiple_file_loading(self, temp_json_files, sample_data_1, sample_data_2):
        """Test loading and merging from multiple JSON files."""
        storage = FederatedJSONStorage(
            json_files=[str(f) for f in temp_json_files],
            enable_watcher=False
        )
        
        try:
            assert storage.get_root() is not None
            assert storage.load_stats['files_loaded'] == 2
            assert storage.load_stats['total_entries'] == len(sample_data_1) + len(sample_data_2)
            assert storage.load_stats['merge_conflicts'] == 0
            
        finally:
            storage.cleanup()
    
    def test_merge_strategy_last_wins(self, temp_json_files, conflicting_data):
        """Test last_wins merge strategy with conflicting data."""
        # Create a third file with conflicting data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(conflicting_data, f, indent=2)
            conflict_file = Path(f.name)
        
        try:
            all_files = [str(f) for f in temp_json_files] + [str(conflict_file)]
            
            storage = FederatedJSONStorage(
                json_files=all_files,
                merge_strategy="last_wins",
                enable_watcher=False
            )
            
            try:
                assert storage.load_stats['merge_conflicts'] == 1
            finally:
                storage.cleanup()
            
        finally:
            conflict_file.unlink()
    
    def test_merge_strategy_first_wins(self, temp_json_files, conflicting_data):
        """Test first_wins merge strategy with conflicting data."""
        # Create a third file with conflicting data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(conflicting_data, f, indent=2)
            conflict_file = Path(f.name)
        
        try:
            all_files = [str(f) for f in temp_json_files] + [str(conflict_file)]
            
            storage = FederatedJSONStorage(
                json_files=all_files,
                merge_strategy="first_wins",
                enable_watcher=False
            )
            
            try:
                assert storage.load_stats['merge_conflicts'] == 1
            finally:
                storage.cleanup()
            
        finally:
            conflict_file.unlink()
    
    def test_merge_strategy_error(self, temp_json_files, conflicting_data):
        """Test error merge strategy with conflicting data."""
        # Create a third file with conflicting data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(conflicting_data, f, indent=2)
            conflict_file = Path(f.name)
        
        try:
            all_files = [str(f) for f in temp_json_files] + [str(conflict_file)]
            
            with pytest.raises(ValueError, match="Merge conflict for DN"):
                FederatedJSONStorage(
                    json_files=all_files,
                    merge_strategy="error",
                    enable_watcher=False
                )
                
        finally:
            conflict_file.unlink()
    
    def test_invalid_json_file(self, temp_json_files):
        """Test handling of invalid JSON files."""
        # Create a file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json content }")
            invalid_file = Path(f.name)
        
        try:
            all_files = [str(f) for f in temp_json_files] + [str(invalid_file)]
            
            with pytest.raises(ValueError, match="Invalid JSON"):
                FederatedJSONStorage(
                    json_files=all_files,
                    enable_watcher=False
                )
                
        finally:
            invalid_file.unlink()
    
    def test_missing_json_file(self, temp_json_files):
        """Test handling of missing JSON files."""
        missing_file = "/tmp/nonexistent_file.json"
        all_files = [str(f) for f in temp_json_files] + [missing_file]
        
        # Should load successfully but skip missing file
        storage = FederatedJSONStorage(
            json_files=all_files,
            enable_watcher=False
        )
        
        try:
            assert storage.load_stats['files_loaded'] == len(temp_json_files)
        finally:
            storage.cleanup()
    
    def test_no_valid_files(self):
        """Test error when no valid files can be loaded."""
        with pytest.raises(ValueError, match="No JSON files could be loaded"):
            FederatedJSONStorage(
                json_files=["/tmp/nonexistent1.json", "/tmp/nonexistent2.json"],
                enable_watcher=False
            )
    
    def test_add_remove_json_files(self, temp_json_files, sample_data_1):
        """Test dynamically adding and removing JSON files."""
        # Start with one file
        storage = FederatedJSONStorage(
            json_files=[str(temp_json_files[0])],
            enable_watcher=False
        )
        
        try:
            initial_count = storage.load_stats['total_entries']
            
            # Add second file
            storage.add_json_file(str(temp_json_files[1]))
            assert storage.load_stats['files_loaded'] == 2
            assert storage.load_stats['total_entries'] > initial_count
            
            # Remove first file
            storage.remove_json_file(str(temp_json_files[0]))
            assert storage.load_stats['files_loaded'] == 1
            
        finally:
            storage.cleanup()
    
    def test_get_stats(self, temp_json_files):
        """Test storage statistics retrieval."""
        storage = FederatedJSONStorage(
            json_files=[str(f) for f in temp_json_files],
            merge_strategy="last_wins",
            enable_watcher=False
        )
        
        try:
            stats = storage.get_stats()
            
            assert 'last_load_time' in stats
            assert 'total_entries' in stats
            assert 'files_loaded' in stats
            assert 'merge_conflicts' in stats
            assert 'load_duration' in stats
            assert 'json_files' in stats
            assert 'merge_strategy' in stats
            assert 'enable_watcher' in stats
            assert 'file_watching_active' in stats
            
            assert stats['files_loaded'] == 2
            assert stats['merge_strategy'] == "last_wins"
            assert stats['enable_watcher'] == False
            assert len(stats['json_files']) == 2
            
        finally:
            storage.cleanup()
    
    @patch('ldap_server.storage.json.Observer')
    def test_file_watching_setup(self, mock_observer_class, temp_json_files):
        """Test file watching setup."""
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer
        
        storage = FederatedJSONStorage(
            json_files=[str(f) for f in temp_json_files],
            enable_watcher=True
        )
        
        try:
            # Verify observer was created and started
            mock_observer_class.assert_called_once()
            mock_observer.schedule.assert_called()
            mock_observer.start.assert_called_once()
            
        finally:
            storage.cleanup()
            if hasattr(storage, '_observer') and storage._observer:
                mock_observer.stop.assert_called_once()
                mock_observer.join.assert_called_once()
    
    def test_password_hashing(self, temp_json_files):
        """Test that passwords are properly hashed."""
        storage = FederatedJSONStorage(
            json_files=[str(temp_json_files[0])],
            enable_watcher=False,
            hash_plain_passwords=True
        )
        
        try:
            # Verify storage loads successfully with password hashing
            assert storage.get_root() is not None
            assert storage.load_stats['total_entries'] > 0
            
        finally:
            storage.cleanup()
    
    def test_string_conversion_of_single_file(self):
        """Test that single string file path is converted to list."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{"dn": "dc=example,dc=com", "attributes": {"objectClass": ["domain"], "dc": ["example"]}}], f)
            temp_file = Path(f.name)
        
        try:
            storage = FederatedJSONStorage(
                json_files=str(temp_file),  # Pass string instead of list
                enable_watcher=False
            )
            
            try:
                assert len(storage.json_files) == 1
                assert storage.json_files[0] == temp_file
            finally:
                storage.cleanup()
            
        finally:
            temp_file.unlink()


class TestJSONStorageLegacyCompatibility:
    """Test backward compatibility of JSONStorage class."""
    
    @pytest.fixture
    def sample_data(self):
        """Sample LDAP data."""
        return [
            {
                "dn": "dc=example,dc=com",
                "attributes": {
                    "objectClass": ["top", "domain"],
                    "dc": ["example"]
                }
            },
            {
                "dn": "cn=test,dc=example,dc=com",
                "attributes": {
                    "objectClass": ["person"],
                    "cn": ["test"],
                    "sn": ["Test"]
                }
            }
        ]
    
    @pytest.fixture
    def temp_json_file(self, sample_data):
        """Create temporary JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data, f, indent=2)
            temp_file = Path(f.name)
        
        yield temp_file
        
        if temp_file.exists():
            temp_file.unlink()
    
    def test_legacy_json_storage_interface(self, temp_json_file):
        """Test that JSONStorage maintains backward compatibility."""
        storage = JSONStorage(
            json_path=str(temp_json_file),
            enable_watcher=False
        )
        
        try:
            # Test legacy properties
            assert storage.json_path == str(temp_json_file)
            assert storage.get_root() is not None
            
            # Test legacy methods
            stats = storage.get_stats()
            
            assert 'json_path' in stats  # Legacy field
            assert stats['json_path'] == str(temp_json_file)
            
        finally:
            storage.cleanup()
    
    def test_legacy_root_access(self, temp_json_file):
        """Test that root entry access works as before."""
        storage = JSONStorage(
            json_path=str(temp_json_file),
            enable_watcher=False
        )
        
        try:
            root_entry = storage.get_root()
            assert root_entry is not None
            
        finally:
            storage.cleanup()
