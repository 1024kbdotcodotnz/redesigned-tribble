# RunPod Connection Guide

## Current Connection Info

```
SSH Command: ssh hfm6dv73af3es0-64410b2f@ssh.runpod.io -i ~/.ssh/id_ed25519
Password: 29fxgw5i462wfscmhgj6
```

## Connection Methods

### Method 1: Direct SSH (Try This)

```bash
ssh hfm6dv73af3es0-64410b2f@ssh.runpod.io -i ~/.ssh/id_ed25519
```

If that fails, try:

```bash
# Use the config we created
ssh runpod

# Or with verbose output
ssh -v hfm6dv73af3es0-64410b2f@ssh.runpod.io -i ~/.ssh/id_ed25519
```

### Method 2: Password Authentication

```bash
ssh hfm6dv73af3es0-64410b2f@ssh.runpod.io
# When prompted for password: 29fxgw5i462wfscmhgj6
```

### Method 3: Web Terminal (Easiest)

1. Go to https://www.runpod.io/console/pods
2. Click your pod
3. Click **"Web Terminal"**
4. You get a browser-based terminal - no SSH needed!

---

## Once Connected

### Check Storage
```bash
df -h | grep -E "(Filesystem|workspace|volume)"
```

### Setup NZ Legal Advisor
```bash
cd /workspace
ls -la
```

If the code is not there, you need to upload it first.

---

## If SSH Keeps Failing

### Option A: Download New SSH Key from RunPod

1. RunPod Console → Your Pod → Connect
2. Look for "Download Private Key" button
3. Save to `~/.ssh/runpod_key`
4. Try: `ssh -i ~/.ssh/runpod_key hfm6dv73af3es0-64410b2f@ssh.runpod.io`

### Option B: Use Web Terminal for Everything

Just use the Web Terminal in RunPod Console - it bypasses all SSH issues!

---

## Quick Test Commands

```bash
# Test basic connection
ssh hfm6dv73af3es0-64410b2f@ssh.runpod.io "echo 'Hello from RunPod'"

# Check GPU
ssh hfm6dv73af3es0-64410b2f@ssh.runpod.io "nvidia-smi"

# Check disk space
ssh hfm6dv73af3es0-64410b2f@ssh.runpod.io "df -h"
```
