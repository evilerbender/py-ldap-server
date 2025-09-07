"""
Main LDAP server implementation and entry point.
"""

import argparse
import sys
import signal
import warnings
from typing import Optional

from twisted.internet import reactor
from twisted.python import log
from twisted.application import service

from ldap_server.factory import LDAPServerFactory
from ldap_server.storage.memory import MemoryStorage
from ldap_server.storage.json import JSONStorage

# Filter out known deprecation warnings from dependencies
warnings.filterwarnings("ignore", "'crypt' is deprecated", DeprecationWarning, "passlib.*")
warnings.filterwarnings("ignore", "DistinguishedName.__str__ method is deprecated", DeprecationWarning)


class LDAPServerService:
    """
    Main LDAP server service that manages the server lifecycle.
    """
    def __init__(self, port: int = 1389, bind_host: str = "localhost", debug: bool = True, 
                 json_path: str = None, json_files: list = None, merge_strategy: str = "last_wins",
                 no_auto_reload: bool = False, debounce_time: float = 0.5):
        self.port = port
        self.bind_host = bind_host
        self.debug = debug
        self.json_path = json_path
        self.json_files = json_files
        self.merge_strategy = merge_strategy
        self.enable_watcher = not no_auto_reload
        self.debounce_time = debounce_time
        self.factory: Optional[LDAPServerFactory] = None
        self.listening_port = None

    def start(self) -> None:
        """Start the LDAP server."""
        # Initialize logging
        if self.debug:
            log.startLogging(sys.stderr)

        log.msg(f"Starting LDAP server on {self.bind_host}:{self.port}")

        # Select storage backend
        if self.json_files:
            log.msg(f"Using federated JSON backend: {self.json_files}")
            log.msg(f"Merge strategy: {self.merge_strategy}")
            log.msg(f"Auto-reload: {self.enable_watcher}")
            storage = JSONStorage(
                json_file_paths=self.json_files,
                merge_strategy=self.merge_strategy,
                enable_file_watching=self.enable_watcher,
                debounce_time=self.debounce_time
            )
        elif self.json_path:
            log.msg(f"Using JSON backend: {self.json_path}")
            log.msg(f"Auto-reload: {self.enable_watcher}")
            storage = JSONStorage(
                json_file_paths=self.json_path,
                enable_file_watching=self.enable_watcher
            )
        else:
            log.msg("Using in-memory storage backend")
            storage = MemoryStorage()

        # Create server factory
        self.factory = LDAPServerFactory(storage=storage, debug=self.debug)

        # Print storage statistics if available
        if hasattr(storage, 'get_stats'):
            stats = storage.get_stats()
            log.msg(f"Storage stats: {stats.get('total_entries', 'N/A')} entries, "
                   f"{stats.get('files_loaded', 'N/A')} files loaded")
            if stats.get('merge_conflicts', 0) > 0:
                log.msg(f"Warning: {stats['merge_conflicts']} merge conflicts resolved")

        # Start listening
        self.listening_port = reactor.listenTCP(self.port, self.factory, interface=self.bind_host)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        log.msg(f"LDAP server started successfully")
        log.msg(f"Test with: ldapsearch -x -H ldap://{self.bind_host}:{self.port} -b 'dc=example,dc=com' -s base")

        # Start the reactor
        reactor.run()

    def stop(self) -> None:
        """Stop the LDAP server gracefully."""
        log.msg("Stopping LDAP server...")

        if self.listening_port:
            self.listening_port.stopListening()

        if self.factory:
            self.factory.cleanup()

        if reactor.running:
            reactor.stop()

        log.msg("LDAP server stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        log.msg(f"Received signal {signum}, shutting down gracefully...")
        reactor.callFromThread(self.stop)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="py-ldap-server: A Python LDAP server implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Start with in-memory storage
  %(prog)s --json data.json                  # Use single JSON file
  %(prog)s --json-files data1.json data2.json data3.json  # Use federated JSON
  %(prog)s --json-files users.json groups.json --merge-strategy first_wins
  %(prog)s --port 389 --bind-host 0.0.0.0   # Start on all interfaces, port 389
  %(prog)s --no-debug                        # Start without debug logging
  %(prog)s --no-auto-reload                  # Disable file watching

Test the server:
  ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base
        """
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=1389,
        help="Port to bind the LDAP server to (default: 1389)"
    )

    parser.add_argument(
        "--bind-host", "-H",
        type=str,
        default="localhost",
        help="Host address to bind to (default: localhost)"
    )

    # Storage backend options (mutually exclusive)
    storage_group = parser.add_mutually_exclusive_group()
    
    storage_group.add_argument(
        "--json",
        type=str,
        default=None,
        help="Path to JSON file for single-file backend (optional)"
    )
    
    storage_group.add_argument(
        "--json-files",
        nargs="+",
        metavar="FILE",
        help="Paths to multiple JSON files for federated backend"
    )

    # JSON storage configuration
    parser.add_argument(
        "--merge-strategy",
        choices=["first_wins", "last_wins", "error"],
        default="last_wins",
        help="Merge strategy for federated JSON storage (default: last_wins)"
    )
    
    parser.add_argument(
        "--no-auto-reload",
        action="store_true",
        help="Disable automatic file watching and reloading"
    )
    
    parser.add_argument(
        "--debounce-time",
        type=float,
        default=0.5,
        help="Debounce time for file change detection in seconds (default: 0.5)"
    )

    # Logging options
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        default=True,
        help="Enable debug logging (default: enabled)"
    )

    parser.add_argument(
        "--no-debug",
        action="store_false",
        dest="debug",
        help="Disable debug logging"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="py-ldap-server 0.3.0"
    )

    return parser


def main():
    """Main entry point for the LDAP server."""
    parser = create_argument_parser()
    args = parser.parse_args()

    try:
        server = LDAPServerService(
            port=args.port,
            bind_host=args.bind_host,
            debug=args.debug,
            json_path=args.json,
            json_files=args.json_files,
            merge_strategy=args.merge_strategy,
            no_auto_reload=args.no_auto_reload,
            debounce_time=args.debounce_time
        )
        server.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting LDAP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
