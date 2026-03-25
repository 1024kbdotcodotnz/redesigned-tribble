# NZ Legal Advisor - Scripts Reference

## Complete Script List

### 🚀 Deployment Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `runpod_setup.sh` | One-click setup on RunPod | Run on RunPod: `./runpod_setup.sh` |
| `upload_to_runpod.sh` | Upload code & database | `./upload_to_runpod.sh <ip>` |
| `connect_runpod.sh` | SSH with port forwarding | `./connect_runpod.sh <ip>` |
| `check_storage.sh` | Verify storage configuration | `./check_storage.sh <ip>` |

### 💾 Backup & Sync Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `backup_runpod.sh` | Backup database from RunPod | `./backup_runpod.sh <ip>` |
| `restore_runpod.sh` | Restore database to RunPod | `./restore_runpod.sh <ip> <path>` |
| `sync_daily.sh` | Two-way sync | `./sync_daily.sh <ip>` |
| `setup_cron.sh` | Auto daily sync (2 AM) | `./setup_cron.sh <ip>` |

### 👥 Staff Management

| Script | Purpose | Usage |
|--------|---------|-------|
| `manage_staff.sh` | Remote staff management | `./manage_staff.sh <ip> list` |
| `staff_management.py` | Local API key management | `python staff_management.py add "Name"` |

---

## Quick Command Reference

### Deploy & Setup
```bash
# 1. Deploy RunPod (RTX 3090, 20GB Container, 50GB Volume)
#    via RunPod Console

# 2. Upload code
./upload_to_runpod.sh 194.36.144.12

# 3. Setup (on RunPod)
ssh root@194.36.144.12
cd /workspace && ./runpod_setup.sh

# 4. Check storage is correct
./check_storage.sh 194.36.144.12
```

### Daily Use
```bash
# Connect and use
./connect_runpod.sh 194.36.144.12
open http://localhost:8501

# Stop pod when done (save money)
# via RunPod Console → Stop
```

### Backup & Maintenance
```bash
# Manual backup
./backup_runpod.sh 194.36.144.12

# Restore if needed
./restore_runpod.sh 194.36.144.12 ./backups/latest

# Sync local changes
./sync_daily.sh 194.36.144.12

# Setup auto-sync
./setup_cron.sh 194.36.144.12
```

### Staff Management
```bash
# List staff
python staff_management.py list

# Add new staff
python staff_management.py add "Jane Smith" --tier professional

# Revoke access
python staff_management.py revoke <tenant-id>
```

---

## File Locations

### Local Machine
```
/home/owner/nz_legal_rag/
├── *.sh                    # All scripts
├── *.py                    # Python utilities
├── chroma_db/              # Local database copy
├── tenant_data/            # API keys
├── backups/                # RunPod backups
└── logs/                   # Sync logs
```

### RunPod (Volume Disk - Persistent)
```
/workspace/
├── nz_legal_rag/           # Application code
│   ├── chroma_db/          # Database (CRITICAL)
│   └── tenant_data/        # API keys (CRITICAL)
├── ollama_models/          # AI models (30GB)
└── start_legal_advisor.sh  # Startup script
```

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Can't connect | Check pod is running in RunPod Console |
| Database lost | Did you use Volume Disk? Redeploy with 50GB Volume |
| Models slow to load | Volume too small - use 50GB+ |
| API not responding | `ssh root@<ip>` then `/workspace/start_legal_advisor.sh` |
| Out of space | Check with `./check_storage.sh <ip>` |
| Forgot API key | Create new one with `python staff_management.py add "Name"` |

---

## Cost Summary

| Item | Monthly Cost |
|------|-------------|
| RTX 3090 GPU (160 hrs) | $35.20 |
| Volume Disk (50GB) | $5.00 |
| **Total** | **$40/month** |
