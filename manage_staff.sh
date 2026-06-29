#!/bin/bash
# NZ Legal Advisor - Staff Management Script
# Create and manage API keys for staff members
# Usage: ./manage_staff.sh <runpod-ip>[:port] [command] [args]

RUNPOD_ADDR="$1"
COMMAND="${2:-list}"
shift 2 || true

if [ -z "$RUNPOD_ADDR" ]; then
    echo "Usage:"
    echo "  List all staff:     ./manage_staff.sh <runpod-ip>[:port] list"
    echo "  Add new staff:      ./manage_staff.sh <runpod-ip>[:port] add \"Staff Name\" \"role\""
    echo "  Revoke access:      ./manage_staff.sh <runpod-ip>[:port] revoke \"tenant-id\""
    echo "  Enable API access:  ./manage_staff.sh <runpod-ip>[:port] enable-api \"tenant-id\""
    echo ""
    echo "Roles: community, professional, enterprise"
    echo ""
    echo "Examples:"
    echo "  ./manage_staff.sh 194.36.144.12 list"
    echo "  ./manage_staff.sh 213.192.2.88:40141 list"
    echo "  ./manage_staff.sh 194.36.144.12 add \"Jane Smith\" professional"
    exit 1
fi

# Parse IP and port
RUNPOD_IP=$(echo "$RUNPOD_ADDR" | cut -d: -f1)
RUNPOD_PORT=$(echo "$RUNPOD_ADDR" | grep -o ':[0-9]*$' | tr -d ':')

# Default to port 22 if not specified
if [ -z "$RUNPOD_PORT" ]; then
    RUNPOD_PORT=22
fi

# Check connectivity
if ! ssh -p $RUNPOD_PORT -o ConnectTimeout=5 root@$RUNPOD_IP "echo 'connected'" > /dev/null 2>&1; then
    echo "❌ Cannot connect to RunPod at $RUNPOD_IP:$RUNPOD_PORT"
    exit 1
fi

case "$COMMAND" in
    list)
        echo "══════════════════════════════════════════════════"
        echo "  Staff Access - Current API Keys"
        echo "══════════════════════════════════════════════════"
        echo ""
        ssh -p $RUNPOD_PORT root@$RUNPOD_IP "cd /workspace/nz_legal_rag && source venv/bin/activate && python -m security.tenant_manager list 2>/dev/null || cat tenant_data/tenants.json | python3 -c \"import json,sys; d=json.load(sys.stdin); [print(f'{v[\"tenant_id\"][:8]}... | {v[\"name\"][:20]:<20} | {v[\"tier\"]:<12} | API:{v.get(\"can_use_api\",False)}') for k,v in d.items()]\"" 2>/dev/null || echo "  (No tenants configured)"
        echo ""
        ;;
        
    add)
        STAFF_NAME="$1"
        TIER="${2:-professional}"
        
        if [ -z "$STAFF_NAME" ]; then
            echo "Usage: ./manage_staff.sh <runpod-ip> add \"Staff Name\" [tier]"
            exit 1
        fi
        
        echo "══════════════════════════════════════════════════"
        echo "  Creating Staff Access"
        echo "══════════════════════════════════════════════════"
        echo ""
        echo "Name: $STAFF_NAME"
        echo "Tier: $TIER"
        echo ""
        
        # Create tenant via SSH
        ssh -p $RUNPOD_PORT root@$RUNPOD_IP "cd /workspace/nz_legal_rag && source venv/bin/activate && python -m security.tenant_manager create -n \"$STAFF_NAME\" -t $TIER"
        
        echo ""
        echo "⚠️  Save the API key shown above - it cannot be retrieved later!"
        echo ""
        echo "Enable API access for this key? (y/n): "
        read -r enable_api
        if [ "$enable_api" = "y" ] || [ "$enable_api" = "Y" ]; then
            # Get the tenant ID from the last created entry
            TENANT_ID=$(ssh -p $RUNPOD_PORT root@$RUNPOD_IP "cd /workspace/nz_legal_rag && source venv/bin/activate && python -c \"import json; d=json.load(open('tenant_data/tenants.json')); print(list(d.keys())[-1])\"")
            ssh -p $RUNPOD_PORT root@$RUNPOD_IP "cd /workspace/nz_legal_rag && source venv/bin/activate && python -c \"import json; d=json.load(open('tenant_data/tenants.json')); d['$TENANT_ID']['can_use_api']=True; json.dump(d, open('tenant_data/tenants.json','w'), indent=2)\" && echo '✓ API access enabled'"
        fi
        echo ""
        ;;
        
    revoke)
        TENANT_ID="$1"
        if [ -z "$TENANT_ID" ]; then
            echo "Usage: ./manage_staff.sh <runpod-ip> revoke <tenant-id>"
            echo "Example: ./manage_staff.sh 194.36.144.12 revoke d020b0f7-69b7-4772-bfe1-fbd5704f81b5"
            exit 1
        fi
        
        echo "Revoking access for tenant: $TENANT_ID"
        ssh -p $RUNPOD_PORT root@$RUNPOD_IP "cd /workspace/nz_legal_rag && source venv/bin/activate && python -m security.tenant_manager revoke $TENANT_ID"
        echo "✓ Access revoked"
        ;;
        
    enable-api)
        TENANT_ID="$1"
        if [ -z "$TENANT_ID" ]; then
            echo "Usage: ./manage_staff.sh <runpod-ip> enable-api <tenant-id>"
            exit 1
        fi
        
        echo "Enabling API access for tenant: $TENANT_ID"
        ssh -p $RUNPOD_PORT root@$RUNPOD_IP "cd /workspace/nz_legal_rag && source venv/bin/activate && python -c \"
import json
with open('tenant_data/tenants.json', 'r') as f:
    tenants = json.load(f)
if '$TENANT_ID' in tenants:
    tenants['$TENANT_ID']['can_use_api'] = True
    with open('tenant_data/tenants.json', 'w') as f:
        json.dump(tenants, f, indent=2)
    print('✓ API access enabled for $TENANT_ID')
else:
    print('❌ Tenant not found')
\" && pkill -f 'python -m api.server' 2>/dev/null; sleep 2; nohup python -m api.server > logs/api.log 2>&1 &"
        echo "✓ API server restarted with new permissions"
        ;;
        
    *)
        echo "Unknown command: $COMMAND"
        echo "Use: list, add, revoke, enable-api"
        exit 1
        ;;
esac
