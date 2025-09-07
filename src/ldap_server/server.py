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
    def __init__(self, port: int = 1389, bind_host: str = "localhost", debug: bool = True, json_path: str = None):
        self.port = port
        self.bind_host = bind_host
        self.debug = debug
        self.json_path = json_path
        self.factory: Optional[LDAPServerFactory] = None
        self.listening_port = None

    def start(self) -> None:
        """Start the LDAP server."""
        # Initialize logging
        if self.debug:
            log.startLogging(sys.stderr)

        log.msg(f"Starting LDAP server on {self.bind_host}:{self.port}")

        # Select storage backend
        if self.json_path:
            log.msg(f"Using JSON backend: {self.json_path}")
            storage = JSONStorage(self.json_path)
        else:
            storage = MemoryStorage()

        # Create server factory
        self.factory = LDAPServerFactory(storage=storage, debug=self.debug)

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
  %(prog)s                                    # Start on localhost:1389
  %(prog)s --port 389 --bind-host 0.0.0.0   # Start on all interfaces, port 389
  %(prog)s --json data.json                  # Use JSON backend with hot reload
  %(prog)s --no-debug                        # Start without debug logging

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

    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Path to JSON file for hot-reloading backend (optional)"
    )

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
        version="py-ldap-server 0.1.0"
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
            json_path=args.json
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
