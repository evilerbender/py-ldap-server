"""
LDAP bind authentication handlers.
"""

from twisted.python import log
from ldaptor.protocols.ldap import ldaperrors
from ldaptor.protocols.ldap.distinguishedname import DistinguishedName
from ldaptor.protocols.pureldap import LDAPBindResponse, LDAPResult

from ldap_server.auth.password import PasswordManager


class BindHandler:
    """
    Handles LDAP bind authentication operations.
    """
    
    def __init__(self, storage, password_manager=None, debug=False):
        """
        Initialize bind handler.
        
        Args:
            storage: Storage backend containing user data
            password_manager: Password manager instance for verification
            debug: Enable debug logging
        """
        self.storage = storage
        self.password_manager = password_manager or PasswordManager()
        self.debug = debug
    
    def handle_simple_bind(self, dn_str, password):
        """
        Handle simple bind authentication.
        
        Args:
            dn_str: Distinguished name as string
            password: Plain text password
            
        Returns:
            tuple: (result_code: int, message: str)
        """
        if self.debug:
            log.msg(f"Simple bind attempt for DN: {dn_str}")
        
        # Handle anonymous bind (empty DN and password)
        if not dn_str and not password:
            if self.debug:
                log.msg("Anonymous bind successful")
            return 0, "Anonymous bind successful"
        
        # Reject empty password with non-empty DN (RFC 4513)
        if dn_str and not password:
            if self.debug:
                log.msg(f"Rejecting bind with empty password for DN: {dn_str}")
            return 49, "Invalid credentials"  # invalidCredentials
        
        # Parse and normalize DN
        try:
            dn = DistinguishedName(stringValue=dn_str)
            normalized_dn = dn.getText()
        except Exception as e:
            if self.debug:
                log.msg(f"Invalid DN format: {dn_str} - {e}")
            return 34, "Invalid DN syntax"  # invalidDNSyntax
        
        # Find user entry in storage
        user_entry = self._find_user_entry(normalized_dn)
        if not user_entry:
            if self.debug:
                log.msg(f"User not found: {normalized_dn}")
            return 32, "No such object"  # noSuchObject
        
        # Verify password
        if self._verify_user_password(user_entry, password):
            if self.debug:
                log.msg(f"Bind successful for: {normalized_dn}")
            return 0, "Authentication successful"
        else:
            if self.debug:
                log.msg(f"Password verification failed for: {normalized_dn}")
            return 49, "Invalid credentials"  # invalidCredentials
    
    def _find_user_entry(self, dn_str):
        """
        Find user entry in storage by DN.
        
        Args:
            dn_str: Normalized DN string
            
        Returns:
            Entry object or None if not found
        """
        try:
            if self.debug:
                log.msg(f"Looking for user entry: {dn_str}")
            
            # Check if this is a mock storage (for testing)
            if hasattr(self.storage, 'find_entry'):
                return self.storage.find_entry(dn_str)
            
            # Otherwise use LDIFTreeEntry navigation
            root = self.storage.root
            
            if self.debug:
                log.msg(f"Root children: {list(root.children())}")
            
            # Parse DN components
            dn = DistinguishedName(stringValue=dn_str)
            
            # Navigate to the entry
            current_entry = root
            dn_components = list(reversed(list(dn.split())))
            
            if self.debug:
                log.msg(f"DN components (reversed): {[c.getText() for c in dn_components]}")
            
            # Skip the root component if it's empty
            if dn_components and dn_components[0].getText() == "":
                dn_components = dn_components[1:]
            
            for i, component in enumerate(dn_components):
                component_str = component.getText()
                found = False
                
                if self.debug:
                    log.msg(f"Looking for component {i}: {component_str}")
                    children_list = list(current_entry.children())
                    log.msg(f"Available children: {[child.name for child in children_list]}")
                
                # Look for child with matching RDN
                for child in current_entry.children():
                    if child.name.lower() == component_str.lower():
                        current_entry = child
                        found = True
                        if self.debug:
                            log.msg(f"Found component: {component_str}")
                        break
                
                if not found:
                    if self.debug:
                        log.msg(f"Component not found: {component_str}")
                    return None
            
            if self.debug:
                log.msg(f"Found entry: {current_entry}")
            return current_entry
            
        except Exception as e:
            if self.debug:
                log.msg(f"Error finding user entry {dn_str}: {e}")
            return None
    
    def _verify_user_password(self, user_entry, password):
        """
        Verify user password against stored hash.
        
        Args:
            user_entry: LDIFTreeEntry object
            password: Plain text password to verify
            
        Returns:
            bool: True if password is valid
        """
        try:
            # Get userPassword attribute from LDIFTreeEntry
            user_passwords = user_entry.get('userPassword', [])
            
            if not user_passwords:
                if self.debug:
                    log.msg("No userPassword attribute found")
                return False
            
            # Try to verify against any of the stored password hashes
            for stored_password in user_passwords:
                if isinstance(stored_password, bytes):
                    stored_password = stored_password.decode('utf-8')
                
                if self.password_manager.verify_password(password, stored_password):
                    return True
            
            return False
            
        except Exception as e:
            if self.debug:
                log.msg(f"Error verifying password: {e}")
            return False
    
    def handle_sasl_bind(self, dn_str, mechanism, credentials):
        """
        Handle SASL bind authentication (future implementation).
        
        Args:
            dn_str: Distinguished name as string
            mechanism: SASL mechanism name
            credentials: SASL credentials
            
        Returns:
            tuple: (result_code: int, message: str)
        """
        # For now, reject all SASL binds
        if self.debug:
            log.msg(f"SASL bind not supported: mechanism={mechanism}")
        return 7, "SASL authentication not supported"  # authMethodNotSupported
