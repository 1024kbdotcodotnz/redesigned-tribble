#!/usr/bin/env python3
"""
NZ Legal Advisor - Staff Management System
Create and manage API keys for law firm staff
"""

import json
import uuid
import hashlib
import argparse
from datetime import datetime, timedelta
from pathlib import Path


def generate_api_key():
    """Generate a secure API key"""
    key_id = uuid.uuid4().hex[:24]
    secret = uuid.uuid4().hex[:32]
    return f"nzl_{key_id}_{secret}"


def hash_api_key(api_key):
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_tenant(tenants_file, name, tier="professional"):
    """Create a new tenant/staff member"""
    
    # Load existing tenants
    if tenants_file.exists():
        with open(tenants_file, 'r') as f:
            tenants = json.load(f)
    else:
        tenants = {}
    
    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # Create tenant
    tenant_id = str(uuid.uuid4())
    
    tier_config = {
        "community": {
            "can_access_public_db": True,
            "can_store_confidential": False,
            "can_use_api": True,  # Changed to True for staff
            "max_queries_per_day": 100,
            "max_storage_bytes": 1000000000,
            "max_documents": 100,
        },
        "professional": {
            "can_access_public_db": True,
            "can_store_confidential": True,
            "can_use_api": True,
            "max_queries_per_day": 1000,
            "max_storage_bytes": 10000000000,
            "max_documents": 1000,
        },
        "enterprise": {
            "can_access_public_db": True,
            "can_store_confidential": True,
            "can_use_api": True,
            "max_queries_per_day": 10000,
            "max_storage_bytes": 100000000000,
            "max_documents": 10000,
        }
    }
    
    config = tier_config.get(tier, tier_config["professional"])
    
    tenants[tenant_id] = {
        "tenant_id": tenant_id,
        "name": name,
        "tier": tier,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
        "api_key_hash": key_hash,
        **config,
        "max_users": 1 if tier == "community" else (5 if tier == "professional" else 50),
        "queries_per_minute": 60 if tier == "community" else (120 if tier == "professional" else 300),
        "concurrent_users": 1 if tier == "community" else (3 if tier == "professional" else 20),
    }
    
    # Save
    tenants_file.parent.mkdir(parents=True, exist_ok=True)
    with open(tenants_file, 'w') as f:
        json.dump(tenants, f, indent=2)
    
    return tenant_id, api_key


def list_tenants(tenants_file):
    """List all tenants"""
    if not tenants_file.exists():
        print("No staff members configured yet.")
        return
    
    with open(tenants_file, 'r') as f:
        tenants = json.load(f)
    
    print("\n" + "="*80)
    print("  STAFF ACCESS LIST")
    print("="*80)
    print(f"\n{'ID':<36} {'Name':<25} {'Tier':<12} {'API Access':<10} {'Expires'}")
    print("-"*80)
    
    for tenant_id, tenant in tenants.items():
        name = tenant.get('name', 'Unknown')[:24]
        tier = tenant.get('tier', 'unknown')
        api = "Yes" if tenant.get('can_use_api', False) else "No"
        expires = tenant.get('expires_at', 'N/A')[:10]
        print(f"{tenant_id:<36} {name:<25} {tier:<12} {api:<10} {expires}")
    
    print(f"\nTotal staff members: {len(tenants)}")
    print("="*80)


def revoke_tenant(tenants_file, tenant_id):
    """Revoke a tenant's access"""
    if not tenants_file.exists():
        print("No tenants file found.")
        return False
    
    with open(tenants_file, 'r') as f:
        tenants = json.load(f)
    
    if tenant_id not in tenants:
        print(f"❌ Tenant not found: {tenant_id}")
        return False
    
    name = tenants[tenant_id].get('name', 'Unknown')
    del tenants[tenant_id]
    
    with open(tenants_file, 'w') as f:
        json.dump(tenants, f, indent=2)
    
    print(f"✓ Access revoked for: {name}")
    return True


def export_staff_list(tenants_file, output_file):
    """Export staff list to a file for sharing"""
    if not tenants_file.exists():
        print("No tenants file found.")
        return
    
    with open(tenants_file, 'r') as f:
        tenants = json.load(f)
    
    with open(output_file, 'w') as f:
        f.write("NZ Legal Advisor - Staff Access List\n")
        f.write("="*60 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        
        for tenant_id, tenant in tenants.items():
            f.write(f"Name: {tenant.get('name', 'Unknown')}\n")
            f.write(f"  ID: {tenant_id}\n")
            f.write(f"  Tier: {tenant.get('tier', 'unknown')}\n")
            f.write(f"  API Access: {'Yes' if tenant.get('can_use_api') else 'No'}\n")
            f.write(f"  Expires: {tenant.get('expires_at', 'N/A')[:10]}\n")
            f.write(f"  Daily Queries: {tenant.get('max_queries_per_day', 'N/A')}\n")
            f.write("\n")
    
    print(f"✓ Staff list exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='NZ Legal Advisor - Staff Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all staff
  python staff_management.py list
  
  # Add new staff member
  python staff_management.py add "Jane Smith" --tier professional
  
  # Add admin user
  python staff_management.py add "Admin" --tier enterprise
  
  # Revoke access
  python staff_management.py revoke <tenant-id>
  
  # Export staff list
  python staff_management.py export --file staff_list.txt
        """
    )
    
    parser.add_argument('command', choices=['list', 'add', 'revoke', 'export'],
                       help='Command to execute')
    parser.add_argument('name', nargs='?', help='Staff member name (for add/revoke)')
    parser.add_argument('--tier', default='professional',
                       choices=['community', 'professional', 'enterprise'],
                       help='Access tier (default: professional)')
    parser.add_argument('--file', default='staff_list.txt',
                       help='Output file for export')
    parser.add_argument('--tenants-file', 
                       default='/home/owner/nz_legal_rag/tenant_data/tenants.json',
                       help='Path to tenants.json')
    
    args = parser.parse_args()
    
    tenants_file = Path(args.tenants_file)
    
    if args.command == 'list':
        list_tenants(tenants_file)
    
    elif args.command == 'add':
        if not args.name:
            print("❌ Error: Staff name is required")
            print("Usage: python staff_management.py add 'Jane Smith' --tier professional")
            return
        
        print("\n" + "="*60)
        print("  Creating New Staff Access")
        print("="*60)
        print(f"\nName: {args.name}")
        print(f"Tier: {args.tier}")
        
        tenant_id, api_key = create_tenant(tenants_file, args.name, args.tier)
        
        print(f"\n✓ Staff member created!")
        print(f"\n{'='*60}")
        print("  ⚠️  SAVE THIS API KEY - IT CANNOT BE RETRIEVED LATER")
        print(f"{'='*60}")
        print(f"\n  API Key: {api_key}")
        print(f"  Tenant ID: {tenant_id}")
        print(f"\n  Use in API calls:")
        print(f'    curl -H "Authorization: Bearer {api_key}" ...')
        print(f"\n{'='*60}")
        
        # Save to file for safekeeping
        key_file = Path(f"/home/owner/nz_legal_rag/keys_{args.name.replace(' ', '_')}.txt")
        key_file.parent.mkdir(parents=True, exist_ok=True)
        with open(key_file, 'w') as f:
            f.write(f"NZ Legal Advisor - API Key\n")
            f.write(f"Name: {args.name}\n")
            f.write(f"Tier: {args.tier}\n")
            f.write(f"Tenant ID: {tenant_id}\n")
            f.write(f"API Key: {api_key}\n")
            f.write(f"Created: {datetime.now().isoformat()}\n")
        print(f"✓ Key also saved to: {key_file}")
    
    elif args.command == 'revoke':
        if not args.name:
            print("❌ Error: Tenant ID is required")
            print("Usage: python staff_management.py revoke <tenant-id>")
            return
        revoke_tenant(tenants_file, args.name)
    
    elif args.command == 'export':
        export_staff_list(tenants_file, args.file)


if __name__ == '__main__':
    main()
