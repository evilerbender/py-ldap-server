"""
py-ldap-server: A Python LDAP server implementation using Ldaptor.
"""

__version__ = "0.3.0"
__author__ = "evilerbender"
__email__ = "evilerbender@users.noreply.github.com"

from ldap_server.server import LDAPServerFactory

__all__ = ["LDAPServerFactory"]
