#!/usr/bin/env python3
"""
Multi-Tenant Manager (Demo Role-Based Version)
Handles access control and isolation for the online demo app.
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path

class UserRole(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    USER = "user"

@dataclass
class TenantConfig:
    tenant_id: str
    username: str
    name: str
    role: UserRole
    created_at: str
    expires_at: Optional[str]
    api_key_hash: str
    password_hash: str
    # Demo-only: stored plaintext so login can return it after restart
    api_key: Optional[str] = None
    
    # Permissions
    can_access_public_db: bool = True
    can_store_permanent: bool = False
    can_use_api: bool = True
    can_invite_users: bool = False
    
    # Quotas
    max_storage_bytes: int = 0
    max_queries_per_day: int = 100
    max_users: int = 1
    max_documents: int = 10
    
    # Rate limits
    queries_per_minute: int = 30
    concurrent_users: int = 1

@dataclass
class UsageStats:
    tenant_id: str
    date: str
    queries_made: int = 0
    documents_stored: int = 0
    storage_bytes_used: int = 0
    api_calls: int = 0


class TenantManager:
    """
    Manages demo user access control
    
    Roles:
    - ADMIN: Full access, unlimited queries, can manage users
    - STAFF: Full access including permanent storage
    - USER: Read-only + temporary session uploads only
    """
    
    ROLE_DEFAULTS = {
        UserRole.USER: {
            "can_access_public_db": True,
            "can_store_permanent": False,
            "can_use_api": True,
            "can_invite_users": False,
            "max_storage_bytes": 0,
            "max_queries_per_day": 50,
            "max_users": 1,
            "max_documents": 0,
            "queries_per_minute": 30,
            "concurrent_users": 1
        },
        UserRole.STAFF: {
            "can_access_public_db": True,
            "can_store_permanent": True,
            "can_use_api": True,
            "can_invite_users": False,
            "max_storage_bytes": 10_000_000_000,  # 10GB
            "max_queries_per_day": 500,
            "max_users": 1,
            "max_documents": 5000,
            "queries_per_minute": 120,
            "concurrent_users": 3
        },
        UserRole.ADMIN: {
            "can_access_public_db": True,
            "can_store_permanent": True,
            "can_use_api": True,
            "can_invite_users": True,
            "max_storage_bytes": 100_000_000_000,  # 100GB
            "max_queries_per_day": 100_000,
            "max_users": 50,
            "max_documents": 100_000,
            "queries_per_minute": 600,
            "concurrent_users": 50
        }
    }
    
    DEMO_ACCOUNTS = {
        "admin": {
            "name": "Demo Admin",
            "role": UserRole.ADMIN,
            "password": "demo-admin-2024!",
            "api_key": "nzl_demo_admin_7a8f9e2b4c1d"
        },
        "staff": {
            "name": "Demo Staff",
            "role": UserRole.STAFF,
            "password": "demo-staff-2024!",
            "api_key": "nzl_demo_staff_3e5a7b9d0f2e"
        },
        "user": {
            "name": "Demo User",
            "role": UserRole.USER,
            "password": "demo-user-2024!",
            "api_key": "nzl_demo_user_1c4e6a8b0d3f"
        },
    }
    
    def __init__(self, storage_dir: str = "./tenant_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.tenants_file = self.storage_dir / "tenants.json"
        self.usage_file = self.storage_dir / "usage.json"
        
        self.tenants: Dict[str, TenantConfig] = {}
        self.usage_stats: Dict[str, List[UsageStats]] = {}
        
        self._load_data()
        self._auto_seed_demo_users()
    
    def _load_data(self):
        """Load tenants and usage from disk"""
        if self.tenants_file.exists():
            try:
                with open(self.tenants_file, 'r') as f:
                    data = json.load(f)
                for tid, tdata in data.items():
                    # Handle migration from old tier field if present
                    if 'role' not in tdata and 'tier' in tdata:
                        tier = tdata.pop('tier')
                        role_map = {
                            'community': UserRole.USER,
                            'professional': UserRole.STAFF,
                            'enterprise': UserRole.ADMIN
                        }
                        tdata['role'] = role_map.get(tier, UserRole.USER).value
                    if 'api_key' not in tdata:
                        tdata['api_key'] = None
                    tdata['role'] = UserRole(tdata['role'])
                    self.tenants[tid] = TenantConfig(**tdata)
            except Exception as e:
                print(f"Error loading tenants: {e}")
        
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                for tid, usage_list in data.items():
                    self.usage_stats[tid] = [
                        UsageStats(**u) for u in usage_list
                    ]
            except Exception as e:
                print(f"Error loading usage: {e}")
    
    def _save_data(self):
        """Save tenants and usage to disk"""
        tenants_data = {
            tid: {**asdict(t), 'role': t.role.value}
            for tid, t in self.tenants.items()
        }
        with open(self.tenants_file, 'w') as f:
            json.dump(tenants_data, f, indent=2)
        
        usage_data = {
            tid: [asdict(u) for u in stats]
            for tid, stats in self.usage_stats.items()
        }
        with open(self.usage_file, 'w') as f:
            json.dump(usage_data, f, indent=2)
    
    def _auto_seed_demo_users(self):
        """Create the three demo accounts if no users exist yet."""
        if self.tenants:
            return
        
        for username, info in self.DEMO_ACCOUNTS.items():
            self.create_user(
                username=username,
                name=info["name"],
                role=info["role"],
                password=info["password"],
                api_key=info["api_key"],
                days_valid=365
            )
        print("✓ Seeded demo users: admin, staff, user")
    
    def create_user(self, 
                    username: str,
                    name: str,
                    role: UserRole,
                    password: str,
                    api_key: Optional[str] = None,
                    days_valid: int = 365) -> Tuple[str, str]:
        """
        Create a new demo user.
        
        Returns:
            (tenant_id, api_key)
        """
        tenant_id = str(uuid.uuid4())
        if api_key is None:
            api_key = self._generate_api_key()
        api_key_hash = self._hash(api_key)
        password_hash = self._hash(password)
        
        defaults = self.ROLE_DEFAULTS[role]
        
        config = TenantConfig(
            tenant_id=tenant_id,
            username=username,
            name=name,
            role=role,
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(days=days_valid)).isoformat(),
            api_key_hash=api_key_hash,
            password_hash=password_hash,
            api_key=api_key,
            **defaults
        )
        
        self.tenants[tenant_id] = config
        self.usage_stats[tenant_id] = []
        self._save_data()
        
        return tenant_id, api_key
    
    def _generate_api_key(self) -> str:
        """Generate a new API key"""
        return f"nzl_{uuid.uuid4().hex}_{uuid.uuid4().hex[:16]}"
    
    def _hash(self, value: str) -> str:
        """Hash a string for storage"""
        return hashlib.sha256(value.encode()).hexdigest()
    
    def verify_api_key(self, api_key: str) -> Optional[TenantConfig]:
        """Verify an API key and return tenant config"""
        api_key_hash = self._hash(api_key)
        
        for tenant in self.tenants.values():
            if tenant.api_key_hash == api_key_hash:
                if tenant.expires_at:
                    expires = datetime.fromisoformat(tenant.expires_at)
                    if datetime.now() > expires:
                        return None
                return tenant
        
        return None
    
    def verify_credentials(self, username: str, password: str) -> Optional[Tuple[TenantConfig, str]]:
        """Verify username/password and return (tenant, api_key)"""
        password_hash = self._hash(password)
        
        for tenant in self.tenants.values():
            if tenant.username == username and tenant.password_hash == password_hash:
                if tenant.expires_at:
                    expires = datetime.fromisoformat(tenant.expires_at)
                    if datetime.now() > expires:
                        return None
                return tenant, tenant.api_key
        
        return None
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)
    
    def get_tenant_by_username(self, username: str) -> Optional[TenantConfig]:
        """Get tenant by username"""
        for tenant in self.tenants.values():
            if tenant.username == username:
                return tenant
        return None
    
    def update_tenant(self, tenant_id: str, **kwargs) -> bool:
        """Update tenant configuration"""
        if tenant_id not in self.tenants:
            return False
        
        tenant = self.tenants[tenant_id]
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        self._save_data()
        return True
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant and all associated data"""
        if tenant_id not in self.tenants:
            return False
        
        del self.tenants[tenant_id]
        if tenant_id in self.usage_stats:
            del self.usage_stats[tenant_id]
        
        self._save_data()
        return True
    
    def record_usage(self, tenant_id: str, query_count: int = 0, 
                     storage_bytes: int = 0, api_calls: int = 0):
        """Record usage for a tenant"""
        if tenant_id not in self.usage_stats:
            self.usage_stats[tenant_id] = []
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        today_stats = None
        for stats in self.usage_stats[tenant_id]:
            if stats.date == today:
                today_stats = stats
                break
        
        if today_stats is None:
            today_stats = UsageStats(
                tenant_id=tenant_id,
                date=today
            )
            self.usage_stats[tenant_id].append(today_stats)
        
        today_stats.queries_made += query_count
        today_stats.storage_bytes_used += storage_bytes
        today_stats.api_calls += api_calls
        
        self._save_data()
    
    def check_quota(self, tenant_id: str, operation: str) -> Tuple[bool, str]:
        """
        Check if tenant can perform an operation
        
        Returns:
            (allowed, reason)
        """
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False, "Tenant not found"
        
        if tenant.expires_at:
            expires = datetime.fromisoformat(tenant.expires_at)
            if datetime.now() > expires:
                return False, "Subscription expired"
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_stats = None
        for stats in self.usage_stats.get(tenant_id, []):
            if stats.date == today:
                today_stats = stats
                break
        
        queries_today = today_stats.queries_made if today_stats else 0
        
        if operation == "query":
            if queries_today >= tenant.max_queries_per_day:
                return False, f"Daily query limit reached ({tenant.max_queries_per_day})"
        
        elif operation in ("store_permanent", "store_confidential"):
            if not tenant.can_store_permanent:
                return False, "Permanent storage not allowed for this role"
        
        elif operation == "api_call":
            if not tenant.can_use_api:
                return False, "API access not allowed"
        
        return True, "OK"
    
    def get_usage_report(self, tenant_id: str, days: int = 30) -> Dict:
        """Generate usage report for a tenant"""
        if tenant_id not in self.tenants:
            return {"error": "Tenant not found"}
        
        tenant = self.tenants[tenant_id]
        stats = self.usage_stats.get(tenant_id, [])
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        recent_stats = [s for s in stats if s.date >= cutoff]
        
        total_queries = sum(s.queries_made for s in recent_stats)
        total_api = sum(s.api_calls for s in recent_stats)
        current_storage = max((s.storage_bytes_used for s in recent_stats), default=0)
        
        return {
            "tenant_id": tenant_id,
            "username": tenant.username,
            "name": tenant.name,
            "role": tenant.role.value,
            "period_days": days,
            "summary": {
                "total_queries": total_queries,
                "total_api_calls": total_api,
                "storage_bytes_used": current_storage
            },
            "quotas": {
                "max_queries_per_day": tenant.max_queries_per_day,
                "max_storage_bytes": tenant.max_storage_bytes,
                "max_documents": tenant.max_documents
            },
            "daily_breakdown": [
                {
                    "date": s.date,
                    "queries": s.queries_made,
                    "api_calls": s.api_calls,
                    "storage_bytes": s.storage_bytes_used
                }
                for s in recent_stats
            ]
        }
    
    def list_tenants(self) -> List[Dict]:
        """List all tenants (admin only)"""
        return [
            {
                "tenant_id": t.tenant_id,
                "username": t.username,
                "name": t.name,
                "role": t.role.value,
                "created_at": t.created_at,
                "expires_at": t.expires_at
            }
            for t in self.tenants.values()
        ]


def main():
    """CLI entry point for tenant management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Tenant Manager CLI")
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    create_parser = subparsers.add_parser('create', help='Create new user')
    create_parser.add_argument('--username', '-u', required=True, help='Username')
    create_parser.add_argument('--name', '-n', required=True, help='Display name')
    create_parser.add_argument('--role', '-r', choices=['admin', 'staff', 'user'],
                              default='user', help='User role')
    create_parser.add_argument('--password', '-p', required=True, help='Password')
    create_parser.add_argument('--api-key', '-k', help='Optional fixed API key')
    create_parser.add_argument('--days', '-d', type=int, default=365, help='Days valid')
    
    subparsers.add_parser('list', help='List all users')
    
    delete_parser = subparsers.add_parser('delete', help='Delete user')
    delete_parser.add_argument('tenant_id', help='Tenant ID')
    
    usage_parser = subparsers.add_parser('usage', help='Show usage report')
    usage_parser.add_argument('tenant_id', help='Tenant ID')
    usage_parser.add_argument('--days', '-d', type=int, default=30, help='Days to report')
    
    args = parser.parse_args()
    
    manager = TenantManager()
    
    if args.command == 'create':
        role = UserRole(args.role)
        tenant_id, api_key = manager.create_user(
            username=args.username,
            name=args.name,
            role=role,
            password=args.password,
            api_key=args.api_key,
            days_valid=args.days
        )
        print(f"\n✓ User created")
        print(f"  ID: {tenant_id}")
        print(f"  Username: {args.username}")
        print(f"  Role: {args.role}")
        print(f"  API Key: {api_key}")
        print(f"\n⚠️  Save the API key securely - it cannot be retrieved later!")
    
    elif args.command == 'list':
        tenants = manager.list_tenants()
        print(f"\n{'ID':<36} {'Username':<15} {'Name':<20} {'Role':<10} {'Expires':<20}")
        print("-" * 100)
        for t in tenants:
            print(f"{t['tenant_id']:<36} {t['username']:<15} {t['name']:<20} {t['role']:<10} {t['expires_at'] or 'Never':<20}")
    
    elif args.command == 'delete':
        if manager.delete_tenant(args.tenant_id):
            print(f"✓ User {args.tenant_id} deleted")
        else:
            print(f"✗ User not found")
    
    elif args.command == 'usage':
        report = manager.get_usage_report(args.tenant_id, args.days)
        if 'error' in report:
            print(f"✗ {report['error']}")
        else:
            print(f"\nUsage Report: {report['name']} ({report['username']})")
            print(f"Role: {report['role']}")
            print(f"Period: Last {report['period_days']} days")
            print(f"\nSummary:")
            print(f"  Queries: {report['summary']['total_queries']}")
            print(f"  API calls: {report['summary']['total_api_calls']}")
            print(f"  Storage: {report['summary']['storage_bytes_used']:,} bytes")
            print(f"\nQuotas:")
            print(f"  Max queries/day: {report['quotas']['max_queries_per_day']}")
            print(f"  Max storage: {report['quotas']['max_storage_bytes']:,} bytes")


if __name__ == "__main__":
    main()
