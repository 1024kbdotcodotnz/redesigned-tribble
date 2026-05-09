#!/usr/bin/env python3
"""
Seed / reset the three demo accounts for the online demo app.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from security.tenant_manager import TenantManager


def main():
    parser = argparse.ArgumentParser(description="Seed demo accounts")
    parser.add_argument("--reset", action="store_true", help="Delete all existing users and re-seed")
    args = parser.parse_args()

    manager = TenantManager()

    if args.reset:
        print("⚠️  Resetting all users...")
        for tid in list(manager.tenants.keys()):
            manager.delete_tenant(tid)
        print("✓ All users deleted")

    # Trigger auto-seed if empty
    manager._auto_seed_demo_users()

    print("\n✓ Demo accounts ready:")
    print("-" * 60)
    for t in manager.tenants.values():
        print(f"  Username: {t.username}")
        print(f"  Name:     {t.name}")
        print(f"  Role:     {t.role.value}")
        print(f"  API Key:  {t.api_key}")
        print("-" * 60)


if __name__ == "__main__":
    main()
