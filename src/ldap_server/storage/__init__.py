"""
Storage backend package initialization.
"""

from ldap_server.storage.memory import MemoryStorage
from ldap_server.storage.json import JSONStorage

__all__ = ["MemoryStorage", "JSONStorage"]
