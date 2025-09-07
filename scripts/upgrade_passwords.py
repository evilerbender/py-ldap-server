#!/usr/bin/env python3
"""
Script to upgrade LDAP JSON data file with secure password hashes.

This script will:
1. Read the existing data.json file
2. Identify plain text passwords
3. Replace them with secure bcrypt hashes
4. Create a backup of the original file
5. Write the updated data back to the file

Usage:
    python scripts/upgrade_passwords.py [data_file]
    
    # Or with uv:
    uv run python scripts/upgrade_passwords.py data.json
"""

import json
import sys
import os
import shutil
from datetime import datetime
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ldap_server.auth.password import PasswordManager


def backup_file(file_path: str) -> str:
    """Create a backup of the original file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    return backup_path


def upgrade_json_passwords(file_path: str) -> None:
    """Upgrade passwords in a JSON LDAP data file."""
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File {file_path} does not exist")
        sys.exit(1)
    
    print(f"🔍 Processing LDAP data file: {file_path}")
    
    # Create backup
    backup_path = backup_file(file_path)
    print(f"💾 Created backup: {backup_path}")
    
    # Load JSON data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            entries = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)
    
    if not isinstance(entries, list):
        print("❌ Error: JSON root must be a list of entries")
        sys.exit(1)
    
    # Track changes
    total_entries = len(entries)
    entries_with_passwords = 0
    passwords_upgraded = 0
    
    # Upgrade passwords
    upgraded_entries = []
    
    for entry in entries:
        updated_entry = entry.copy()
        attributes = updated_entry.get("attributes", {}).copy()
        
        # Check for userPassword attribute
        if "userPassword" in attributes:
            entries_with_passwords += 1
            passwords = attributes["userPassword"]
            hashed_passwords = []
            entry_passwords_upgraded = 0
            
            for password in passwords:
                # Only hash if it's plain text (no format prefix)
                if not password.startswith("{"):
                    hashed_password = PasswordManager.hash_password(password)
                    hashed_passwords.append(hashed_password)
                    entry_passwords_upgraded += 1
                    passwords_upgraded += 1
                    print(f"🔒 Upgraded password for: {updated_entry.get('dn', 'unknown')}")
                else:
                    # Keep existing hashed passwords
                    hashed_passwords.append(password)
                    print(f"✅ Password already hashed for: {updated_entry.get('dn', 'unknown')}")
            
            if entry_passwords_upgraded > 0:
                attributes["userPassword"] = hashed_passwords
                updated_entry["attributes"] = attributes
        
        upgraded_entries.append(updated_entry)
    
    # Write updated data back to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(upgraded_entries, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully updated {file_path}")
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        # Restore from backup
        shutil.copy2(backup_path, file_path)
        print(f"🔄 Restored original file from backup")
        sys.exit(1)
    
    # Print summary
    print("\n📊 Upgrade Summary:")
    print(f"   Total entries: {total_entries}")
    print(f"   Entries with passwords: {entries_with_passwords}")
    print(f"   Passwords upgraded: {passwords_upgraded}")
    print(f"   Backup created: {backup_path}")
    
    if passwords_upgraded > 0:
        print("\n🎉 Password upgrade completed successfully!")
        print("   All plain text passwords have been replaced with secure bcrypt hashes.")
    else:
        print("\n ℹ️  No plain text passwords found to upgrade.")


def main():
    """Main entry point."""
    # Determine data file path
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        # Default to data.json in the project root
        project_root = Path(__file__).parent.parent
        data_file = str(project_root / "data.json")
    
    print("🔐 LDAP Password Upgrade Tool")
    print("=" * 40)
    print(f"This tool will upgrade plain text passwords in {data_file}")
    print("to secure bcrypt hashes.\n")
    
    # Confirm with user
    if sys.stdin.isatty():  # Only prompt if running interactively
        response = input("Continue? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Operation cancelled")
            sys.exit(0)
    
    try:
        upgrade_json_passwords(data_file)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
