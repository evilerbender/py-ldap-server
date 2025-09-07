#!/bin/bash
#
# Simple script to run py-ldap-server with uv
#

cd "$(dirname "$0")"

echo "Starting py-ldap-server with JSON backend..."
echo "Press Ctrl+C to stop the server"
echo ""

# Run with JSON backend
uv run py-ldap-server --json data.json "$@"
