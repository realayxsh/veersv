# AWS Hosting Guide — Complete Step-by-Step

## Overview
This guide walks you through hosting your Discord bot on an **Amazon EC2** instance using Docker.
The bot will run 24/7, auto-restart on crashes, and keep `data.json` on disk across restarts.

---

## Step 1 — Create an AWS Account
If you don't have one: https://aws.amazon.com/free

---

## Step 2 — Launch an EC2 Instance

1. Go to **EC2 Dashboard** → **Launch Instance**
2. **Name:** `discord-bot`
3. **AMI:** Choose `Ubuntu Server 22.04 LTS` (Free tier eligible)
4. **Instance type:** `t2.micro` (Free tier) or `t3.small` for better performance
5. **Key pair:** Create a new key pair → download the `.pem` file → save it safely
6. **Security Group:** Allow inbound SSH (port 22) from your IP only
7. Click **Launch Instance**

---

## Step 3 — Connect to Your Server

On your computer (Linux/Mac):
```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

On Windows: Use **PuTTY** or **Windows Terminal** with the .pem file.

---

## Step 4 — Install Docker on the Server

Run these commands on your EC2 instance:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install -y docker-compose

# Add ubuntu user to docker group (no sudo needed)
sudo usermod -aG docker ubuntu

# Log out and back in for the group change to take effect
exit
```

SSH back in after logging out.

---

## Step 5 — Get Your Bot Code on the Server

### Option A — Clone from GitHub (recommended)
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO/bot
```

### Option B — Upload files directly
On your local machine:
```bash
scp -i your-key.pem -r ./bot ubuntu@YOUR_EC2_PUBLIC_IP:~/bot
```
Then on the server:
```bash
cd ~/bot
```

---

## Step 6 — Set Your Bot Token

On the EC2 server, inside the `bot/` folder:
```bash
# Create the .env file with your real token
echo "DISCORD_TOKEN=your_actual_bot_token_here" > .env
```

**How to get your bot token:**
1. Go to https://discord.com/developers/applications
2. Select your bot application
3. Go to **Bot** → **Reset Token** → Copy it
4. Paste it in the `.env` file above

---

## Step 7 — Create the data.json file

```bash
echo '{"afk": {}, "owners": [282494845753491456, 145759040956399616], "perms": []}' > data.json
```

---

## Step 8 — Start the Bot

```bash
# Build and start the bot (runs in background, auto-restarts)
docker-compose up -d --build

# Check if it's running
docker-compose ps

# View live logs
docker-compose logs -f
```

You should see:
```
✅ Logged in as YourBot#1234 (...)
✅ Synced X slash commands
🔊 Joined VC: ...
```

---

## Step 9 — Bot Permissions in Discord

In your Discord **Developer Portal**:
1. Go to your app → **Bot**
2. Enable these Privileged Intents:
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent**
3. Go to **OAuth2 → URL Generator**
4. Scopes: `bot` + `applications.commands`
5. Bot Permissions: `Administrator` (easiest) or manually:
   - Send Messages, Embed Links, Manage Roles, Connect, Speak, Move Members

---

## Step 10 — Useful Commands

```bash
# Stop the bot
docker-compose down

# Restart the bot
docker-compose restart

# Update bot after code change
git pull
docker-compose up -d --build

# View logs
docker-compose logs -f bot

# Check data.json
cat data.json
```

---

## Auto-Start on Server Reboot

The `restart: always` in `docker-compose.yml` already handles this.
But also enable Docker to start on boot:
```bash
sudo systemctl enable docker
```

---

## Keeping Your Server Safe

1. **Never share your `.env` file or bot token publicly**
2. **Set up automatic security updates:**
   ```bash
   sudo apt install -y unattended-upgrades
   sudo dpkg-reconfigure --priority=low unattended-upgrades
   ```
3. **Create an Elastic IP** in AWS so your server IP never changes (optional but recommended)

---

## Cost Estimate

| Plan | Monthly Cost |
|------|-------------|
| t2.micro (Free Tier, first 12 months) | $0 |
| t2.micro after free tier | ~$8/month |
| t3.small (recommended for 24/7 bot) | ~$15/month |

---

## Troubleshooting

**Bot not connecting to voice channel:**
- Make sure the bot has `Connect` and `Speak` permissions in that specific channel

**Slash commands not showing:**
- Wait up to 1 hour for global sync, or use guild-specific sync for instant results

**Bot crashes on start:**
- Run `docker-compose logs bot` to see the error
- Most common: wrong token or missing intents in Developer Portal

**data.json not saving:**
- The volume mount in `docker-compose.yml` maps `./data.json` to the container
- Make sure `data.json` exists in the same folder as `docker-compose.yml`
