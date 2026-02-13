# CPU Monitor Discord Bot

A Docker-based bot that monitors your Linux system's CPU usage and sends you Discord DM alerts when it exceeds a specified threshold.

## Features

- 🔍 Monitors host CPU usage (not container CPU)
- 📨 Sends Discord DMs when CPU exceeds threshold
- ⏱️ Configurable check interval and alert cooldown
- 🐳 Fully containerized with Docker
- 🔄 Auto-restart on failure
- 📊 Includes memory usage and load average in alerts

## Prerequisites

- Docker and Docker Compose installed
- A Discord bot token
- Your Discord user ID

## Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot"
5. Under "TOKEN", click "Reset Token" and copy it (you'll need this)
6. **Important:** Under "Privileged Gateway Intents", enable **"Message Content Intent"** (required for commands)
7. Go to "OAuth2" > "URL Generator"
8. Select scopes: `bot`
9. Select bot permissions: `Send Messages`
10. Copy the generated URL and open it in your browser to invite the bot to a server (or just use it for DMs)

### 2. Get Your Discord User ID

1. Open Discord
2. Go to User Settings > Advanced
3. Enable "Developer Mode"
4. Right-click on your username anywhere and select "Copy ID"

### 3. Configure the Bot

1. Clone or download this repository
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and fill in your details:
   ```env
   DISCORD_BOT_TOKEN=your_actual_bot_token
   DISCORD_USER_ID=your_actual_user_id
   CPU_THRESHOLD=80
   CHECK_INTERVAL=60
   COOLDOWN_PERIOD=300
   ```

### 4. Run the Bot

Using Docker Compose (recommended):
```bash
docker-compose up -d
```

Or using Docker directly:
```bash
docker build -t cpu-monitor .
docker run -d \
  --name cpu-monitor-bot \
  --restart unless-stopped \
  --pid host \
  -v /proc:/host/proc:ro \
  --env-file .env \
  cpu-monitor
```

### 5. Verify It's Working

Check the logs:
```bash
docker-compose logs -f
```

You should see output like:
```
Logged in as YourBot#1234
Monitoring CPU usage. Threshold: 80%
Check interval: 60 seconds
[2024-02-12 10:30:00] CPU Usage: 45.2%
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | *required* | Your Discord bot token |
| `DISCORD_USER_ID` | *required* | Your Discord user ID |
| `CPU_THRESHOLD` | 80 | CPU percentage threshold for alerts |
| `CHECK_INTERVAL` | 60 | How often to check CPU (seconds) |
| `COOLDOWN_PERIOD` | 300 | Minimum time between alerts (seconds) |
| `HTTP_PORT` | 8080 | Port for HTTP trigger endpoints |

## Bot Commands

### Discord Commands
You can DM the bot these commands:

| Command | Description |
|---------|-------------|
| `!status` (or `!stats`, `!cpu`) | Get current CPU, memory, and load average |
| `!test` | Send a test alert to see what alerts look like |
| `!help` (or `!commands`) | Show available commands |

**Note:** Discord commands require "Message Content Intent" enabled in your bot settings.

### HTTP Endpoints (Recommended)
The bot also runs an HTTP server for more reliable manual triggers:

```bash
# Get current status
curl http://localhost:8080/status

# Send test alert
curl http://localhost:8080/test

# Get bot info
curl http://localhost:8080/info
```

You can also trigger from anywhere on your network:
```bash
curl http://your-server-ip:8080/status
```

**These HTTP endpoints are much more reliable than Discord commands!**

## How It Works

1. The bot monitors your **host system's** CPU usage (not the container's)
2. Every `CHECK_INTERVAL` seconds, it checks the current CPU percentage
3. If CPU > `CPU_THRESHOLD`, it sends you a Discord DM
4. To prevent spam, it won't send another alert until `COOLDOWN_PERIOD` has passed
5. The alert includes CPU usage, memory usage, load average, and timestamp

## Troubleshooting

### Discord commands not working

If `!status` and other commands don't work:
1. **Use HTTP endpoints instead** (more reliable): `curl http://localhost:8080/status`
2. Make sure "Message Content Intent" is enabled in Discord Developer Portal
3. Check the logs for "Received message from..." to see if bot is receiving messages
4. Try restarting the bot after enabling the intent

### Bot can't send me DMs

- Make sure you share at least one server with the bot
- Check your Discord privacy settings (User Settings > Privacy & Safety > Allow direct messages from server members)
- Try sending the bot a message first

### CPU reading is always low/wrong

- Make sure you're using `--pid host` and mounting `/proc`
- The docker-compose.yml already includes these settings

### Bot crashes or restarts

Check logs with:
```bash
docker-compose logs cpu-monitor
```

Common issues:
- Invalid bot token
- Invalid user ID
- Bot doesn't have permission to send messages

## Management Commands

Start the bot:
```bash
docker-compose up -d
```

Stop the bot:
```bash
docker-compose down
```

View logs:
```bash
docker-compose logs -f
```

Restart the bot:
```bash
docker-compose restart
```

Rebuild after changes:
```bash
docker-compose up -d --build
```

## Security Notes

- Never commit your `.env` file to version control
- Keep your bot token secret
- The bot only needs "Send Messages" permission
- The container runs with host PID namespace to read CPU stats - this is necessary but means the container can see host processes

## License

MIT License - feel free to modify and use as needed!
