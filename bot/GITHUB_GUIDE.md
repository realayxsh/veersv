# GitHub Push Guide

## Step 1 — Create a GitHub Repository

1. Go to https://github.com/new
2. Repository name: `discord-bot` (or any name)
3. Set to **Private** (your bot token should never be public)
4. Click **Create repository**
5. Copy the repository URL (e.g. `https://github.com/yourusername/discord-bot.git`)

---

## Step 2 — Push from Replit

Open the Replit Shell and run:

```bash
cd /home/runner/workspace/bot

# Initialize git
git init

# Add all files (.gitignore will automatically exclude .env and data.json)
git add .

# Commit
git commit -m "Initial bot commit"

# Set remote (replace with YOUR repo URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Authentication:** GitHub now requires a Personal Access Token (not your password):
1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
2. Generate a token with `repo` scope
3. Use it as your password when git asks

---

## Step 3 — Keep Code Updated

After making changes:
```bash
cd /home/runner/workspace/bot
git add .
git commit -m "your change description"
git push
```

---

## On Your AWS Server — Pull Updates

```bash
cd ~/discord-bot/bot   # or wherever you cloned it
git pull
docker-compose up -d --build
```

---

## Important: What's NOT pushed to GitHub

The `.gitignore` file already excludes:
- `.env` — contains your secret bot token ✅
- `data.json` — local server data (you create this on AWS) ✅
- `__pycache__/` — Python cache files ✅

**Never commit your bot token to GitHub.**
