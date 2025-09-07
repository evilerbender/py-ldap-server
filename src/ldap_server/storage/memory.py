"""
In-memory storage backend for LDAP directory data.
"""

from typing import Dict, Any
from ldaptor.ldiftree import LDIFTreeEntry
import tempfile
import os

from ldap_server.auth.password import PasswordManager


class MemoryStorage:
    """
    In-memory LDAP directory storage using LDIFTreeEntry.
    """
    
    def __init__(self, base_dn: str = "dc=example,dc=com"):
        """
        Initialize the in-memory storage with a base DN.
        
        Args:
            base_dn: The base distinguished name for the directory tree
        """
        self.base_dn = base_dn
        self._temp_dir = tempfile.mkdtemp(prefix="ldap_server_")
        self.root = LDIFTreeEntry(self._temp_dir)
        self._initialize_sample_data()
    
    def _initialize_sample_data(self) -> None:
        """Initialize the directory with sample data using a more straightforward approach."""
        try:
            # Create base structure similar to Ldaptor cookbook examples
            # Root: dc=com
            dc_com = self.root.addChild("dc=com", {
                "objectClass": ["dcObject"],
                "dc": ["com"]
            })
            
            # Second level: dc=example,dc=com
            dc_example = dc_com.addChild("dc=example", {
                "objectClass": ["dcObject", "organization"],
                "dc": ["example"],
                "o": ["Example Organization"],
                "description": ["Sample LDAP directory for py-ldap-server"]
            })
            
            # Add organizational units
            people_ou = dc_example.addChild("ou=people", {
                "objectClass": ["organizationalUnit"],
                "ou": ["people"],
                "description": ["People in the organization"]
            })
            
            groups_ou = dc_example.addChild("ou=groups", {
                "objectClass": ["organizationalUnit"], 
                "ou": ["groups"],
                "description": ["Groups in the organization"]
            })
            
            # Add sample users
            self._add_sample_users(people_ou)
            self._add_sample_groups(groups_ou)
            
        except Exception as e:
            print(f"Error initializing sample data: {e}")
            import traceback
            traceback.print_exc()
    
    def _add_sample_users(self, people_ou: LDIFTreeEntry) -> None:
        """Add sample user entries with securely hashed passwords."""
        users = [
            {
                "dn": "uid=admin",
                "attrs": {
                    "objectClass": ["inetOrgPerson", "posixAccount"],
                    "uid": ["admin"],
                    "cn": ["LDAP Administrator"],
                    "sn": ["Administrator"],
                    "givenName": ["LDAP"],
                    "mail": ["admin@example.com"],
                    "userPassword": [PasswordManager.hash_password("admin123")],
                    "uidNumber": ["1000"],
                    "gidNumber": ["1000"],
                    "homeDirectory": ["/home/admin"],
                    "loginShell": ["/bin/bash"]
                }
            },
            {
                "dn": "uid=testuser",
                "attrs": {
                    "objectClass": ["inetOrgPerson", "posixAccount"],
                    "uid": ["testuser"],
                    "cn": ["Test User"],
                    "sn": ["User"],
                    "givenName": ["Test"],
                    "mail": ["testuser@example.com"],
                    "userPassword": [PasswordManager.hash_password("password123")],
                    "uidNumber": ["1001"],
                    "gidNumber": ["1001"],
                    "homeDirectory": ["/home/testuser"],
                    "loginShell": ["/bin/bash"]
                }
            }
        ]
        
        for user in users:
            people_ou.addChild(user["dn"], user["attrs"])
    
    def _add_sample_groups(self, groups_ou: LDIFTreeEntry) -> None:
        """Add sample group entries."""
        groups = [
            {
                "dn": "cn=admins",
                "attrs": {
                    "objectClass": ["groupOfNames"],
                    "cn": ["admins"],
                    "description": ["System administrators"],
                    "member": ["uid=admin,ou=people,dc=example,dc=com"]
                }
            },
            {
                "dn": "cn=users",
                "attrs": {
                    "objectClass": ["groupOfNames"],
                    "cn": ["users"],
                    "description": ["Regular users"],
                    "member": [
                        "uid=admin,ou=people,dc=example,dc=com",
                        "uid=testuser,ou=people,dc=example,dc=com"
                    ]
                }
            }
        ]
        
        for group in groups:
            groups_ou.addChild(group["dn"], group["attrs"])
    
    def get_root(self) -> LDIFTreeEntry:
        """Get the root entry of the directory tree."""
        return self.root
    
    def cleanup(self) -> None:
        """Clean up temporary directory."""
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)
