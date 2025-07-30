"""
Storage backend package initialization.
"""

from ldap_server.storage.memory import MemoryStorage

__all__ = ["MemoryStorage"]
