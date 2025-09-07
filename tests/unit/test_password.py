"""
Test cases for password authentication functionality.
"""

import pytest
from ldap_server.auth.password import PasswordManager, generate_secure_password


class TestPasswordManager:
    """Test cases for PasswordManager."""
    
    def test_hash_password_bcrypt_format(self):
        """Test that hashed passwords are in correct LDAP format."""
        password = "testpassword123"
        hashed = PasswordManager.hash_password(password)
        
        # Should start with {BCRYPT}
        assert hashed.startswith("{BCRYPT}")
        
        # Should be longer than original password
        assert len(hashed) > len(password)
        
        # Should be base64-encoded bcrypt hash
        import base64
        try:
            # Extract and decode the hash part
            b64_part = hashed[8:]  # Remove {BCRYPT} prefix
            decoded = base64.b64decode(b64_part.encode('ascii'))
            # Bcrypt hashes are 60 bytes
            assert len(decoded) == 60
        except Exception:
            pytest.fail("Hash is not valid base64-encoded bcrypt")
    
    def test_verify_correct_password(self):
        """Test password verification with correct password."""
        password = "mypassword123"
        hashed = PasswordManager.hash_password(password)
        
        # Correct password should verify
        assert PasswordManager.verify_password(password, hashed) is True
    
    def test_verify_incorrect_password(self):
        """Test password verification with incorrect password."""
        password = "mypassword123"
        wrong_password = "wrongpassword"
        hashed = PasswordManager.hash_password(password)
        
        # Wrong password should not verify
        assert PasswordManager.verify_password(wrong_password, hashed) is False
    
    def test_verify_plain_text_backwards_compatibility(self):
        """Test that plain text passwords still work for backwards compatibility."""
        password = "plaintext"
        
        # Plain text comparison should work
        assert PasswordManager.verify_password(password, password) is True
        assert PasswordManager.verify_password(password, "different") is False
    
    def test_different_rounds(self):
        """Test password hashing with different round counts."""
        password = "testpassword"
        
        # Test valid round ranges
        for rounds in [4, 10, 12, 15]:
            hashed = PasswordManager.hash_password(password, rounds)
            assert PasswordManager.verify_password(password, hashed) is True
    
    def test_invalid_rounds(self):
        """Test that invalid round counts raise errors."""
        password = "testpassword"
        
        # Too low
        with pytest.raises(ValueError, match="Bcrypt rounds must be between 4 and 31"):
            PasswordManager.hash_password(password, rounds=3)
        
        # Too high
        with pytest.raises(ValueError, match="Bcrypt rounds must be between 4 and 31"):
            PasswordManager.hash_password(password, rounds=32)
    
    def test_empty_password(self):
        """Test handling of empty passwords."""
        # Empty password should hash without error
        hashed = PasswordManager.hash_password("")
        assert PasswordManager.verify_password("", hashed) is True
        assert PasswordManager.verify_password("nonempty", hashed) is False
    
    def test_unicode_passwords(self):
        """Test handling of unicode characters in passwords."""
        password = "pässwörd123🔒"
        hashed = PasswordManager.hash_password(password)
        
        assert PasswordManager.verify_password(password, hashed) is True
        assert PasswordManager.verify_password("different", hashed) is False
    
    def test_invalid_input_types(self):
        """Test handling of invalid input types."""
        # Non-string password for hashing
        with pytest.raises(ValueError, match="Password must be a string"):
            PasswordManager.hash_password(123)
        
        # Non-string inputs for verification
        assert PasswordManager.verify_password(123, "hash") is False
        assert PasswordManager.verify_password("password", 123) is False
    
    def test_malformed_hash_verification(self):
        """Test verification with malformed hashes."""
        password = "testpassword"
        
        # Malformed bcrypt hash
        assert PasswordManager.verify_password(password, "{BCRYPT}invalid") is False
        
        # Unknown hash format
        assert PasswordManager.verify_password(password, "{UNKNOWN}hash") is False
        
        # Empty hash
        assert PasswordManager.verify_password(password, "") is False


class TestSecurePasswordGeneration:
    """Test cases for secure password generation."""
    
    def test_generate_secure_password_default_length(self):
        """Test default password generation."""
        password = generate_secure_password()
        
        # Should be 16 characters by default
        assert len(password) == 16
        
        # Should contain various character types
        assert any(c.islower() for c in password)  # lowercase
        assert any(c.isupper() for c in password)  # uppercase
    
    def test_generate_secure_password_custom_length(self):
        """Test password generation with custom length."""
        for length in [12, 20, 32]:
            password = generate_secure_password(length)
            assert len(password) == length
    
    def test_generate_secure_password_minimum_length(self):
        """Test that passwords must meet minimum length requirement."""
        with pytest.raises(ValueError, match="Password length must be at least 12"):
            generate_secure_password(8)
    
    def test_generate_secure_password_uniqueness(self):
        """Test that generated passwords are unique."""
        passwords = [generate_secure_password() for _ in range(10)]
        
        # All passwords should be unique
        assert len(set(passwords)) == len(passwords)


class TestPasswordUpgrade:
    """Test cases for password upgrade functionality."""
    
    def test_upgrade_plain_passwords(self):
        """Test upgrading plain text passwords in entry format."""
        entries = [
            {
                "dn": "uid=test,ou=people,dc=example,dc=com",
                "attributes": {
                    "objectClass": ["inetOrgPerson"],
                    "uid": ["test"],
                    "userPassword": ["plaintext123"]
                }
            }
        ]
        
        upgraded = PasswordManager.upgrade_plain_passwords(entries)
        
        # Should have one entry
        assert len(upgraded) == 1
        
        # Password should be hashed
        password = upgraded[0]["attributes"]["userPassword"][0]
        assert password.startswith("{BCRYPT}")
        
        # Should verify correctly
        assert PasswordManager.verify_password("plaintext123", password)
    
    def test_upgrade_preserves_existing_hashes(self):
        """Test that existing hashed passwords are preserved."""
        existing_hash = PasswordManager.hash_password("existing")
        
        entries = [
            {
                "dn": "uid=test,ou=people,dc=example,dc=com",
                "attributes": {
                    "objectClass": ["inetOrgPerson"],
                    "uid": ["test"],
                    "userPassword": [existing_hash]
                }
            }
        ]
        
        upgraded = PasswordManager.upgrade_plain_passwords(entries)
        
        # Hash should be unchanged
        assert upgraded[0]["attributes"]["userPassword"][0] == existing_hash


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
