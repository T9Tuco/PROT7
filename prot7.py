#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Prot7 Security Discord Bot
# Version: 1.5.7
# Author: T9Tuco

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
import os
import re
import threading
import time
import signal
import sys

try:
    import discord
    from discord.ext import commands, tasks
    from discord import app_commands
except ImportError:
    print("Error: discord.py is not installed!")
    print("Please install it with: pip3 install discord.py")
    exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('prot7.log'),
        logging.StreamHandler()
    ]
)

# Global variables for graceful shutdown
bot_running = True
shutdown_event = threading.Event()

class Prot7Bot:
    def __init__(self):
        # Log startup information
        print(f"Starting Prot7 Security Bot (PID: {os.getpid()})...")
        logging.info(f"Starting Prot7 Security Bot (PID: {os.getpid()})...")
        
        try:
            # Load token from env file
            self.token = self.load_token_from_env()
            if not self.token:
                print("ERROR: Discord token not found in prot7.env")
                logging.error("Discord token not found in prot7.env")
                raise ValueError("Discord token not found")
            
            # Load configuration
            self.config = self.load_config()
            
            # Initialize Discord bot
            self.intents = discord.Intents.all()
            self.bot = commands.Bot(command_prefix=self.config.get('prefix', '!p7'), intents=self.intents)
            
            # Initialize database
            self.db = self.initialize_database()
            
            # Initialize trackers
            self.spam_tracker = {}
            self.raid_protection = {}
            self.last_config_check = time.time()
            self.config_lock = threading.Lock()
            self.current_status = "STARTING"
            
            # Set up event handlers and commands
            self.setup_bot_events()
            self.setup_bot_commands()
            self.setup_slash_commands()
            
            # Set up signal handlers
            self.setup_signal_handlers()
            
            # Store bot reference for access in commands
            self.bot.prot7_bot = self
            
            logging.info("Bot initialization successful")
            print("Bot initialization successful")
        except Exception as e:
            error_msg = f"Error during bot initialization: {str(e)}"
            logging.error(error_msg)
            print(f"ERROR: {error_msg}")
            raise
    
    def load_token_from_env(self):
        """Load bot token from prot7.env file"""
        env_file = 'prot7.env'
        token = None
        
        # Check if file exists
        if not os.path.exists(env_file):
            logging.warning(f"Environment file {env_file} not found, creating it")
            with open(env_file, 'w') as f:
                f.write("# Prot7 Discord Security Bot Configuration\n")
                f.write("DISCORD_TOKEN=\n")
            return None
        
        # Read token from file
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('DISCORD_TOKEN='):
                        token_value = line.split('=', 1)[1].strip()
                        if token_value and token_value != "YOUR_DISCORD_TOKEN_HERE":
                            token = token_value
                            break
            if token:
                logging.info("Discord token loaded from environment file")
            else:
                logging.warning("No valid Discord token found in environment file")
        except Exception as e:
            logging.error(f"Error reading environment file: {e}")
        
        return token
    
    def load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                logging.info("Configuration loaded successfully")
                return config
        except FileNotFoundError:
            logging.warning("Config file not found, creating default config")
            default_config = {
                "prefix": "!p7",
                "admin_roles": [],
                "mod_roles": [],
                "log_channel": None,
                "mod_log_channel": None,
                "blocked_words": ["spam", "badword"],
                "modules": {
                    "anti_spam": True,
                    "auto_mod": True,
                    "channel_guard": True,
                    "user_tracking": True
                }
            }
            with open('config.json', 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            # Return minimal config to keep bot functional
            return {"prefix": "!p7", "modules": {}, "blocked_words": []}
    
    def initialize_database(self):
        """Initialize SQLite database"""
        logging.info("Initializing database")
        try:
            conn = sqlite3.connect('prot7.db')
            cursor = conn.cursor()
            
            # Create messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    username TEXT,
                    channel_id TEXT,
                    guild_id TEXT,
                    content TEXT,
                    timestamp DATETIME,
                    message_type TEXT
                )
            ''')
            
            # Create security events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    user_id TEXT,
                    details TEXT,
                    timestamp DATETIME,
                    severity TEXT
                )
            ''')
            
            # Create server stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS server_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    member_count INTEGER,
                    channel_count INTEGER,
                    timestamp DATETIME
                )
            ''')
            
            # Create moderation actions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderation_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    user_id TEXT,
                    moderator_id TEXT,
                    action_type TEXT,
                    reason TEXT,
                    timestamp DATETIME
                )
            ''')
            
            conn.commit()
            logging.info("Database initialized successfully")
            return conn
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
            print(f"Database error: {e}")
            return None
    
    def log_message(self, message):
        """Log message to database"""
        if not self.db:
            return
            
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                INSERT INTO messages (user_id, username, channel_id, guild_id, content, timestamp, message_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(message.author.id),
                message.author.name,
                str(message.channel.id),
                str(message.guild.id) if message.guild else None,
                message.content,
                datetime.now(),
                'user_message'
            ))
            self.db.commit()
        except Exception as e:
            logging.error(f"Failed to log message: {e}")
    
    def log_security_event(self, event_type, user_id, details, severity="medium"):
        """Log security event to database and send to log channel"""
        if not self.db:
            return
            
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                INSERT INTO security_events (event_type, user_id, details, timestamp, severity)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                event_type,
                str(user_id) if user_id else "system",
                details,
                datetime.now(),
                severity
            ))
            self.db.commit()
            
            logging.warning(f"Security Event: {event_type} - User: {user_id} - {details}")
            
            # Send to Discord log channel asynchronously
            asyncio.create_task(self.send_log_embed(event_type, user_id, details, severity))
        except Exception as e:
            logging.error(f"Failed to log security event: {e}")
    
    async def send_log_embed(self, event_type, user_id, details, severity="medium"):
        """Send log embed to configured log channel"""
        with self.config_lock:
            log_channel_id = self.config.get('log_channel')
        
        if not log_channel_id:
            return
            
        try:
            channel = self.bot.get_channel(int(log_channel_id))
            if not channel:
                return
                
            # Color based on severity
            color_map = {
                "low": 0x00ff00,     # Green
                "medium": 0xffa500,  # Orange
                "high": 0xff0000     # Red
            }
            
            embed = discord.Embed(
                title=f"🛡️ Security Event: {event_type.replace('_', ' ').title()}",
                color=color_map.get(severity, 0xffa500),
                timestamp=datetime.now()
            )
            
            if user_id:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    embed.add_field(name="👤 User", value=f"{user.mention} (`{user.id}`)", inline=True)
                except:
                    embed.add_field(name="👤 User ID", value=user_id, inline=True)
            
            embed.add_field(name="📝 Details", value=details, inline=False)
            embed.add_field(name="⚠️ Severity", value=severity.upper(), inline=True)
            embed.set_footer(text=f"Prot7 Security System")
            
            await channel.send(embed=embed)
            logging.info(f"Security event logged to channel: {event_type}")
        except Exception as e:
            logging.error(f"Failed to send log embed: {e}")
    
    async def on_message_handler(self, message):
        """Handle incoming messages"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Process commands
        await self.bot.process_commands(message)
        
        # Check if auto-mod is enabled
        with self.config_lock:
            auto_mod_enabled = self.config['modules'].get('auto_mod', True)
        
        if not auto_mod_enabled:
            return
        
        # Log message to database
        self.log_message(message)
        
        # Run moderation checks
        if await self.check_message_content(message):
            return
        
        # Check for spam
        if await self.check_for_spam(message):
            return
    
    async def check_message_content(self, message):
        """Check message content for blocked words"""
        with self.config_lock:
            blocked_words = self.config.get('blocked_words', [])
        
        for word in blocked_words:
            if word.lower() in message.content.lower():
                try:
                    await message.delete()
                    self.log_security_event("blocked_word", message.author.id, f"Used blocked word: {word}", "medium")
                    try:
                        await message.author.send(f"⚠️ Your message was deleted for containing a blocked word: `{word}`")
                    except:
                        pass
                    return True
                except Exception as e:
                    logging.error(f"Failed to delete message: {e}")
        
        return False
    
    async def check_for_spam(self, message):
        """Check message for spam patterns"""
        with self.config_lock:
            anti_spam_enabled = self.config['modules'].get('anti_spam', True)
        
        if not anti_spam_enabled:
            return False
        
        user_id = str(message.author.id)
        current_time = datetime.now()
        
        # Initialize user tracker
        if user_id not in self.spam_tracker:
            self.spam_tracker[user_id] = {
                'messages': [],
                'warnings': 0,
                'last_warning': None
            }
        
        # Clean old messages (older than 1 minute)
        self.spam_tracker[user_id]['messages'] = [
            msg for msg in self.spam_tracker[user_id]['messages']
            if current_time - msg['time'] < timedelta(minutes=1)
        ]
        
        # Add current message
        self.spam_tracker[user_id]['messages'].append({
            'content': message.content,
            'time': current_time
        })
        
        user_messages = self.spam_tracker[user_id]['messages']
        
        # Check for spam patterns
        spam_detected = False
        reason = ""
        
        # Too many messages in short time
        if len(user_messages) > 8:
            spam_detected = True
            reason = "Too many messages in short time"
        
        # Repeated content
        elif len(user_messages) >= 3:
            recent_content = [msg['content'] for msg in user_messages[-3:]]
            if len(set(recent_content)) == 1:
                spam_detected = True
                reason = "Repeated message content"
        
        # Very long message
        elif len(message.content) > 1000:
            spam_detected = True
            reason = "Message too long"
        
        # Too many mentions
        elif len(message.mentions) > 5:
            spam_detected = True
            reason = "Too many user mentions"
        
        if spam_detected:
            try:
                await message.delete()
                self.spam_tracker[user_id]['warnings'] += 1
                self.spam_tracker[user_id]['last_warning'] = current_time
                
                # Progressive punishment
                if self.spam_tracker[user_id]['warnings'] >= 3:
                    # Timeout for 10 minutes
                    try:
                        await message.author.timeout(duration=timedelta(minutes=10), reason=f"Spam: {reason}")
                        self.log_security_event("spam_timeout", message.author.id, f"User timed out for spam: {reason}", "high")
                    except Exception as e:
                        logging.error(f"Failed to timeout user: {e}")
                elif self.spam_tracker[user_id]['warnings'] >= 2:
                    # Warning message
                    try:
                        await message.author.send(f"⚠️ **Spam Warning**: {reason}. One more spam message will result in a timeout.")
                    except:
                        pass
                    self.log_security_event("spam_warning", message.author.id, f"Spam warning: {reason}", "medium")
                
                self.log_security_event("spam_detected", message.author.id, reason, "medium")
                return True
            except Exception as e:
                logging.error(f"Failed to handle spam: {e}")
        
        return False
    
    async def check_raid_protection(self, member):
        """Check for potential raid when new member joins"""
        with self.config_lock:
            channel_guard_enabled = self.config['modules'].get('channel_guard', True)
        
        if not channel_guard_enabled:
            return
        
        guild_id = str(member.guild.id)
        current_time = datetime.now()
        
        if guild_id not in self.raid_protection:
            self.raid_protection[guild_id] = []
        
        # Clean old joins (older than 5 minutes)
        self.raid_protection[guild_id] = [
            join_time for join_time in self.raid_protection[guild_id]
            if current_time - join_time < timedelta(minutes=5)
        ]
        
        # Add current join
        self.raid_protection[guild_id].append(current_time)
        
        # Check if too many joins in short time (potential raid)
        if len(self.raid_protection[guild_id]) > 10:  # 10 joins in 5 minutes
            self.log_security_event("potential_raid", member.id, f"Potential raid detected: {len(self.raid_protection[guild_id])} joins in 5 minutes", "high")
            
            # Check if account is new (created less than 7 days ago)
            account_age = current_time - member.created_at
            if account_age < timedelta(days=7):
                try:
                    await member.kick(reason="Raid protection: New account during potential raid")
                    self.log_security_event("raid_kick", member.id, f"Kicked new account during raid (age: {account_age.days} days)", "high")
                except Exception as e:
                    logging.error(f"Failed to kick user: {e}")
    
    def setup_bot_events(self):
        """Set up Discord event handlers"""
        logging.info("Setting up event handlers")
        
        @self.bot.event
        async def on_ready():
            print(f'🛡️ Prot7 is online! Logged in as {self.bot.user}')
            logging.info(f'Bot started as {self.bot.user}')
            
            # Update status
            self.current_status = "ONLINE"
            
            # Sync slash commands
            try:
                synced = await self.bot.tree.sync()
                print(f"Synced {len(synced)} slash commands")
                logging.info(f"Synced {len(synced)} slash commands")
            except Exception as e:
                print(f"Failed to sync slash commands: {e}")
                logging.error(f"Failed to sync slash commands: {e}")
            
            # Start background tasks
            self.cleanup_old_data.start()
            self.config_monitor.start()
            self.update_server_stats.start()
            
            # Set custom status
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="for security threats"
                ),
                status=discord.Status.online
            )
            
            # Send startup notification
            self.log_security_event("bot_started", None, f"Prot7 bot started successfully as {self.bot.user}", "low")
        
        @self.bot.event
        async def on_message(message):
            await self.on_message_handler(message)
        
        @self.bot.event
        async def on_member_join(member):
            self.log_security_event("member_join", member.id, f"User {member.name} joined server", "low")
            
            # Raid protection
            await self.check_raid_protection(member)
            
            # Check if user was previously banned
            try:
                bans = [ban async for ban in member.guild.bans()]
                if any(ban.user.id == member.id for ban in bans):
                    self.log_security_event("banned_user_rejoin", member.id, "Previously banned user attempted to rejoin", "high")
            except Exception as e:
                logging.error(f"Failed to check bans: {e}")
        
        @self.bot.event
        async def on_member_remove(member):
            self.log_security_event("member_leave", member.id, f"User {member.name} left server", "low")
        
        @self.bot.event
        async def on_message_delete(message):
            if message.author.bot:
                return
            
            with self.config_lock:
                user_tracking_enabled = self.config['modules'].get('user_tracking', True)
            
            if user_tracking_enabled:
                self.log_security_event("message_deleted", message.author.id, f"Message deleted: {message.content[:100]}", "low")
        
        @self.bot.event
        async def on_message_edit(before, after):
            if before.author.bot or before.content == after.content:
                return
            
            with self.config_lock:
                user_tracking_enabled = self.config['modules'].get('user_tracking', True)
            
            if user_tracking_enabled:
                self.log_security_event("message_edited", before.author.id, f"Message edited from: {before.content[:50]} to: {after.content[:50]}", "low")
    
    @tasks.loop(minutes=1)
    async def config_monitor(self):
        """Monitor config file for changes"""
        try:
            config_mtime = os.path.getmtime('config.json')
            if config_mtime > self.last_config_check:
                old_config = self.config.copy()
                
                with open('config.json', 'r') as f:
                    self.config = json.load(f)
                
                # Update prefix if changed
                if old_config.get('prefix') != self.config.get('prefix'):
                    self.bot.command_prefix = self.config.get('prefix', '!p7')
                
                self.last_config_check = config_mtime
                logging.info("Configuration reloaded due to file change")
        except Exception as e:
            logging.error(f"Error checking config changes: {e}")
    
    @tasks.loop(hours=1)
    async def cleanup_old_data(self):
        """Clean up old data periodically"""
        current_time = datetime.now()
        
        # Clean spam tracker
        for user_id in list(self.spam_tracker.keys()):
            # Reset warnings after 1 hour
            if (self.spam_tracker[user_id].get('last_warning') and 
                current_time - self.spam_tracker[user_id]['last_warning'] > timedelta(hours=1)):
                self.spam_tracker[user_id]['warnings'] = 0
        
        # Clean raid protection data
        for guild_id in list(self.raid_protection.keys()):
            self.raid_protection[guild_id] = [
                join_time for join_time in self.raid_protection[guild_id]
                if current_time - join_time < timedelta(hours=1)
            ]
        
        logging.info("Cleaned up old data")
    
    @tasks.loop(hours=6)
    async def update_server_stats(self):
        """Update server statistics periodically"""
        if not self.db:
            return
            
        for guild in self.bot.guilds:
            try:
                cursor = self.db.cursor()
                cursor.execute('''
                    INSERT INTO server_stats (guild_id, member_count, channel_count, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (
                    str(guild.id),
                    guild.member_count,
                    len(guild.channels),
                    datetime.now()
                ))
                self.db.commit()
            except Exception as e:
                logging.error(f"Failed to update server stats: {e}")
        
        logging.info("Updated server statistics")
    
    def setup_bot_commands(self):
        """Set up traditional prefix commands"""
        logging.info("Setting up bot commands")
        
        @self.bot.command(name='status')
        @commands.has_permissions(administrator=True)
        async def status(ctx):
            """Show bot status"""
            embed = discord.Embed(title="🛡️ Prot7 Status", color=0x00ff00)
            embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
            embed.add_field(name="Users", value=sum(g.member_count for g in self.bot.guilds), inline=True)
            embed.add_field(name="Status", value=self.current_status, inline=True)
            embed.add_field(name="Modules", value="\n".join([f"✅ {k}" for k, v in self.config['modules'].items() if v]), inline=False)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='lockdown')
        @commands.has_permissions(administrator=True)
        async def lockdown(ctx, channel: discord.TextChannel = None):
            """Lock down a channel"""
            if not channel:
                channel = ctx.channel
            
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
            await ctx.send(f"🔒 Channel {channel.mention} is now locked down.")
            self.log_security_event("lockdown", ctx.author.id, f"Locked channel {channel.id}", "high")
        
        @self.bot.command(name='unlock')
        @commands.has_permissions(administrator=True)
        async def unlock(ctx, channel: discord.TextChannel = None):
            """Unlock a channel"""
            if not channel:
                channel = ctx.channel
            
            await channel.set_permissions(ctx.guild.default_role, send_messages=True)
            await ctx.send(f"🔓 Channel {channel.mention} is now unlocked.")
            self.log_security_event("unlock", ctx.author.id, f"Unlocked channel {channel.id}", "medium")
        
        @self.bot.command(name='reload')
        @commands.has_permissions(administrator=True)
        async def reload_config_cmd(ctx):
            """Reload bot configuration"""
            try:
                with open('config.json', 'r') as f:
                    self.config = json.load(f)
                await ctx.send("✅ Configuration reloaded!")
            except Exception as e:
                await ctx.send(f"❌ Failed to reload config: {e}")
    
    def setup_slash_commands(self):
        """Set up slash commands"""
        logging.info("Setting up slash commands")
        
        @self.bot.tree.command(name="security_status", description="Show security system status")
        async def security_status(interaction: discord.Interaction):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You need administrator permissions!", ephemeral=True)
                return
            
            # Get statistics
            cursor = self.db.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp > datetime('now', '-24 hours')")
            recent_messages = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM security_events WHERE timestamp > datetime('now', '-24 hours')")
            recent_events = cursor.fetchone()[0]
            
            embed = discord.Embed(title="🛡️ Prot7 Security Status", color=0x00ff00)
            embed.add_field(name="📊 24h Activity", value=f"Messages: {recent_messages}\nEvents: {recent_events}", inline=True)
            embed.add_field(name="🔧 Active Modules", value="\n".join([f"✅ {k}" for k, v in self.config['modules'].items() if v]), inline=True)
            embed.add_field(name="🚫 Blocked Words", value=f"{len(self.config.get('blocked_words', []))}", inline=True)
            
            await interaction.response.send_message(embed=embed)
        
        @self.bot.tree.command(name="ban", description="Ban a user from the server")
        @app_commands.describe(
            user="The user to ban",
            reason="Reason for the ban",
            delete_messages="Delete the user's messages (in days, 0-7)"
        )
        async def ban_command(
            interaction: discord.Interaction, 
            user: discord.User, 
            reason: str = "No reason provided",
            delete_messages: int = 0
        ):
            # Check permissions
            if not interaction.user.guild_permissions.ban_members:
                await interaction.response.send_message("❌ You don't have permission to ban members", ephemeral=True)
                return
                
            # Validate delete_messages
            if delete_messages < 0 or delete_messages > 7:
                await interaction.response.send_message("❌ delete_messages must be between 0 and 7 days", ephemeral=True)
                return
            
            try:
                # First inform the user
                try:
                    embed = discord.Embed(
                        title="⚠️ You have been banned",
                        description=f"You have been banned from {interaction.guild.name}",
                        color=0xff0000
                    )
                    embed.add_field(name="Reason", value=reason)
                    embed.add_field(name="Moderator", value=interaction.user.name)
                    await user.send(embed=embed)
                except:
                    pass  # User might have DMs closed
                
                # Ban the user
                await interaction.guild.ban(
                    user, 
                    reason=f"Banned by {interaction.user}: {reason}",
                    delete_message_days=delete_messages
                )
                
                # Log the ban
                self.log_security_event(
                    "member_banned", 
                    user.id, 
                    f"User banned by {interaction.user.name}: {reason}", 
                    "high"
                )
                
                # Send confirmation
                embed = discord.Embed(
                    title="✅ User Banned", 
                    description=f"{user.mention} has been banned",
                    color=0x00ff00
                )
                embed.add_field(name="User", value=f"{user.name} ({user.id})")
                embed.add_field(name="Reason", value=reason)
                embed.add_field(name="Moderator", value=interaction.user.mention)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to ban user: {e}", ephemeral=True)
        
        @self.bot.tree.command(name="kick", description="Kick a user from the server")
        @app_commands.describe(
            user="The user to kick",
            reason="Reason for the kick"
        )
        async def kick_command(
            interaction: discord.Interaction, 
            user: discord.Member, 
            reason: str = "No reason provided"
        ):
            # Check permissions
            if not interaction.user.guild_permissions.kick_members:
                await interaction.response.send_message("❌ You don't have permission to kick members", ephemeral=True)
                return
            
            try:
                # First inform the user
                try:
                    embed = discord.Embed(
                        title="⚠️ You have been kicked",
                        description=f"You have been kicked from {interaction.guild.name}",
                        color=0xff9900
                    )
                    embed.add_field(name="Reason", value=reason)
                    embed.add_field(name="Moderator", value=interaction.user.name)
                    await user.send(embed=embed)
                except:
                    pass  # User might have DMs closed
                
                # Kick the user
                await user.kick(reason=f"Kicked by {interaction.user}: {reason}")
                
                # Log the kick
                self.log_security_event(
                    "member_kicked", 
                    user.id, 
                    f"User kicked by {interaction.user.name}: {reason}", 
                    "medium"
                )
                
                # Send confirmation
                embed = discord.Embed(
                    title="✅ User Kicked", 
                    description=f"{user.mention} has been kicked",
                    color=0x00ff00
                )
                embed.add_field(name="User", value=f"{user.name} ({user.id})")
                embed.add_field(name="Reason", value=reason)
                embed.add_field(name="Moderator", value=interaction.user.mention)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to kick user: {e}", ephemeral=True)
        
        @self.bot.tree.command(name="setup", description="Set up Prot7 Security Bot on your server")
        async def setup_command(interaction: discord.Interaction):
            # Check if user is server owner or administrator
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You need administrator permissions to set up the bot", ephemeral=True)
                return
            
            await interaction.response.send_message("🔄 Setting up Prot7 Security Bot...", ephemeral=True)
            
            try:
                guild = interaction.guild
                
                # 1. Create log channels if they don't exist
                security_logs = discord.utils.get(guild.channels, name="security-logs")
                if not security_logs:
                    security_logs = await guild.create_text_channel("security-logs")
                    await security_logs.set_permissions(guild.default_role, read_messages=False)
                
                mod_logs = discord.utils.get(guild.channels, name="mod-logs")
                if not mod_logs:
                    mod_logs = await guild.create_text_channel("mod-logs")
                    await mod_logs.set_permissions(guild.default_role, read_messages=False)
                
                # 2. Create roles if they don't exist
                admin_role = discord.utils.get(guild.roles, name="Prot7 Admin")
                if not admin_role:
                    admin_role = await guild.create_role(
                        name="Prot7 Admin",
                        color=discord.Color.red(),
                        permissions=discord.Permissions(administrator=True),
                        hoist=True,
                        mentionable=True
                    )
                
                mod_role = discord.utils.get(guild.roles, name="Prot7 Moderator")
                if not mod_role:
                    mod_role = await guild.create_role(
                        name="Prot7 Moderator",
                        color=discord.Color.blue(),
                        permissions=discord.Permissions(
                            kick_members=True,
                            ban_members=True,
                            manage_messages=True,
                            mute_members=True,
                            deafen_members=True,
                            move_members=True
                        ),
                        hoist=True,
                        mentionable=True
                    )
                
                # 3. Update configuration
                with self.config_lock:
                    self.config["log_channel"] = str(security_logs.id)
                    self.config["mod_log_channel"] = str(mod_logs.id)
                    self.config["admin_roles"] = [str(admin_role.id)]
                    self.config["mod_roles"] = [str(mod_role.id)]
                    
                    with open('config.json', 'w') as f:
                        json.dump(self.config, f, indent=4)
                
                # 4. Send success message with information
                setup_embed = discord.Embed(
                    title="✅ Prot7 Setup Complete",
                    description="The bot has been set up successfully!",
                    color=0x00ff00
                )
                setup_embed.add_field(
                    name="Channels Created",
                    value=f"Security Logs: {security_logs.mention}\nMod Logs: {mod_logs.mention}",
                    inline=False
                )
                setup_embed.add_field(
                    name="Roles Created",
                    value=f"Admin: {admin_role.mention}\nModerator: {mod_role.mention}",
                    inline=False
                )
                setup_embed.add_field(
                    name="Next Steps",
                    value="1. Assign the roles to your staff members\n2. Configure additional settings using the bot admin panel",
                    inline=False
                )
                
                await interaction.edit_original_response(content="", embed=setup_embed)
                
                # Log the setup
                self.log_security_event(
                    "bot_setup", 
                    interaction.user.id, 
                    f"Bot setup completed by {interaction.user.name}", 
                    "low"
                )
                
            except Exception as e:
                logging.error(f"Setup error: {e}")
                await interaction.edit_original_response(content=f"❌ Setup failed: {e}")
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            global bot_running
            logging.info(f"Received signal {sig}, shutting down gracefully...")
            bot_running = False
            shutdown_event.set()
            # Close database connection
            if self.db:
                self.db.close()
            # Close discord connection
            asyncio.create_task(self.bot.close())
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self):
        """Run the bot"""
        try:
            if not self.token:
                print("ERROR: Discord token not set in prot7.env file")
                logging.error("Discord token not set in prot7.env file")
                return
            
            print("Starting bot with token from prot7.env...")
            logging.info("Starting bot with token from prot7.env")
            
            # Start the bot
            self.bot.run(self.token, reconnect=True)
            
        except Exception as e:
            error_msg = f"Bot startup error: {e}"
            logging.error(error_msg)
            print(f"ERROR: {error_msg}")
        finally:
            # Close database connection
            if hasattr(self, 'db') and self.db:
                self.db.close()
            logging.info("Bot shutdown complete")
            print("Bot shutdown complete")

if __name__ == "__main__":
    try:
        bot = Prot7Bot()
        bot.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)
