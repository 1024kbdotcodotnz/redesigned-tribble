# NZ Legal Advisor - Solo Practitioner Guide

Complete deployment guide for solo practitioners using RunPod cloud GPU.

## 💰 Cost Summary

| Component | Monthly Cost |
|-----------|-------------|
| RTX 3090 GPU (~160 hrs) | $35.20 |
| Network Storage (50GB) | $2.00 |
| **Total** | **~$37/month** |

---

## 🚀 Quick Start (5 minutes)

### 1. Deploy RunPod Instance ⚠️ STORAGE IS CRITICAL

```bash
# 1. Sign up at https://www.runpod.io
# 2. Go to Console → GPU Pods → Deploy
# 3. Configure:
#    - GPU: RTX 3090 (Community Cloud - $0.22/hr)
#    - Template: PyTorch 2.1 + CUDA 12.1
#    - Container Disk: 20GB  (temporary - OS only)
#    - Volume Disk: 50GB     (PERSISTENT - database + models) ⭐ CRITICAL
#    - Auto-stop: 30 minutes
# 4. Click "Deploy"
# 5. Copy the Pod IP address
#
# ⚠️  WITHOUT VOLUME DISK: Your database is LOST when pod stops!
# ✅ WITH VOLUME DISK: Data persists between stop/start cycles
```

### 2. Run Setup Scripts

```bash
# On your local machine - upload setup
./upload_to_runpod.sh <pod-ip>

# SSH into RunPod and run setup (takes 15-20 minutes)
ssh root@<pod-ip>
cd /workspace && ./runpod_setup.sh

# This will:
# - Install Ollama
# - Download Mixtral (26GB) and embeddings model
# - Setup Python environment
```

### 3. Upload Your Database

```bash
# From local machine
./upload_to_runpod.sh <pod-ip>
```

### 4. Start the Service

```bash
# On RunPod
/workspace/start_legal_advisor.sh
```

### 5. Access Locally

```bash
# From local machine
./connect_runpod.sh <pod-ip>

# Then open browser:
# Web UI: http://localhost:8501
# API:    http://localhost:8000
```

---

## 📦 Daily Workflow

### Morning - Start Your Day

```bash
# 1. Start your RunPod (if stopped)
#    Go to runpod.io/console/pods → Click "Start"

# 2. Connect with port forwarding
./connect_runpod.sh <pod-ip>

# 3. Open browser to http://localhost:8501
```

### Throughout Day - Legal Research

```bash
# Web interface is running at localhost:8501
# API available at localhost:8000

# Quick API test:
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "section 21 BORA search warrant", "top_k": 5}'
```

### Evening - Shutdown (Save Money!)

```bash
# Stop RunPod to avoid charges
# Go to runpod.io/console/pods → Click "Stop"

# Or auto-stop after 30 min inactivity (configured)
```

---

## 🔧 Scripts Reference

### 1. Backup Script
```bash
# Manual backup
./backup_runpod.sh <pod-ip>

# Creates backup in: ./backups/legal_advisor_backup_YYYYMMDD_HHMMSS/
# Auto-cleanup: Keeps last 10 backups
```

### 2. Restore Script
```bash
# Restore from backup
./restore_runpod.sh <pod-ip> ./backups/latest
# OR specify specific backup:
./restore_runpod.sh <pod-ip> ./backups/legal_advisor_backup_20260303_143022
```

### 3. Daily Sync
```bash
# Manual sync (two-way: code → RunPod, database ← RunPod)
./sync_daily.sh <pod-ip>
```

### 4. Automatic Daily Sync
```bash
# Setup cron job (runs daily at 2 AM)
./setup_cron.sh <pod-ip>

# View/Edit: crontab -e
```

### 5. Staff Management
```bash
# List all staff API keys
python staff_management.py list

# Add new staff member
python staff_management.py add "Jane Smith" --tier professional

# Add admin
python staff_management.py add "Admin" --tier enterprise

# Revoke access
python staff_management.py revoke <tenant-id>

# Export staff list
python staff_management.py export --file staff_list.txt
```

---

## 👥 Staff Access Setup

### Create API Keys for Staff

```bash
# 1. Add a staff member (generates API key)
python staff_management.py add "Jane Smith" --tier professional

# Output:
# API Key: nzl_a5801708773d4cca8897dc2afe56dff6_ed40e4323d7e469c
# ⚠️ SAVE THIS - cannot be retrieved later!

# 2. Key is automatically saved to: keys_Jane_Smith.txt

# 3. Staff uses the key:
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer nzl_a5801708773d4cca8897dc2afe56dff6_ed40e4323d7e469c" \
  -d '{"query": "search warrant requirements"}'
```

### Tier Comparison

| Tier | Daily Queries | Storage | Confidential Docs | Best For |
|------|--------------|---------|-------------------|----------|
| community | 100 | 1GB | No | Read-only access |
| professional | 1000 | 10GB | Yes | Lawyers, paralegals |
| enterprise | 10000 | 100GB | Yes | Admin, senior partners |

---

## 💾 Backup Strategy

### Automatic (Recommended)

```bash
# Setup daily backup at 2 AM
./setup_cron.sh <pod-ip>

# This syncs:
# - RunPod database → Local (backup)
# - Local code changes → RunPod (updates)
```

### Manual

```bash
# Before major updates
./backup_runpod.sh <pod-ip>

# Backups stored in: ./backups/
# Latest symlink: ./backups/latest/
```

### Restore After Disaster

```bash
# If RunPod fails, deploy new pod, then:
./restore_runpod.sh <new-pod-ip> ./backups/latest
```

---

## 📊 Monitoring & Logs

### Check Logs

```bash
# On RunPod
tail -f /workspace/nz_legal_rag/logs/api.log

# Local sync logs
tail -f /home/owner/nz_legal_rag/logs/sync.log
```

### Check GPU Usage

```bash
# On RunPod
watch -n 1 nvidia-smi

# Or
ollama ps
```

---

## 🔒 Security Checklist

- [ ] Change default admin API key in `.env`
- [ ] Enable auto-stop (30 min inactivity)
- [ ] Use professional/enterprise tiers for confidential docs
- [ ] Backup database daily
- [ ] Store API keys securely (keys_*.txt files)
- [ ] Revoke access when staff leaves

---

## 🐛 Troubleshooting

### Can't Connect to RunPod
```bash
# Check if pod is running
# RunPod Console → Pods → Status

# Test SSH
ssh root@<pod-ip>
```

### API Not Responding
```bash
# On RunPod - restart services
pkill -f "python -m api.server"
pkill -f streamlit
/workspace/start_legal_advisor.sh
```

### Out of Memory
```bash
# On RunPod - check GPU usage
nvidia-smi

# Use smaller model if needed:
ollama pull mistral:latest  # 4GB instead of 26GB
```

### Database Corrupted
```bash
# Restore from latest backup
./restore_runpod.sh <pod-ip> ./backups/latest
```

---

## 📞 Support Commands

```bash
# Check system health
curl http://localhost:8000/health

# List all API keys
python staff_management.py list

# Quick backup
./backup_runpod.sh <pod-ip>

# Full sync
./sync_daily.sh <pod-ip>
```

---

## 📈 Scaling Up

When your practice grows:

| Upgrade | When | Cost |
|---------|------|------|
| RTX 4090 | Need 20% more speed | +$19/mo |
| A100 40GB | Multiple concurrent users | +$100/mo |
| Always-on | 24/7 availability | $158/mo |

---

**Questions?** Check the main README or API docs at http://localhost:8000/docs
