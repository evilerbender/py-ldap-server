"""
Password hashing and verification utilities for LDAP authentication.
"""

import bcrypt
import base64
from typing import Union, Optional


class PasswordManager:
    """
    Secure password management using bcrypt for LDAP userPassword attributes.
    
    Supports multiple password hash formats commonly used in LDAP:
    - {BCRYPT} - bcrypt hashes (recommended)
    - {SSHA} - Salted SHA-1 (legacy support)
    - Plain text (for backwards compatibility, but not recommended)
    """
    
    @staticmethod
    def hash_password(password: str, rounds: int = 12) -> str:
        """
        Hash a password using bcrypt with a salt.
        
        Args:
            password: Plain text password to hash
            rounds: Number of bcrypt rounds (default: 12, recommended: 10-15)
            
        Returns:
            LDAP-formatted bcrypt hash string: {BCRYPT}base64_encoded_hash
        """
        if not isinstance(password, str):
            raise ValueError("Password must be a string")
        
        if rounds < 4 or rounds > 31:
            raise ValueError("Bcrypt rounds must be between 4 and 31")
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Encode in LDAP format
        b64_hash = base64.b64encode(hashed).decode('ascii')
        return f"{{BCRYPT}}{b64_hash}"
    
    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """
        Verify a password against a stored hash.
        
        Args:
            password: Plain text password to verify
            stored_hash: Stored password hash from LDAP
            
        Returns:
            True if password matches, False otherwise
        """
        if not isinstance(password, str) or not isinstance(stored_hash, str):
            return False
        
        try:
            # Handle different hash formats
            if stored_hash.startswith("{BCRYPT}"):
                return PasswordManager._verify_bcrypt(password, stored_hash)
            elif stored_hash.startswith("{SSHA}"):
                return PasswordManager._verify_ssha(password, stored_hash)
            else:
                # Plain text comparison (insecure, for backwards compatibility)
                return password == stored_hash
        except Exception:
            # Any error in verification should return False
            return False
    
    @staticmethod
    def _verify_bcrypt(password: str, stored_hash: str) -> bool:
        """Verify bcrypt hash."""
        try:
            # Remove {BCRYPT} prefix and decode
            b64_hash = stored_hash[8:]  # Remove "{BCRYPT}"
            hash_bytes = base64.b64decode(b64_hash.encode('ascii'))
            
            # Verify password
            return bcrypt.checkpw(password.encode('utf-8'), hash_bytes)
        except Exception:
            return False
    
    @staticmethod
    def _verify_ssha(password: str, stored_hash: str) -> bool:
        """
        Verify SSHA (Salted SHA-1) hash for legacy compatibility.
        Note: SHA-1 is deprecated, this is for legacy support only.
        """
        import hashlib
        
        try:
            # Remove {SSHA} prefix and decode
            b64_hash = stored_hash[6:]  # Remove "{SSHA}"
            hash_bytes = base64.b64decode(b64_hash.encode('ascii'))
            
            # Extract salt (last 4 bytes) and hash (first 20 bytes)
            if len(hash_bytes) < 24:
                return False
            
            salt = hash_bytes[20:]
            stored_sha = hash_bytes[:20]
            
            # Compute SHA-1 with salt
            computed_sha = hashlib.sha1(password.encode('utf-8') + salt).digest()
            
            return computed_sha == stored_sha
        except Exception:
            return False
    
    @staticmethod
    def upgrade_plain_passwords(entries_dict: dict) -> dict:
        """
        Utility function to upgrade plain text passwords to bcrypt hashes.
        
        Args:
            entries_dict: Dictionary of LDAP entries with potential plain passwords
            
        Returns:
            Updated dictionary with hashed passwords
        """
        updated_entries = []
        
        for entry in entries_dict:
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
                        print(f"🔒 Upgraded password for {updated_entry.get('dn', 'unknown')}")
                    else:
                        # Keep existing hashed passwords
                        hashed_passwords.append(password)
                
                attributes["userPassword"] = hashed_passwords
                updated_entry["attributes"] = attributes
            
            updated_entries.append(updated_entry)
        
        return updated_entries


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password.
    
    Args:
        length: Password length (minimum 12)
        
    Returns:
        Secure random password string
    """
    import secrets
    import string
    
    if length < 12:
        raise ValueError("Password length must be at least 12 characters")
    
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# Convenience functions
hash_password = PasswordManager.hash_password
verify_password = PasswordManager.verify_password
