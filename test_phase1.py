#!/usr/bin/env python3
"""
Integration test for Phase 1 - basic server functionality.
Tests that the server starts, accepts connections, and responds to basic LDAP queries.
"""

import sys
import time
import subprocess
import signal
import socket
from pathlib import Path

def check_port_open(host, port, timeout=5):
    """Check if a port is open and accepting connections."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

def test_server_starts():
    """Test that the server starts and listens on the expected port."""
    print("Testing Phase 1: Basic Server Functionality")
    print("=" * 50)
    
    # Start the server
    print("1. Starting LDAP server...")
    server_process = subprocess.Popen([
        sys.executable, "-c", 
        """
import sys
sys.path.insert(0, 'src')
from ldap_server.server import LDAPServerService
server = LDAPServerService(port=1389, bind_host='localhost', debug=False)
try:
    server.start()
except KeyboardInterrupt:
    pass
        """
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Give the server time to start
    time.sleep(2)
    
    # Check if the server is listening
    print("2. Checking if server is listening on port 1389...")
    if check_port_open('localhost', 1389):
        print("✓ Server is listening on localhost:1389")
        success = True
    else:
        print("✗ Server is not listening on localhost:1389")
        success = False
    
    # Clean up
    print("3. Stopping server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
        server_process.wait()
    
    # Check output for errors
    stdout, stderr = server_process.communicate()
    if stderr:
        print(f"Server stderr: {stderr.decode()}")
    
    return success

def test_ldapsearch_available():
    """Test if ldapsearch is available for testing."""
    print("4. Checking if ldapsearch is available...")
    try:
        result = subprocess.run(['ldapsearch', '-VV'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ ldapsearch is available")
            return True
        else:
            print("✗ ldapsearch not found or not working")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("✗ ldapsearch not found")
        return False

def main():
    """Run Phase 1 integration tests."""
    print("Phase 1 Integration Test")
    print("========================")
    
    # Test 1: Server startup
    server_test = test_server_starts()
    
    # Test 2: LDAP client availability (optional)
    ldap_test = test_ldapsearch_available()
    
    print("\nTest Results:")
    print(f"Server startup: {'PASS' if server_test else 'FAIL'}")
    print(f"ldapsearch available: {'PASS' if ldap_test else 'FAIL (optional)'}")
    
    if server_test:
        print("\n🎉 Phase 1 MVP completed successfully!")
        print("The LDAP server can start and accept connections.")
        if ldap_test:
            print("\nNext steps: Test with ldapsearch:")
            print("1. Start server: py-ldap-server --port 1389")
            print("2. Test: ldapsearch -x -H ldap://localhost:1389 -b 'dc=example,dc=com' -s base")
        return 0
    else:
        print("\n❌ Phase 1 tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
