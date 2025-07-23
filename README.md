<div align="center">

# PROT7 Discord Security Bot

<img src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/prot7-removebg-preview-77AKHnP0yPUTGVf11KDii74Z41z9Ab.png" alt="PROT7 Logo" width="200" height="200">

### Advanced Discord Security & Moderation System

[![Python](https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0+-5865f2?style=for-the-badge&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003b57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-00d4aa?style=for-the-badge)](LICENSE)

**Protect your Discord server with enterprise-grade security features**

[Quick Start](#quick-start) • [Features](#features) • [Installation](#installation) • [Documentation](#documentation)

---

</div>

## Overview

PROT7 is a comprehensive Discord security bot designed to protect servers from spam, raids, and malicious activities. Built with Python and featuring an advanced admin control panel, PROT7 provides real-time threat detection, automated moderation, and detailed security analytics.

<details>
<summary><strong>Key Highlights</strong></summary>

- **Real-time Protection**: Advanced anti-spam and raid detection
- **Automated Moderation**: Smart content filtering and user management  
- **Admin Control Panel**: Comprehensive command-line management interface
- **Database Analytics**: SQLite-powered logging and statistics
- **Slash Commands**: Modern Discord interface with intuitive commands
- **Hot Configuration**: Live config reloading without restarts

</details>

---

## Quick Start

<details>
<summary><strong>Prerequisites</strong></summary>

### System Requirements
- **OS**: Debian 11+ / Ubuntu 20.04+ (recommended)
- **Python**: 3.8 or higher
- **Memory**: 512MB+ RAM available
- **Storage**: 1GB+ free disk space
- **Network**: Stable internet connection

### Required Packages
```bash
pip3 install discord.py asyncio sqlite3
```

</details>

<details>
<summary><strong>Installation Steps</strong></summary>

### 1. File Setup
Upload all files to your server root directory:
- `prot7.py` (main bot application)
- `prot7adm.py` (admin control panel)
- `prot7.env` (environment configuration)

### 2. Configure Bot Token
Edit `prot7.env` with your Discord bot token:
```env
DISCORD_TOKEN=your_actual_bot_token_here
```

### 3. Set Permissions
```bash
chmod +x prot7.py prot7adm.py
chmod 600 prot7.env
```

### 4. Start the Bot
```bash
# Method 1: Direct execution
python3 prot7.py

# Method 2: Using admin panel
python3 prot7adm.py
```

</details>

---

## Features

<details>
<summary><strong>Security Features</strong></summary>

### Anti-Spam Protection
- **Smart Detection**: AI-powered spam pattern recognition
- **Progressive Punishment**: Escalating consequences for repeat offenders
- **Rate Limiting**: Message frequency and content analysis
- **Mention Protection**: Prevents mass mention abuse

### Raid Protection
- **Join Rate Monitoring**: Detects suspicious member influx
- **Account Age Verification**: Filters new/suspicious accounts
- **Automatic Response**: Real-time threat mitigation
- **Alert System**: Instant notifications for security events

### Content Moderation
- **Word Filtering**: Customizable blocked word lists
- **Message Analysis**: Advanced content scanning
- **Auto-Deletion**: Instant removal of violating content
- **User Notifications**: Automated warning system

</details>

<details>
<summary><strong>Moderation Tools</strong></summary>

### Slash Commands
- `/security_status` - Real-time security dashboard
- `/ban <user> [reason]` - Advanced user banning with logging
- `/kick <user> [reason]` - User removal with audit trail
- `/setup` - Automated server configuration

### Traditional Commands
- `!p7 status` - Bot status and statistics
- `!p7 lockdown [channel]` - Emergency channel lockdown
- `!p7 unlock [channel]` - Channel access restoration
- `!p7 reload` - Hot configuration reload

### Advanced Features
- **Timeout Management**: Temporary user restrictions
- **Bulk Actions**: Mass message and user management
- **Role Integration**: Permission-based command access
- **Audit Logging**: Comprehensive action tracking

</details>

<details>
<summary><strong>Admin Control Panel</strong></summary>

### Dashboard Features
- **Real-time Monitoring**: Live bot status and metrics
- **Process Management**: Start, stop, restart bot operations
- **Resource Monitoring**: CPU, memory, and performance stats
- **Log Viewing**: Real-time log analysis and filtering

### Data Management
- **Security Logs**: Browse and export security events
- **Message History**: Search and analyze user messages
- **User Tracking**: Comprehensive user activity logs
- **Statistics Export**: CSV export for external analysis

### Configuration Management
- **Module Control**: Enable/disable bot features
- **Word Lists**: Manage blocked content filters
- **Channel Setup**: Configure logging and alert channels
- **Role Management**: Set up admin and moderator roles

### Maintenance Tools
- **Database Cleanup**: Automated data optimization
- **Log Rotation**: Automatic log file management
- **Backup Systems**: Data export and archival
- **Performance Tuning**: System optimization tools

</details>

---

## Installation

<details>
<summary><strong>Server Setup</strong></summary>

### Manual Installation
1. **Create Bot Directory**
   ```bash
   mkdir /opt/prot7
   cd /opt/prot7
   ```

2. **Upload Files**
   - Transfer all bot files to `/opt/prot7/`
   - Ensure proper file permissions

3. **Install Dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

### Systemd Service (Recommended)
Create service file:
```bash
sudo nano /etc/systemd/system/prot7.service
```

Service configuration:
```ini
[Unit]
Description=PROT7 Discord Security Bot
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=10
User=prot7
WorkingDirectory=/opt/prot7
ExecStart=/usr/bin/python3 /opt/prot7/prot7.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable prot7.service
sudo systemctl start prot7.service
sudo systemctl status prot7.service
```

</details>

<details>
<summary><strong>Discord Configuration</strong></summary>

### Bot Permissions
Required Discord permissions:
- **Text Permissions**: Send Messages, Manage Messages, Read Message History
- **Moderation**: Kick Members, Ban Members, Timeout Members
- **Management**: Manage Channels, Manage Roles
- **Advanced**: Use Slash Commands, Embed Links

### Initial Setup
1. **Run Setup Command**
   ```
   /setup
   ```
   This automatically creates:
   - Security log channels
   - Moderation log channels  
   - Admin and moderator roles
   - Basic permissions structure

2. **Assign Roles**
   - Give `Prot7 Admin` role to server administrators
   - Give `Prot7 Moderator` role to trusted moderators

3. **Configure Channels**
   - Set up dedicated security logging channels
   - Configure alert notification channels
   - Adjust channel permissions as needed

</details>

---

## Documentation

<details>
<summary><strong>Configuration Reference</strong></summary>

### Bot Configuration (`config.json`)
```json
{
    "prefix": "!p7",
    "admin_roles": ["role_id_1", "role_id_2"],
    "mod_roles": ["role_id_3", "role_id_4"],
    "log_channel": "channel_id",
    "mod_log_channel": "channel_id",
    "security_alert_channel": "channel_id",
    "blocked_words": ["spam", "scam", "phishing"],
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

### Environment Variables (`prot7.env`)
```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here

# Optional: Database Configuration
DATABASE_PATH=prot7.db

# Optional: Logging Configuration  
LOG_LEVEL=INFO
LOG_FILE=prot7.log
```

</details>

<details>
<summary><strong>Database Schema</strong></summary>

### Core Tables
- **messages**: User message history and content analysis
- **security_events**: Security incidents with severity levels
- **users**: User profiles and behavioral tracking
- **advanced_audit**: Detailed audit trails for all actions
- **server_stats**: Server analytics and growth metrics
- **moderation_actions**: Complete moderation history

### Data Retention
- **Messages**: 90 days (configurable)
- **Security Events**: 1 year (configurable)
- **Audit Logs**: Permanent (with cleanup tools)
- **Statistics**: Permanent (aggregated monthly)

</details>

<details>
<summary><strong>Monitoring & Analytics</strong></summary>

### Log Files
- `prot7.log` - Main application logs
- `prot7_bot.log` - Bot process output
- `security.log` - Security event details
- `admin.log` - Admin panel activity

### Metrics Dashboard
Access via admin panel:
```bash
python3 prot7adm.py
# Select: System Status & Statistics
```

Key metrics include:
- **Security Events**: Real-time threat detection
- **User Activity**: Message and interaction patterns
- **Server Health**: Performance and resource usage
- **Moderation Stats**: Action frequency and effectiveness

</details>

---

## Troubleshooting

<details>
<summary><strong>Common Issues</strong></summary>

### Bot Won't Start
**Symptoms**: Bot fails to connect or crashes on startup
**Solutions**:
- Verify Discord token in `prot7.env`
- Check Python version: `python3 --version`
- Install missing dependencies: `pip3 install -r requirements.txt`
- Review logs: `tail -f prot7.log`

### Permission Errors
**Symptoms**: Commands fail or features don't work
**Solutions**:
- Ensure bot has required Discord permissions
- Check bot role hierarchy (must be above moderated roles)
- Verify file permissions: `ls -la prot7*`
- Review Discord audit log for permission issues

### Database Issues
**Symptoms**: Data not saving or corruption errors
**Solutions**:
- Check disk space: `df -h`
- Verify write permissions in bot directory
- Run database maintenance via admin panel
- Restore from backup if available

### Performance Issues
**Symptoms**: Slow response times or high resource usage
**Solutions**:
- Monitor system resources: `htop`
- Run database vacuum via admin panel
- Clear old logs and data
- Consider server upgrade if needed

</details>

<details>
<summary><strong>Maintenance</strong></summary>

### Regular Maintenance Tasks
- **Weekly**: Review security logs and statistics
- **Monthly**: Clean up old database records
- **Quarterly**: Update bot and dependencies
- **As Needed**: Backup configuration and data

### Admin Panel Maintenance
```bash
python3 prot7adm.py
# Navigate to: Maintenance Tools
```

Available tools:
- Database cleanup and optimization
- Log file management and rotation
- Data export and backup
- Performance monitoring and tuning

</details>

---

<div align="center">

## Support & Contributing

### Getting Help
- Check the [documentation](#documentation) first
- [Report bugs](https://github.com/yourusername/prot7/issues) on GitHub
- Join our [Discord community](https://discord.gg/your-invite) for support
- Contact: support@prot7.bot

### Contributing
We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

---

### License & Credits

**PROT7** is licensed under the [MIT License](LICENSE)

Created by the PROT7 Team

*Protecting Discord communities worldwide*

---

**Security Notice**: Keep your Discord bot token secure and never share it publicly. Regularly monitor your security logs and update the bot to ensure optimal protection.

</div>
