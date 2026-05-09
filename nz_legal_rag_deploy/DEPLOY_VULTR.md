# Deploy NZ Legal RAG to Vultr GPU

This guide walks you through deploying the NZ Legal RAG demo app to a **Vultr Cloud GPU** instance. The demo runs entirely in Docker, so setup is fast and reproducible.

---

## 1. Create the Vultr GPU Instance

1. Log in to [Vultr.com](https://vultr.com)
2. Click **Deploy Server** → **Cloud GPU**
3. **Location:** Choose the closest region to you (e.g., Sydney, Los Angeles, Amsterdam)
4. **GPU Type:** Select **NVIDIA A10 (24 GB)** for the best price/performance
   - *Upgrade to A40 (48 GB) later if you want to run a 70B model for VIP demos.*
5. **Operating System:** **Ubuntu 22.04 LTS**
6. **Plan:** Cloud GPU — NVIDIA A10
7. **Cloud-Init:** Paste the contents of **`vultr-cloud-init.yml`** into the *Cloud-Init User-Data* field.
8. **SSH Key:** Add your public SSH key
9. **Hostname:** `nzlegal-demo`
10. Click **Deploy Now**

⏱️ **Wait ~5 minutes** for the instance to boot and run cloud-init. You can verify this by SSHing in and checking for the MOTD banner.

---

## 2. Get the Server IP

Once the instance shows **Running**, note the **Public IP address** (e.g., `203.0.113.45`).

---

## 3. Deploy from Your Local Machine

From the project root on your laptop/desktop:

```bash
cd /home/megabyte/nz_legal_rag
chmod +x deploy_to_vultr.sh
./deploy_to_vultr.sh 203.0.113.45
```

*(Replace `203.0.113.45` with your actual Vultr IP.)*

### What the script does:
- Creates a tarball of the app (including the 450 MB `chroma_db` contents)
- Uploads it to `/opt/nzlegal` on the server
- Builds and starts the Docker containers
- Waits for the API to pass its health check

⏱️ **First deploy takes ~3–5 minutes** (mostly uploading the DB and building images).

---

## 4. Access the Demo

Once the script finishes:

- **🌐 Web Demo:** `http://<VULTR_IP>`
- **🔌 API Docs:** `http://<VULTR_IP>:8000/docs`

### Demo Accounts
| Username | Password | Role |
|----------|----------|------|
| `admin` | `demo-admin-2024!` | Admin (can manage users, upload permanently) |
| `staff` | `demo-staff-2024!` | Staff (can upload permanently) |
| `user` | `demo-user-2024!` | User (temporary uploads only) |

---

## 5. Managing the Server

SSH into the instance:
```bash
ssh root@203.0.113.45
```

Useful commands:
```bash
# Check service status
sudo systemctl status nzlegal

# View live API logs
sudo docker logs -f nzlegal-api

# View live web logs
sudo docker logs -f nzlegal-web

# Restart everything
sudo docker compose -f /opt/nzlegal/docker-compose.vultr.yml restart

# Stop the demo (saves money if you only run it for meetings)
sudo docker compose -f /opt/nzlegal/docker-compose.vultr.yml down
```

---

## 6. Updating the Demo

If you change code locally and want to push an update:

```bash
./deploy_to_vultr.sh 203.0.113.45
```

The script will re-upload and rebuild only what changed.

---

## 7. Cost-Saving Tips

- **Vultr bills by the minute.** For a demo site, spin it up before a client meeting and shut it down afterward.
- The A10 costs roughly **$1.20–$1.80/hour**. A 1-hour demo = ~$1.50.
- **Storage:** The 450 MB DB is tiny, so block storage costs are negligible.

---

## 8. Troubleshooting

### "Connection refused" on port 80
Wait another 60 seconds for the web container to finish starting, then refresh.

### Ollama model not found
SSH in and pull manually:
```bash
sudo docker exec -it nzlegal-ollama ollama pull llama3.2:3b
```

### GPU not visible inside Docker
Restart the Docker daemon on the server:
```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
sudo docker compose -f /opt/nzlegal/docker-compose.vultr.yml restart
```

### Slow first response
The very first LLM query after a cold start triggers Ollama to load the model into VRAM. This takes ~10–20 seconds. Subsequent queries on the same model are much faster (2–5 s on the A10).

---

## Files Used

| File | Purpose |
|------|---------|
| `vultr-cloud-init.yml` | One-time server setup (Docker, NVIDIA toolkit, model pulls) |
| `docker-compose.vultr.yml` | Production Docker Compose for Vultr |
| `deploy_to_vultr.sh` | One-command deployment script from your local machine |
| `DEPLOY_VULTR.md` | This guide |
