import discord
import psutil
import asyncio
import os
from datetime import datetime

# Configuration from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
USER_ID = int(os.getenv('DISCORD_USER_ID'))
CPU_THRESHOLD = int(os.getenv('CPU_THRESHOLD', '80'))
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
COOLDOWN_PERIOD = int(os.getenv('COOLDOWN_PERIOD', '300'))  # 5 minutes default

class CPUMonitorBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.last_alert_time = None
        
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print(f'Monitoring CPU usage. Threshold: {CPU_THRESHOLD}%')
        print(f'Check interval: {CHECK_INTERVAL} seconds')
        print(f'Alert cooldown: {COOLDOWN_PERIOD} seconds')
        print(f'Commands: !status, !help')
        self.loop.create_task(self.monitor_cpu())
    
    async def on_message(self, message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
        
        # Only respond to DMs from the configured user
        if isinstance(message.channel, discord.DMChannel) and message.author.id == USER_ID:
            content = message.content.lower().strip()
            
            if content in ['!status', '!stats', '!cpu']:
                await self.send_status(message.channel)
            elif content in ['!help', '!commands']:
                await self.send_help(message.channel)
            elif content == '!test':
                await self.send_test_alert(message.channel)
    
    async def send_status(self, channel):
        """Send current system status"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            message = f"""📊 **System Status**

**CPU Usage:** {cpu_percent}%
**Memory Usage:** {memory.percent}%
**Available Memory:** {memory.available / (1024**3):.2f} GB / {memory.total / (1024**3):.2f} GB
**Load Average:** {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}
**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Alert Threshold:** {CPU_THRESHOLD}%
**Next check in:** ~{CHECK_INTERVAL} seconds"""
            
            await channel.send(message)
            print(f'Status sent to user {USER_ID}')
            
        except Exception as e:
            await channel.send(f'Error getting status: {e}')
            print(f'Error sending status: {e}')
    
    async def send_help(self, channel):
        """Send help message with available commands"""
        help_text = f"""🤖 **CPU Monitor Bot - Commands**

**!status** (or !stats, !cpu)
Get current system status

**!test**
Send a test alert (same format as threshold alerts)

**!help** (or !commands)
Show this help message

**Current Configuration:**
• Threshold: {CPU_THRESHOLD}%
• Check Interval: {CHECK_INTERVAL}s
• Alert Cooldown: {COOLDOWN_PERIOD}s"""
        
        await channel.send(help_text)
        print(f'Help sent to user {USER_ID}')
    
    async def send_test_alert(self, channel):
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
            
            await channel.send(message)
            print(f'Test alert sent to user {USER_ID}')
            
        except Exception as e:
            await channel.send(f'Error sending test alert: {e}')
            print(f'Error sending test alert: {e}')
        
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
            user = await self.fetch_user(USER_ID)
            
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
            
            await user.send(message)
            print(f'Alert sent to user {USER_ID}')
            
        except discord.errors.Forbidden:
            print(f'Cannot send DM to user {USER_ID}. Make sure the bot can DM you.')
        except Exception as e:
            print(f'Error sending alert: {e}')

def main():
    # Validate required environment variables
    if not DISCORD_TOKEN:
        print('Error: DISCORD_BOT_TOKEN environment variable is required')
        return
    
    if not USER_ID:
        print('Error: DISCORD_USER_ID environment variable is required')
        return
    
    # Create and run the bot
    client = CPUMonitorBot()
    client.run(DISCORD_TOKEN)

if __name__ == '__main__':
    main()
