"""Test cases for JSON storage backend functionality."""

import json
import os
import tempfile
import pytest

from ldap_server.storage.json import JSONStorage


class TestJSONStorage:
    """Test cases for JSONStorage backend."""
    
    def test_initialization_simple(self):
        """Test JSONStorage initialization with simple data."""
        # Create temporary file
        fd, json_path = tempfile.mkstemp(suffix='.json')
        
        try:
            # Write simple data
            simple_data = [
                {
                    "dn": "dc=test,dc=com",
                    "attributes": {
                        "objectClass": ["domain"],
                        "dc": ["test"]
                    }
                }
            ]
            
            with os.fdopen(fd, 'w') as f:
                json.dump(simple_data, f)
            
            # Test initialization
            storage = JSONStorage(json_path, hash_plain_passwords=False, enable_watcher=False)
            
            try:
                # Basic checks
                assert storage.json_path == json_path
                assert storage.get_root() is not None
                assert os.path.exists(storage._temp_dir)
            finally:
                storage.cleanup()
                
        finally:
            try:
                os.unlink(json_path)
            except (OSError, FileNotFoundError):
                pass

    def test_load_json_entries_valid(self):
        """Test loading valid JSON entries."""
        fd, json_path = tempfile.mkstemp(suffix='.json')
        
        try:
            sample_data = [
                {
                    "dn": "dc=example,dc=com",
                    "attributes": {
                        "objectClass": ["domain"],
                        "dc": ["example"]
                    }
                }
            ]
            
            with os.fdopen(fd, 'w') as f:
                json.dump(sample_data, f)
            
            entries = JSONStorage._load_json_entries(json_path)
            
            assert len(entries) == 1
            assert entries[0]["dn"] == "dc=example,dc=com"
            assert "objectClass" in entries[0]["attributes"]
            
        finally:
            try:
                os.unlink(json_path)
            except (OSError, FileNotFoundError):
                pass

    def test_load_json_entries_invalid_format(self):
        """Test loading invalid JSON format."""
        fd, json_path = tempfile.mkstemp(suffix='.json')
        
        try:
            # Write invalid JSON (not a list)
            with os.fdopen(fd, 'w') as f:
                json.dump({"invalid": "format"}, f)
            
            with pytest.raises(ValueError, match="JSON root must be a list"):
                JSONStorage._load_json_entries(json_path)
                
        finally:
            try:
                os.unlink(json_path)
            except (OSError, FileNotFoundError):
                pass

    def test_malformed_json_file(self):
        """Test handling of malformed JSON file."""
        fd, json_path = tempfile.mkstemp(suffix='.json')
        
        try:
            # Write malformed JSON
            with os.fdopen(fd, 'w') as f:
                f.write('{"invalid": json content')
            
            with pytest.raises(json.JSONDecodeError):
                JSONStorage(json_path, hash_plain_passwords=False, enable_watcher=False)
                
        finally:
            try:
                os.unlink(json_path)
            except (OSError, FileNotFoundError):
                pass

    def test_nonexistent_json_file(self):
        """Test handling of non-existent JSON file."""
        with pytest.raises(FileNotFoundError):
            JSONStorage('/nonexistent/path/file.json', hash_plain_passwords=False, enable_watcher=False)

    def test_empty_json_file(self):
        """Test handling of empty JSON file."""
        fd, json_path = tempfile.mkstemp(suffix='.json')
        
        try:
            # Write empty list
            with os.fdopen(fd, 'w') as f:
                json.dump([], f)
            
            storage = JSONStorage(json_path, hash_plain_passwords=False, enable_watcher=False)
            
            try:
                root = storage.get_root()
                assert root is not None
                
                # Should have no children
                children = list(root.children())
                assert len(children) == 0
                
            finally:
                storage.cleanup()
                
        finally:
            try:
                os.unlink(json_path)
            except (OSError, FileNotFoundError):
                pass

    def test_cleanup(self):
        """Test cleanup functionality."""
        fd, json_path = tempfile.mkstemp(suffix='.json')
        
        try:
            sample_data = [{"dn": "dc=test,dc=com", "attributes": {"objectClass": ["domain"], "dc": ["test"]}}]
            
            with os.fdopen(fd, 'w') as f:
                json.dump(sample_data, f)
            
            storage = JSONStorage(json_path, hash_plain_passwords=False, enable_watcher=False)
            temp_dir = storage._temp_dir
            
            # Verify temp directory exists
            assert os.path.exists(temp_dir)
            
            # Cleanup
            storage.cleanup()
            
            # Verify temp directory is removed
            assert not os.path.exists(temp_dir)
            
        finally:
            try:
                os.unlink(json_path)
            except (OSError, FileNotFoundError):
                pass