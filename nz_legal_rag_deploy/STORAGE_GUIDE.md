# NZ Legal Advisor - RunPod Storage Guide

## Container Disk vs Volume Disk

### Quick Answer
| Use | Disk Type | Size | Why |
|-----|-----------|------|-----|
| Database | Volume Disk | 20-50GB | Must persist between restarts |
| Ollama Models | Volume Disk | 30-50GB | Avoid 30GB re-downloads |
| Application Code | Container Disk | 10GB | Can re-upload easily |
| Temporary Files | Container Disk | 5GB | Logs, cache, etc. |

**Recommended Config:**
- Container Disk: 20GB
- Volume Disk: 50-100GB

---

## Storage Breakdown

### What Needs to Persist (VOLUME DISK)

```
/workspace/nz_legal_rag/
├── chroma_db/              # 124 MB - YOUR DATABASE - CRITICAL
│   ├── chroma.sqlite3
│   └── index files
├── tenant_data/            # 4 KB - API keys, users - CRITICAL
│   └── tenants.json
├── .env                    # Config file
└── models/ (optional)      # 30GB - Ollama models
```

### What Can Be Rebuilt (CONTAINER DISK)

```
/workspace/nz_legal_rag/
├── venv/                   # Python environment - rebuild with pip
├── logs/                   # Temporary logs
├── __pycache__/            # Python cache
└── uploads/                # Temporary uploads
```

---

## Recommended Configurations

### Option 1: Minimal ($2-3/month storage)
**Best for:** Testing, light use

| Disk | Size | Cost/Month | Stores |
|------|------|------------|--------|
| Container | 20GB | $0 | Code, temp files |
| Volume | 20GB | $2 | Database + API keys |

**Pros:** Cheapest
**Cons:** Must re-download models (26GB) after each stop/start (~10-15 min)

---

### Option 2: Balanced ($4-5/month storage) - RECOMMENDED
**Best for:** Solo practitioners, daily use

| Disk | Size | Cost/Month | Stores |
|------|------|------------|--------|
| Container | 20GB | $0 | Code, temp files |
| Volume | 50GB | $5 | Database + Ollama models |

**Pros:** Fast startup, models persist
**Cons:** None

---

### Option 3: Professional ($8-10/month storage)
**Best for:** Multiple staff, heavy use

| Disk | Size | Cost/Month | Stores |
|------|------|------------|--------|
| Container | 30GB | $0 | Code, multiple models |
| Volume | 100GB | $10 | Database + all models + backups |

**Pros:** Can store multiple LLMs (Mixtral + Llama3.1 + Mistral)
**Cons:** Higher cost

---

## Setup with Volume Disk

### Step 1: Deploy with Volume

```
RunPod Console - Deploy Pod:

GPU: RTX 3090 (Community Cloud)
Container Disk: 20GB
Volume Disk: 50GB  - THIS IS CRITICAL
Template: PyTorch 2.1 + CUDA 12.1
```

### Step 2: Verify Mount

```bash
ssh root@<your-pod-ip>

# Check volume is mounted
df -h
# Should show: /runpod-volume  50G  ...

# Check workspace
ls -la /workspace
# Should be on volume (persistent)
```

### Step 3: Setup Script

The setup script already uses /workspace/ which is on Volume Disk:

```bash
# On RunPod
/workspace/runpod_setup.sh

# This installs to:
# /workspace/nz_legal_rag/          - PERSISTENT (Volume)
# /workspace/ollama_models/         - PERSISTENT (Volume)
```

---

## What Happens When...

### You STOP the Pod
```
Container Disk: WIPED (code gone, but you have local copy)
Volume Disk:    KEPT (database, models, API keys safe)
```

### You START the Pod
```bash
# 1. Container Disk: Fresh Ubuntu + PyTorch
# 2. Volume Disk: Your data still there!
# 3. Just re-run: /workspace/start_legal_advisor.sh
```

### You DELETE the Pod (DANGER)
```
Container Disk: WIPED
Volume Disk:    WIPED (if you delete volume too!)

⚠️ Always backup before deleting!
./backup_runpod.sh <pod-ip>
```

---

## Cost Comparison

| Scenario | Container | Volume | Total | Notes |
|----------|-----------|--------|-------|-------|
| Minimal | 20GB | 20GB | $2/mo | Re-download models each time |
| Recommended | 20GB | 50GB | $5/mo | Models persist, fast restart |
| Professional | 30GB | 100GB | $10/mo | Multiple models, room to grow |

**Storage Pricing:** $0.10/GB/month (Volume only)

---

## Startup Time Comparison

| Storage Config | First Start | After Stop/Start | After Delete |
|----------------|-------------|------------------|--------------|
| 20GB Vol only | 15 min | 15 min | 15 min |
| 50GB Vol w/ models | 15 min | 2 min | 15 min |

**With models on Volume:** 7x faster restart!

---

## Checklist: Verify Your Setup

```bash
# On RunPod - verify persistent storage
ssh root@<your-pod-ip>

# 1. Check volume mount
df -h | grep runpod-volume

# 2. Check workspace is on volume
mount | grep /workspace

# 3. Verify database location
ls -la /workspace/nz_legal_rag/chroma_db/

# 4. Check available space
du -sh /workspace/nz_legal_rag/
du -sh /usr/share/.ollama/models/  # If models installed
```

---

## Common Mistakes

### Mistake 1: No Volume Disk
```
Result: Database lost when pod stops!
Fix: Always add Volume Disk (minimum 20GB)
```

### Mistake 2: Volume Too Small
```
Result: Out of space when downloading models
Fix: Use 50GB+ Volume for models
```

### Mistake 3: Installing on /root/
```bash
# Bad - on Container Disk (lost on restart)
cd /root && git clone ...

# Good - on Volume Disk (persists)
cd /workspace && git clone ...
```

---

## My Recommendation for You

```
Solo Practitioner Configuration
================================
GPU: RTX 3090
Container Disk: 20GB
Volume Disk: 50GB  - PERSISTENT
Auto-stop: 30 minutes

Monthly Costs:
GPU (160 hrs): $35.20
Volume (50GB):  $5.00
------------------
Total:         ~$40/month
```

**Why 50GB Volume?**
- Database: 0.2 GB
- Ollama models: 30 GB (Mixtral + nomic-embed)
- Growth space: 20 GB
- Total: ~50GB

This gives you:
- Fast startup (models persist)
- Database safe between restarts
- Room for additional models
- Reasonable cost
