#!/usr/bin/env python3
"""
Multi-Tenant Manager
Handles access control and isolation for commercial/community use
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path

class AccessTier(Enum):
    COMMUNITY = "community"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

@dataclass
class TenantConfig:
    tenant_id: str
    name: str
    tier: AccessTier
    created_at: str
    expires_at: Optional[str]
    api_key_hash: str
    
    # Permissions
    can_access_public_db: bool = True
    can_store_confidential: bool = False
    can_use_api: bool = False
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
    Manages multi-tenant access control
    
    Tiers:
    - COMMUNITY: Read-only access to public legal DB
    - PROFESSIONAL: Full access + confidential document storage
    - ENTERPRISE: Multi-user + API access + audit logging
    """
    
    TIER_DEFAULTS = {
        AccessTier.COMMUNITY: {
            "can_access_public_db": True,
            "can_store_confidential": False,
            "can_use_api": False,
            "can_invite_users": False,
            "max_storage_bytes": 0,
            "max_queries_per_day": 100,
            "max_users": 1,
            "max_documents": 0,
            "queries_per_minute": 30,
            "concurrent_users": 1
        },
        AccessTier.PROFESSIONAL: {
            "can_access_public_db": True,
            "can_store_confidential": True,
            "can_use_api": False,
            "can_invite_users": False,
            "max_storage_bytes": 10_000_000_000,  # 10GB
            "max_queries_per_day": 1000,
            "max_users": 1,
            "max_documents": 1000,
            "queries_per_minute": 120,
            "concurrent_users": 3
        },
        AccessTier.ENTERPRISE: {
            "can_access_public_db": True,
            "can_store_confidential": True,
            "can_use_api": True,
            "can_invite_users": True,
            "max_storage_bytes": 100_000_000_000,  # 100GB
            "max_queries_per_day": 10000,
            "max_users": 50,
            "max_documents": 10000,
            "queries_per_minute": 600,
            "concurrent_users": 50
        }
    }
    
    def __init__(self, storage_dir: str = "./tenant_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.tenants_file = self.storage_dir / "tenants.json"
        self.usage_file = self.storage_dir / "usage.json"
        
        self.tenants: Dict[str, TenantConfig] = {}
        self.usage_stats: Dict[str, List[UsageStats]] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load tenants and usage from disk"""
        if self.tenants_file.exists():
            try:
                with open(self.tenants_file, 'r') as f:
                    data = json.load(f)
                for tid, tdata in data.items():
                    tdata['tier'] = AccessTier(tdata['tier'])
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
            tid: {**asdict(t), 'tier': t.tier.value}
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
    
    def create_tenant(self, 
                      name: str,
                      tier: AccessTier,
                      days_valid: int = 365) -> Tuple[str, str]:
        """
        Create a new tenant
        
        Returns:
            (tenant_id, api_key)
        """
        tenant_id = str(uuid.uuid4())
        api_key = self._generate_api_key()
        api_key_hash = self._hash_api_key(api_key)
        
        defaults = self.TIER_DEFAULTS[tier]
        
        config = TenantConfig(
            tenant_id=tenant_id,
            name=name,
            tier=tier,
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(days=days_valid)).isoformat(),
            api_key_hash=api_key_hash,
            **defaults
        )
        
        self.tenants[tenant_id] = config
        self.usage_stats[tenant_id] = []
        self._save_data()
        
        return tenant_id, api_key
    
    def _generate_api_key(self) -> str:
        """Generate a new API key"""
        return f"nzl_{uuid.uuid4().hex}_{uuid.uuid4().hex[:16]}"
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_api_key(self, api_key: str) -> Optional[TenantConfig]:
        """Verify an API key and return tenant config"""
        api_key_hash = self._hash_api_key(api_key)
        
        for tenant in self.tenants.values():
            if tenant.api_key_hash == api_key_hash:
                # Check expiration
                if tenant.expires_at:
                    expires = datetime.fromisoformat(tenant.expires_at)
                    if datetime.now() > expires:
                        return None
                return tenant
        
        return None
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)
    
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
        
        # Find or create today's stats
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
        
        # Update stats
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
        
        # Check expiration
        if tenant.expires_at:
            expires = datetime.fromisoformat(tenant.expires_at)
            if datetime.now() > expires:
                return False, "Subscription expired"
        
        # Get today's usage
        today = datetime.now().strftime("%Y-%m-%d")
        today_stats = None
        for stats in self.usage_stats.get(tenant_id, []):
            if stats.date == today:
                today_stats = stats
                break
        
        queries_today = today_stats.queries_made if today_stats else 0
        
        # Check operation-specific limits
        if operation == "query":
            if queries_today >= tenant.max_queries_per_day:
                return False, f"Daily query limit reached ({tenant.max_queries_per_day})"
        
        elif operation == "store_confidential":
            if not tenant.can_store_confidential:
                return False, "Confidential storage not allowed on current tier"
        
        elif operation == "api_call":
            if not tenant.can_use_api:
                return False, "API access not allowed on current tier"
        
        return True, "OK"
    
    def get_usage_report(self, tenant_id: str, days: int = 30) -> Dict:
        """Generate usage report for a tenant"""
        if tenant_id not in self.tenants:
            return {"error": "Tenant not found"}
        
        tenant = self.tenants[tenant_id]
        stats = self.usage_stats.get(tenant_id, [])
        
        # Filter to last N days
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        recent_stats = [s for s in stats if s.date >= cutoff]
        
        total_queries = sum(s.queries_made for s in recent_stats)
        total_api = sum(s.api_calls for s in recent_stats)
        current_storage = max((s.storage_bytes_used for s in recent_stats), default=0)
        
        return {
            "tenant_id": tenant_id,
            "name": tenant.name,
            "tier": tenant.tier.value,
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
                "name": t.name,
                "tier": t.tier.value,
                "created_at": t.created_at,
                "expires_at": t.expires_at
            }
            for t in self.tenants.values()
        ]
    
    def build_query_filter(self, tenant_id: str) -> Optional[Dict]:
        """
        Build ChromaDB filter for tenant isolation
        """
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        
        # Community tier: public documents only
        if tenant.tier == AccessTier.COMMUNITY:
            return {"access_level": "public"}
        
        # Professional/Enterprise: public + tenant's own documents
        return {
            "$or": [
                {"access_level": "public"},
                {"tenant_id": tenant_id}
            ]
        }


class AccessControl:
    """
    Decorator-based access control for API endpoints
    """
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
    
    def require_auth(self, f):
        """Decorator to require API key authentication"""
        def wrapper(*args, **kwargs):
            # Extract API key from request
            api_key = self._extract_api_key(args, kwargs)
            
            tenant = self.tenant_manager.verify_api_key(api_key)
            if not tenant:
                return {"error": "Invalid or expired API key"}, 401
            
            # Add tenant to kwargs
            kwargs['tenant'] = tenant
            return f(*args, **kwargs)
        
        return wrapper
    
    def require_tier(self, min_tier: AccessTier):
        """Decorator to require minimum tier"""
        def decorator(f):
            def wrapper(*args, **kwargs):
                tenant = kwargs.get('tenant')
                if not tenant:
                    return {"error": "Authentication required"}, 401
                
                tier_levels = {
                    AccessTier.COMMUNITY: 1,
                    AccessTier.PROFESSIONAL: 2,
                    AccessTier.ENTERPRISE: 3
                }
                
                if tier_levels[tenant.tier] < tier_levels[min_tier]:
                    return {
                        "error": f"This feature requires {min_tier.value} tier or higher"
                    }, 403
                
                return f(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def check_quota(self, operation: str):
        """Decorator to check quota before operation"""
        def decorator(f):
            def wrapper(*args, **kwargs):
                tenant = kwargs.get('tenant')
                if not tenant:
                    return {"error": "Authentication required"}, 401
                
                allowed, reason = self.tenant_manager.check_quota(
                    tenant.tenant_id, operation
                )
                
                if not allowed:
                    return {"error": reason}, 429
                
                # Record usage after successful call
                result = f(*args, **kwargs)
                self.tenant_manager.record_usage(
                    tenant.tenant_id,
                    query_count=1 if operation == "query" else 0
                )
                
                return result
            
            return wrapper
        return decorator
    
    def _extract_api_key(self, args, kwargs) -> Optional[str]:
        """Extract API key from request"""
        # Check kwargs
        if 'api_key' in kwargs:
            return kwargs['api_key']
        
        # Check for request object (Flask/FastAPI style)
        if 'request' in kwargs:
            request = kwargs['request']
            # Header
            if hasattr(request, 'headers'):
                api_key = request.headers.get('X-API-Key')
                if api_key:
                    return api_key
            
            # Query param
            if hasattr(request, 'args'):
                api_key = request.args.get('api_key')
                if api_key:
                    return api_key
        
        return None


def main():
    """CLI entry point for tenant management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Tenant Manager CLI")
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Create tenant
    create_parser = subparsers.add_parser('create', help='Create new tenant')
    create_parser.add_argument('--name', '-n', required=True, help='Tenant name')
    create_parser.add_argument('--tier', '-t', choices=['community', 'professional', 'enterprise'],
                              default='community', help='Access tier')
    create_parser.add_argument('--days', '-d', type=int, default=365, help='Days valid')
    
    # List tenants
    subparsers.add_parser('list', help='List all tenants')
    
    # Delete tenant
    delete_parser = subparsers.add_parser('delete', help='Delete tenant')
    delete_parser.add_argument('tenant_id', help='Tenant ID')
    
    # Usage report
    usage_parser = subparsers.add_parser('usage', help='Show usage report')
    usage_parser.add_argument('tenant_id', help='Tenant ID')
    usage_parser.add_argument('--days', '-d', type=int, default=30, help='Days to report')
    
    args = parser.parse_args()
    
    manager = TenantManager()
    
    if args.command == 'create':
        tier = AccessTier(args.tier)
        tenant_id, api_key = manager.create_tenant(args.name, tier, args.days)
        print(f"\n✓ Tenant created")
        print(f"  ID: {tenant_id}")
        print(f"  Name: {args.name}")
        print(f"  Tier: {args.tier}")
        print(f"  API Key: {api_key}")
        print(f"\n⚠️  Save the API key securely - it cannot be retrieved later!")
    
    elif args.command == 'list':
        tenants = manager.list_tenants()
        print(f"\n{'ID':<36} {'Name':<30} {'Tier':<15} {'Expires':<20}")
        print("-" * 100)
        for t in tenants:
            print(f"{t['tenant_id']:<36} {t['name']:<30} {t['tier']:<15} {t['expires_at'] or 'Never':<20}")
    
    elif args.command == 'delete':
        if manager.delete_tenant(args.tenant_id):
            print(f"✓ Tenant {args.tenant_id} deleted")
        else:
            print(f"✗ Tenant not found")
    
    elif args.command == 'usage':
        report = manager.get_usage_report(args.tenant_id, args.days)
        if 'error' in report:
            print(f"✗ {report['error']}")
        else:
            print(f"\nUsage Report: {report['name']}")
            print(f"Tier: {report['tier']}")
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
