# PROT7 Discord Security Bot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0+-blue.svg)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained-Yes-green.svg)](https://github.com/yourusername/prot7)

A comprehensive Discord security bot designed to protect servers from spam, raids, and malicious activities. PROT7 features advanced anti-spam detection, automated moderation, user tracking, and a powerful admin control panel for server management.

## Features

### Core Security Features
- **Anti-Spam Protection**: Intelligent spam detection with progressive punishment system
- **Raid Protection**: Automatic detection and mitigation of server raids
- **Auto-Moderation**: Configurable word filtering and content moderation
- **User Tracking**: Comprehensive logging of user activities and message history
- **Channel Guard**: Advanced channel protection and lockdown capabilities
- **Advanced Audit Logging**: Detailed audit trails for all moderation actions

### Moderation Tools
- **Slash Commands**: Modern Discord slash command interface
- **Ban/Kick System**: Advanced user management with reason tracking
- **Timeout Management**: Temporary user restrictions
- **Channel Lockdown**: Emergency channel control features
- **Message Management**: Bulk message deletion and content filtering

### Administration Features
- **Real-time Monitoring**: Live security event tracking
- **Database Management**: SQLite-based data storage with cleanup tools
- **Configuration Management**: Hot-reloadable configuration system
- **Export Capabilities**: Data export for security logs and user data
- **Server Statistics**: Comprehensive server analytics and reporting

## Installation

### Prerequisites

- **Operating System**: Debian 11+ or Ubuntu 20.04+ (recommended)
- **Python**: Version 3.8 or higher
- **Discord Bot Token**: From Discord Developer Portal
- **Server Access**: SSH access with sudo privileges

### Required Python Packages

```bash
pip3 install discord.py sqlite3 asyncio
```

### Server Setup

1. **Clone or Upload Files**
   
   Upload all files to your server's root directory. Ensure the following files are present:
   - `prot7.py` (main bot file)
   - `prot7adm.py` (admin control panel)
   - `prot7.env` (environment configuration)

2. **Configure Bot Token**
   
   Edit the `prot7.env` file and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_actual_bot_token_here
   ```

3. **Set File Permissions**
   
   ```bash
   chmod +x prot7.py
   chmod +x prot7adm.py
   chmod 600 prot7.env
   ```

4. **Install as System Service (Optional)**
   
   Create a systemd service file for automatic startup:
   ```bash
   sudo nano /etc/systemd/system/prot7.service
   ```
   
   Add the following content:
   ```ini
   [Unit]
   Description=PROT7 Discord Security Bot
   After=network.target
   
   [Service]
   Type=simple
   User=your_username
   WorkingDirectory=/path/to/prot7
   ExecStart=/usr/bin/python3 /path/to/prot7/prot7.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable and start the service:
   ```bash
   sudo systemctl enable prot7.service
   sudo systemctl start prot7.service
   ```

## Usage

### Starting the Bot

#### Method 1: Direct Execution
```bash
python3 prot7.py
```

#### Method 2: Using Admin Panel
```bash
python3 prot7adm.py
```
Select option 1 (Bot Control) and then option 1 (Start Bot)

### Admin Control Panel

The admin control panel (`prot7adm.py`) provides comprehensive bot management:

```bash
python3 prot7adm.py
```

#### Available Functions:
- **Bot Control**: Start, stop, restart, and monitor bot status
- **System Status**: View detailed bot statistics and performance metrics
- **Security Logs**: Browse and export security event logs
- **Message Logs**: Search and analyze message history
- **User Management**: View user data and moderation history
- **Module Configuration**: Enable/disable bot features
- **Blocked Words**: Manage content filtering lists
- **Bot Configuration**: Update bot settings and channels
- **Data Export**: Export logs and statistics to CSV
- **Advanced Audit**: View detailed audit trails
- **Maintenance Tools**: Database cleanup and optimization

### Discord Setup

1. **Initial Bot Setup**
   
   Use the `/setup` slash command in your Discord server to automatically:
   - Create security and moderation log channels
   - Set up admin and moderator roles
   - Configure basic bot permissions

2. **Available Commands**
   
   **Slash Commands:**
   - `/security_status` - View bot security status
   - `/ban <user> [reason]` - Ban a user from the server
   - `/kick <user> [reason]` - Kick a user from the server
   - `/setup` - Initial bot configuration
   
   **Prefix Commands:**
   - `!p7 status` - Show bot status
   - `!p7 lockdown [channel]` - Lock down a channel
   - `!p7 unlock [channel]` - Unlock a channel
   - `!p7 reload` - Reload bot configuration

## Configuration

### Bot Configuration (`config.json`)

The bot automatically creates a configuration file with the following structure:

```json
{
    "prefix": "!p7",
    "admin_roles": [],
    "mod_roles": [],
    "log_channel": null,
    "mod_log_channel": null,
    "security_alert_channel": null,
    "blocked_words": ["spam", "badword"],
    "modules": {
        "anti_spam": true,
        "auto_mod": true,
        "channel_guard": true,
        "user_tracking": true,
        "advanced_audit": true,
        "raid_protection": true
    },
    "security": {
        "min_account_age_days": 7,
        "spam_threshold": 8,
        "max_mentions": 5,
        "mod_commands_require_reason": true,
        "dm_on_moderation": true,
        "auto_timeout_spam": true
    }
}
```

### Environment Configuration (`prot7.env`)

```
DISCORD_TOKEN=your_discord_bot_token_here
```

## Database Schema

PROT7 uses SQLite for data storage with the following tables:

- **messages**: User message history and content
- **security_events**: Security incidents and alerts
- **users**: User information and tracking data
- **advanced_audit**: Detailed audit logs for all actions
- **server_stats**: Server statistics and analytics
- **moderation_actions**: Moderation history and actions

## Security Features

### Anti-Spam System
- Message frequency analysis
- Repeated content detection
- Mention spam prevention
- Progressive punishment system
- Automatic timeout for repeat offenders

### Raid Protection
- New member join rate monitoring
- Account age verification
- Automatic suspicious account removal
- Real-time threat assessment

### Content Moderation
- Configurable word filtering
- Message content analysis
- Automatic message deletion
- User notification system

## Monitoring and Logging

### Log Files
- `prot7.log` - Main bot activity log
- `prot7_bot.log` - Bot process output log

### Database Logs
- Security events with severity levels
- User activity tracking
- Moderation action history
- Server statistics over time

## Troubleshooting

### Common Issues

1. **Bot Won't Start**
   - Verify Discord token in `prot7.env`
   - Check Python version (3.8+ required)
   - Ensure all dependencies are installed

2. **Permission Errors**
   - Verify bot has necessary Discord permissions
   - Check file permissions on server
   - Ensure bot role is above moderated roles

3. **Database Issues**
   - Check disk space availability
   - Verify write permissions in bot directory
   - Use admin panel maintenance tools for cleanup

### Log Analysis

Use the admin panel to view detailed logs:
```bash
python3 prot7adm.py
# Select option 2 (System Status) for overview
# Select option 3 (Security Logs) for detailed events
```

## Performance Optimization

### Recommended Server Specifications
- **CPU**: 1+ cores
- **RAM**: 512MB+ available
- **Storage**: 1GB+ free space
- **Network**: Stable internet connection

### Database Maintenance
- Regular database vacuum operations
- Periodic old data cleanup
- Log file rotation
- Statistics monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review log files for error details

## Changelog

### Version 1.5.7
- Enhanced admin control panel
- Improved database management
- Advanced audit logging
- Better error handling
- Performance optimizations

---

**Note**: Always keep your Discord bot token secure and never share it publicly. Regularly update the bot and monitor security logs for any suspicious activities.
