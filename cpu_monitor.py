import discord
import psutil
import asyncio
import os
from datetime import datetime
from aiohttp import web
import threading

# Configuration from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
USER_ID = int(os.getenv('DISCORD_USER_ID'))
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', '0'))  # Optional: channel for alerts
CPU_THRESHOLD = int(os.getenv('CPU_THRESHOLD', '80'))
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
COOLDOWN_PERIOD = int(os.getenv('COOLDOWN_PERIOD', '300'))  # 5 minutes default
HTTP_PORT = int(os.getenv('HTTP_PORT', '8080'))
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')

class CPUMonitorBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.last_alert_time = None
        self.user_cache = None
        self.channel_cache = None
        
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print(f'Monitoring CPU usage. Threshold: {CPU_THRESHOLD}%')
        print(f'Check interval: {CHECK_INTERVAL} seconds')
        print(f'Alert cooldown: {COOLDOWN_PERIOD} seconds')
        print(f'HTTP endpoint: http://localhost:{HTTP_PORT}')
        print(f'Command prefix: {COMMAND_PREFIX}')
        
        # Cache the user object for DMs
        if USER_ID:
            try:
                self.user_cache = await self.fetch_user(USER_ID)
                print(f'Cached DM user: {self.user_cache.name}')
            except Exception as e:
                print(f'Warning: Could not cache user: {e}')
        
        # Cache the channel object for server alerts
        if CHANNEL_ID:
            try:
                self.channel_cache = await self.fetch_channel(CHANNEL_ID)
                print(f'Cached alert channel: {self.channel_cache.name} in {self.channel_cache.guild.name}')
            except Exception as e:
                print(f'Warning: Could not cache channel: {e}')
        
        if not self.user_cache and not self.channel_cache:
            print('WARNING: No USER_ID or CHANNEL_ID configured. Alerts will not be sent!')
        
        self.loop.create_task(self.monitor_cpu())
    
    async def on_message(self, message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
        
        content = message.content.strip()
        
        # Check if message starts with prefix or mentions the bot
        is_command = False
        command_text = ""
        
        if content.startswith(COMMAND_PREFIX):
            is_command = True
            command_text = content[len(COMMAND_PREFIX):].lower().strip()
        elif self.user.mentioned_in(message):
            is_command = True
            # Remove the mention and get the command
            command_text = message.content.replace(f'<@{self.user.id}>', '').replace(f'<@!{self.user.id}>', '').strip().lower()
        
        if not is_command:
            return
        
        print(f'Command from {message.author.name} in {message.channel}: {command_text}')
        
        # Check permissions - DMs from configured user or messages in configured channel
        has_permission = False
        if isinstance(message.channel, discord.DMChannel) and message.author.id == USER_ID:
            has_permission = True
        elif CHANNEL_ID and message.channel.id == CHANNEL_ID:
            has_permission = True
        elif isinstance(message.channel, discord.TextChannel):
            # Allow in any server channel if CHANNEL_ID is not set
            if not CHANNEL_ID:
                has_permission = True
        
        if not has_permission:
            return
        
        # Process commands
        if command_text in ['status', 'stats', 'cpu']:
            await self.send_status(message.channel)
        elif command_text in ['help', 'commands']:
            await self.send_help(message.channel)
        elif command_text == 'test':
            await self.send_test_alert(message.channel)
        elif command_text == 'ping':
            await message.channel.send('🏓 Pong!')
        elif command_text:
            await message.channel.send(f"Unknown command. Try `{COMMAND_PREFIX}help` for available commands.")
    
    async def get_alert_destination(self):
        """Get the configured alert destination (channel or user DM)"""
        if self.channel_cache:
            return self.channel_cache
        elif self.user_cache:
            return self.user_cache
        elif CHANNEL_ID:
            try:
                return await self.fetch_channel(CHANNEL_ID)
            except Exception as e:
                print(f'Error fetching channel {CHANNEL_ID}: {e}')
        elif USER_ID:
            try:
                return await self.fetch_user(USER_ID)
            except Exception as e:
                print(f'Error fetching user {USER_ID}: {e}')
        return None
    
    async def send_status(self, channel=None):
        """Send current system status"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            alert_mode = "DM" if USER_ID and not CHANNEL_ID else f"Channel"
            
            message = f"""📊 **System Status**

**CPU Usage:** {cpu_percent}%
**Memory Usage:** {memory.percent}%
**Available Memory:** {memory.available / (1024**3):.2f} GB / {memory.total / (1024**3):.2f} GB
**Load Average:** {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}
**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Alert Threshold:** {CPU_THRESHOLD}%
**Alert Mode:** {alert_mode}
**Next check in:** ~{CHECK_INTERVAL} seconds"""
            
            if channel:
                await channel.send(message)
            else:
                # Send to configured destination
                destination = await self.get_alert_destination()
                if destination:
                    await destination.send(message)
                else:
                    print('No alert destination configured!')
                    return False
            
            print(f'Status sent')
            return True
            
        except Exception as e:
            error_msg = f'Error getting status: {e}'
            if channel:
                try:
                    await channel.send(error_msg)
                except:
                    pass
            print(f'Error sending status: {e}')
            return False
    
    async def send_help(self, channel):
        """Send help message with available commands"""
        help_text = f"""🤖 **CPU Monitor Bot - Commands**

**Discord Commands:**
• `{COMMAND_PREFIX}status` (or stats, cpu) - Get current system status
• `{COMMAND_PREFIX}test` - Send a test alert
• `{COMMAND_PREFIX}ping` - Check if bot is responsive
• `{COMMAND_PREFIX}help` (or commands) - Show this message
• `@{self.user.name} status` - Mention the bot with a command

**HTTP Endpoint:**
• `curl http://localhost:{HTTP_PORT}/status`
• `curl http://localhost:{HTTP_PORT}/test`

**Current Configuration:**
• Threshold: {CPU_THRESHOLD}%
• Check Interval: {CHECK_INTERVAL}s
• Alert Cooldown: {COOLDOWN_PERIOD}s
• Alert via: {"Channel" if CHANNEL_ID else "DM"}"""
        
        await channel.send(help_text)
        print(f'Help sent')
    
    async def send_test_alert(self, channel=None):
        """Send a test alert"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            message = f"""🧪 **TEST ALERT**
            
**CPU Usage:** {cpu_percent}%
**Threshold:** {CPU_THRESHOLD}%
**Memory Usage:** {memory.percent}%
**Load Average:** {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}
**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This is a test alert. Real alerts look like this!"""
            
            if channel:
                await channel.send(message)
            else:
                # Send to configured destination
                destination = await self.get_alert_destination()
                if destination:
                    await destination.send(message)
                else:
                    print('No alert destination configured!')
                    return False
            
            print(f'Test alert sent')
            return True
            
        except Exception as e:
            error_msg = f'Error sending test alert: {e}'
            if channel:
                try:
                    await channel.send(error_msg)
                except:
                    pass
            print(f'Error sending test alert: {e}')
            return False
        
    async def monitor_cpu(self):
        await self.wait_until_ready()
        
        while not self.is_closed():
            try:
                # Get CPU usage percentage
                cpu_percent = psutil.cpu_percent(interval=1)
                print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] CPU Usage: {cpu_percent}%')
                
                # Check if threshold is exceeded
                if cpu_percent > CPU_THRESHOLD:
                    # Check cooldown period
                    current_time = datetime.now()
                    if self.last_alert_time is None or \
                       (current_time - self.last_alert_time).total_seconds() > COOLDOWN_PERIOD:
                        
                        await self.send_alert(cpu_percent)
                        self.last_alert_time = current_time
                    else:
                        remaining = COOLDOWN_PERIOD - (current_time - self.last_alert_time).total_seconds()
                        print(f'Alert suppressed. Cooldown remaining: {int(remaining)} seconds')
                
            except Exception as e:
                print(f'Error monitoring CPU: {e}')
            
            await asyncio.sleep(CHECK_INTERVAL)
    
    async def send_alert(self, cpu_percent):
        try:
            destination = await self.get_alert_destination()
            if not destination:
                print('ERROR: No alert destination configured!')
                return
            
            # Get additional system info
            memory = psutil.virtual_memory()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            message = f"""⚠️ **CPU Alert** ⚠️
            
**CPU Usage:** {cpu_percent}%
**Threshold:** {CPU_THRESHOLD}%
**Memory Usage:** {memory.percent}%
**Load Average:** {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}
**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Your CPU usage has exceeded the threshold!"""
            
            await destination.send(message)
            
            if isinstance(destination, discord.TextChannel):
                print(f'Alert sent to channel #{destination.name}')
            else:
                print(f'Alert sent via DM')
            
        except discord.errors.Forbidden:
            print(f'Cannot send message. Check bot permissions.')
        except Exception as e:
            print(f'Error sending alert: {e}')

def main():
    # Validate required environment variables
    if not DISCORD_TOKEN:
        print('Error: DISCORD_BOT_TOKEN environment variable is required')
        return
    
    if not USER_ID and not CHANNEL_ID:
        print('Error: Either DISCORD_USER_ID or DISCORD_CHANNEL_ID must be set')
        print('  - Set DISCORD_USER_ID to send alerts via DM')
        print('  - Set DISCORD_CHANNEL_ID to send alerts to a server channel')
        return
    
    # Create the bot
    client = CPUMonitorBot()
    
    # Setup HTTP server for manual triggers
    app = web.Application()
    
    async def handle_status(request):
        """HTTP endpoint to trigger status message"""
        try:
            success = await client.send_status()
            if success:
                return web.Response(text='Status sent to Discord\n')
            else:
                return web.Response(text='Failed to send status\n', status=500)
        except Exception as e:
            return web.Response(text=f'Error: {e}\n', status=500)
    
    async def handle_test(request):
        """HTTP endpoint to trigger test alert"""
        try:
            success = await client.send_test_alert()
            if success:
                return web.Response(text='Test alert sent to Discord\n')
            else:
                return web.Response(text='Failed to send test alert\n', status=500)
        except Exception as e:
            return web.Response(text=f'Error: {e}\n', status=500)
    
    async def handle_info(request):
        """HTTP endpoint to get bot info"""
        info = f"""CPU Monitor Bot

Endpoints:
  GET /status - Send status message to Discord
  GET /test   - Send test alert to Discord
  GET /info   - This page

Configuration:
  CPU Threshold: {CPU_THRESHOLD}%
  Check Interval: {CHECK_INTERVAL}s
  Cooldown Period: {COOLDOWN_PERIOD}s
  Discord User ID: {USER_ID}

Usage:
  curl http://localhost:{HTTP_PORT}/status
  curl http://localhost:{HTTP_PORT}/test
"""
        return web.Response(text=info)
    
    app.router.add_get('/status', handle_status)
    app.router.add_get('/test', handle_test)
    app.router.add_get('/info', handle_info)
    app.router.add_get('/', handle_info)
    
    # Run HTTP server in background
    async def run_web_server():
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', HTTP_PORT)
        await site.start()
        print(f'HTTP server started on port {HTTP_PORT}')
    
    # Start both the bot and web server
    async def run_both():
        await run_web_server()
        await client.start(DISCORD_TOKEN)
    
    asyncio.run(run_both())

if __name__ == '__main__':
    main()
