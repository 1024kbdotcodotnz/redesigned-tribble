# NZ Legal Advisor - RunPod Deployment Guide

Complete automated deployment of NZ Legal Advisor to RunPod GPU Cloud.

## 📋 Prerequisites

1. **RunPod Account** with payment method
2. **Local NZ Legal Advisor** code ready
3. **SSH Key** (usually `~/.ssh/id_ed25519`)

## 🚀 3-Step Deployment

### STEP 1: Setup RunPod (Run in Web Terminal)

1. **Deploy Pod** in RunPod Console:
   - GPU: RTX 3090
   - Container Disk: 20GB
   - **Volume Disk: 50GB** (CRITICAL)
   - Template: PyTorch 2.2 - CUDA 12.1

2. **Open Web Terminal** (RunPod Console → Connect → Web Terminal)

3. **Run Setup Script**:
   ```bash
   # Copy this ENTIRE block and paste in Web Terminal:
   curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/1_setup_runpod.sh | bash
   ```
   
   Or if script is local:
   ```bash
   # First upload script, then:
   bash /workspace/1_setup_runpod.sh
   ```

**Wait:** 15-20 minutes for model download.

**Result:** Ollama installed, models downloaded, directories ready.

---

### STEP 2: Upload Your Code (Run on Local Machine)

**On your local machine:**

```bash
cd /home/owner/nz_legal_rag

# Upload everything
./2_upload_all.sh 1ckakeoxjyi5pz-64411d4b@ssh.runpod.io
```

**Replace** `1ckakeoxjyi5pz-64411d4b@ssh.runpod.io` with your actual RunPod SSH host.

**What gets uploaded:**
- Application code (Python files)
- Legal database (`chroma_db/`)
- API keys (`tenant_data/`)

**Wait:** 1-2 minutes for upload.

---

### STEP 3: Connect & Use (Run on Local Machine)

**Start services on RunPod** (in Web Terminal):
```bash
/workspace/start_legal_advisor.sh
```

**Connect from local machine:**
```bash
./3_connect.sh 1ckakeoxjyi5pz-64411d4b@ssh.runpod.io
```

**Open browser:**
- Web UI: http://localhost:8501
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📁 Script Reference

| Script | Run On | Purpose |
|--------|--------|---------|
| `1_setup_runpod.sh` | RunPod Web Terminal | Install Ollama, download models |
| `2_upload_all.sh` | Local Machine | Upload code & database |
| `3_connect.sh` | Local Machine | SSH with port forwarding |

---

## 💰 Monthly Costs

| Component | Cost |
|-----------|------|
| RTX 3090 (~160 hrs) | $35.20 |
| Volume Disk (50GB) | $5.00 |
| **Total** | **~$40/month** |

---

## 🔧 Daily Workflow

### Morning
```bash
# 1. Start Pod (if stopped) via RunPod Console

# 2. Connect with port forwarding
./3_connect.sh <runpod-ssh-host>

# 3. Open browser to http://localhost:8501
```

### Evening
```bash
# Stop Pod via RunPod Console (save money)
```

---

## 🆘 Troubleshooting

### Can't Connect
```bash
# Test SSH
ssh -i ~/.ssh/id_ed25519 <user>@<host>

# Check if pod is running
# RunPod Console → Pods → Status
```

### Services Not Starting
```bash
# In Web Terminal, check Ollama
ollama ps
nvidia-smi

# Start manually
/workspace/start_legal_advisor.sh
```

### Database Not Found
```bash
# Re-upload database
./2_upload_all.sh <runpod-ssh-host>
```

---

## 📊 What's on Volume Disk (Persistent)

| Path | Content | Size |
|------|---------|------|
| `/workspace/ollama_models/` | AI Models | ~30GB |
| `/workspace/nz_legal_rag/chroma_db/` | Database | ~124MB |
| `/workspace/nz_legal_rag/tenant_data/` | API Keys | ~4KB |

**Survives pod stop/start!**

---

## ✅ Quick Checklist

- [ ] Pod deployed with 50GB Volume Disk
- [ ] Step 1: Setup script completed
- [ ] Step 2: Code uploaded successfully  
- [ ] Step 3: Connected and services running
- [ ] Web UI accessible at localhost:8501

**Deployment complete!** 🎉
