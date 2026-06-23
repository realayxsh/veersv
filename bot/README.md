# Discord Bot

A server management bot with permission-controlled commands, AFK system, and voice channel presence.

## Commands

### Available to Everyone
| Command | Description |
|---------|-------------|
| `-afk <reason>` / `/afk` | Set yourself as AFK |

### Available to Owners & Permitted Users (role: 1502876234705535088)
| Command | Description |
|---------|-------------|
| `-embed #channel message` / `/embed` | Send a transparent embed to a channel |
| `-help` / `/help` | Show all commands |
| `-owners` / `/owners` | List bot owners |

### Owners Only (282494845753491456 & 145759040956399616)
| Command | Description |
|---------|-------------|
| `-perms give @user` / `/perms give` | Give bot permissions to a user |
| `-perms remove @user` / `/perms remove` | Remove bot permissions from a user |
| `-perms list` / `/perms list` | List users with bot permissions |
| `-addowner @user` / `/addowner` | Add a new bot owner |
| `-removeowner @user` / `/removeowner` | Remove a bot owner |

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create `.env`:
   ```
   DISCORD_TOKEN=your_token_here
   ```

3. Create `data.json`:
   ```json
   {"afk": {}, "owners": [282494845753491456, 145759040956399616], "perms": []}
   ```

4. Run:
   ```bash
   python main.py
   ```

## Hosting
- See `AWS_HOSTING_GUIDE.md` for full AWS EC2 deployment
- See `GITHUB_GUIDE.md` for pushing to GitHub
