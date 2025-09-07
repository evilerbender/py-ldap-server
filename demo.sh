#!/bin/bash
#
# Demo script for py-ldap-server with uv
#

echo "🚀 py-ldap-server Demo"
echo "======================"
echo
echo "Starting LDAP server with JSON backend..."
echo

# Start the server in background
uv run py-ldap-server --json data.json &
SERVER_PID=$!

# Give server time to start
sleep 2

echo "✅ Server started (PID: $SERVER_PID)"
echo "📡 Running LDAP queries..."
echo

# Test 1: Base search
echo "🔍 Test 1: Base search for dc=example,dc=com"
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base "(objectClass=*)" | head -10
echo

# Test 2: Search for all users
echo "🔍 Test 2: Search for all users in ou=people"
ldapsearch -x -H ldap://localhost:1389 -b "ou=people,dc=example,dc=com" -s one "(objectClass=*)" | grep "dn:"
echo

# Test 3: Search for admin user
echo "🔍 Test 3: Search for admin user"
ldapsearch -x -H ldap://localhost:1389 -b "ou=people,dc=example,dc=com" -s one "(uid=admin)" cn mail
echo

# Test 4: Search for all groups
echo "🔍 Test 4: Search for all groups"
ldapsearch -x -H ldap://localhost:1389 -b "ou=groups,dc=example,dc=com" -s one "(objectClass=posixGroup)" cn memberUid | grep -E "(dn:|cn:|memberUid:)"
echo

# Cleanup
echo "🛑 Stopping server..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

echo "✅ Demo complete!"
echo
echo "📖 To run the server manually:"
echo "   uv run py-ldap-server --json data.json"
echo
echo "📖 To run with custom options:"
echo "   uv run py-ldap-server --port 389 --bind-host 0.0.0.0 --json data.json"
