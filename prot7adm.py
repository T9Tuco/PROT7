#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Prot7 Admin Control Panel - Enhanced Edition
# Created: 2025-07-23 16:47:00
# Author: T9Tuco

import sqlite3
import json
import argparse
import sys
from datetime import datetime, timedelta
import os
import subprocess
import signal
import time
import threading
import csv
import io
import re

# Color codes for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Sichere Eingabefunktion gegen EOF-Fehler
def safe_input(prompt):
    try:
        return input(prompt)
    except EOFError:
        print("\nEOF-Fehler bei Eingabe. Verwende leere Eingabe.")
        return ""
    except KeyboardInterrupt:
        print("\nEingabe abgebrochen.")
        return ""

class BotController:
    def __init__(self):
        self.bot_pid_file = 'prot7_bot.pid'
        self.bot_script = 'prot7.py'  # Name des Bot-Scripts
        self.log_file = 'prot7_bot.log'
        self.env_file = 'prot7.env'
        
        # Prüfe, ob die Umgebungsvariablendatei existiert
        self.check_env_file()

    def check_env_file(self):
        """Prüft, ob die .env Datei existiert und einen Token enthält"""
        if not os.path.exists(self.env_file):
            print(f"Erstelle {self.env_file}...")
            with open(self.env_file, 'w') as f:
                f.write("# Prot7 Discord Security Bot Configuration\n")
                f.write("DISCORD_TOKEN=\n")
        
        # Prüfe, ob ein Token eingetragen ist
        token_set = False
        with open(self.env_file, 'r') as f:
            for line in f:
                if line.startswith('DISCORD_TOKEN=') and '=' in line:
                    token_value = line.split('=', 1)[1].strip()
                    if token_value and token_value != "YOUR_DISCORD_TOKEN_HERE":
                        token_set = True
                        break
        
        if not token_set:
            print(f"{Colors.YELLOW}Warnung: Kein Discord-Token in {self.env_file} gefunden.{Colors.ENDC}")
            print(f"{Colors.YELLOW}Bitte trage deinen Token in die Datei ein.{Colors.ENDC}")

    def start_bot(self):
        """Start the Discord bot in persistent mode (survives SSH disconnect)"""
        if self.is_bot_running():
            return False, "Bot is already running"
        
        # Prüfe, ob ein Token in der Env-Datei steht
        token_set = False
        with open(self.env_file, 'r') as f:
            for line in f:
                if line.startswith('DISCORD_TOKEN=') and '=' in line:
                    token_value = line.split('=', 1)[1].strip()
                    if token_value and token_value != "YOUR_DISCORD_TOKEN_HERE":
                        token_set = True
                        break
        
        if not token_set:
            return False, "Error: No Discord token set in prot7.env file"
        
        try:
            # Direkter nohup-Befehl ohne subprocess.Popen
            nohup_cmd = f"nohup python3 {self.bot_script} > {self.log_file} 2>&1 & echo $!"
            
            # Führt den Befehl aus und fängt die PID
            pid = subprocess.check_output(nohup_cmd, shell=True).decode().strip()
            
            # Speichert die PID in die Datei
            with open(self.bot_pid_file, 'w') as f:
                f.write(pid)
            
            # Überprüfen, ob der Prozess tatsächlich läuft
            time.sleep(2)
            if not self.is_bot_running():
                return False, "Bot started but failed to stay running. Check logs."
                
            return True, f"Bot started successfully (PID: {pid})"
        except Exception as e:
            return False, f"Failed to start bot: {e}"

    def stop_bot(self):
        """Stop the Discord bot (kill process by PID)"""
        if not self.is_bot_running():
            return False, "Bot is not running"
        try:
            with open(self.bot_pid_file, 'r') as f:
                pid = f.read().strip()
            
            # Beendet den Prozess
            os.system(f"kill {pid}")
            
            # Wartet kurz und prüft, ob der Prozess beendet wurde
            time.sleep(2)
            if self.is_bot_running():
                # Erzwungenes Beenden, falls nötig
                os.system(f"kill -9 {pid}")
                time.sleep(1)
            
            # Entfernt die PID-Datei
            if os.path.exists(self.bot_pid_file):
                os.remove(self.bot_pid_file)
                
            return True, "Bot stopped successfully"
        except Exception as e:
            return False, f"Failed to stop bot: {e}"

    def restart_bot(self):
        """Restart the Discord bot"""
        stop_success, stop_msg = self.stop_bot()
        if not stop_success and "not running" not in stop_msg:
            return False, f"Failed to stop bot: {stop_msg}"
        
        # Wartet kurz zwischen Stop und Start
        time.sleep(3)
        
        return self.start_bot()

    def is_bot_running(self):
        """Check if bot is running by PID file and process existence"""
        if not os.path.exists(self.bot_pid_file):
            return False
        try:
            with open(self.bot_pid_file, 'r') as f:
                pid = f.read().strip()
            
            # Prüft, ob der Prozess existiert
            return os.system(f"ps -p {pid} > /dev/null") == 0
        except:
            if os.path.exists(self.bot_pid_file):
                os.remove(self.bot_pid_file)
            return False
    
    def get_bot_process_info(self):
        """Get information about the bot process"""
        if not self.is_bot_running():
            return None
        
        try:
            with open(self.bot_pid_file, 'r') as f:
                pid = f.read().strip()
            
            # Get process info
            process_info = {}
            
            # Get uptime and command
            ps_output = subprocess.check_output(f"ps -p {pid} -o pid,ppid,etime,cmd", shell=True).decode()
            lines = ps_output.strip().split('\n')
            if len(lines) > 1:
                # Parse PS output (headers are in first line)
                headers = lines[0].split()
                values = re.split(r'\s+', lines[1], maxsplit=len(headers)-1)
                
                for i, header in enumerate(headers):
                    if i < len(values):
                        process_info[header.lower()] = values[i]
            
            # Get memory usage
            mem_output = subprocess.check_output(f"ps -p {pid} -o rss", shell=True).decode()
            mem_lines = mem_output.strip().split('\n')
            if len(mem_lines) > 1:
                process_info['memory_kb'] = int(mem_lines[1].strip())
                process_info['memory_mb'] = round(process_info['memory_kb'] / 1024, 2)
            
            # Get CPU usage
            cpu_output = subprocess.check_output(f"ps -p {pid} -o %cpu", shell=True).decode()
            cpu_lines = cpu_output.strip().split('\n')
            if len(cpu_lines) > 1:
                process_info['cpu'] = cpu_lines[1].strip()
            
            return process_info
        except Exception as e:
            print(f"Error getting process info: {e}")
            return None

    def get_bot_status(self):
        """Get current bot status"""
        if self.is_bot_running():
            return "ONLINE", Colors.GREEN
        else:
            return "OFFLINE", Colors.RED
    
    def get_bot_activity(self):
        """Get the current bot activity from database"""
        try:
            conn = sqlite3.connect('prot7.db')
            cursor = conn.cursor()
            
            # Try to get bot status from database
            cursor.execute("SELECT status, details, timestamp FROM bot_status ORDER BY id DESC LIMIT 1")
            status_row = cursor.fetchone()
            
            if status_row:
                status, details, timestamp = status_row
                return status, details, timestamp
            
            return "Unknown", "No status recorded", None
        except Exception as e:
            print(f"Error getting bot activity: {e}")
            return "Unknown", "Database error", None
        finally:
            if conn:
                conn.close()

    def show_bot_logs(self):
        """Show bot logs"""
        log_files = ['prot7.log', 'prot7_bot.log']
        for log_file in log_files:
            if os.path.exists(log_file):
                print(f"{Colors.HEADER}Letzte Logs aus {log_file}:{Colors.ENDC}")
                print(f"{Colors.BLUE}{'-'*50}{Colors.ENDC}")
                # Zeigt die letzten 20 Zeilen der Logdatei
                os.system(f"tail -n 20 {log_file}")
                print()
        print(f"{Colors.YELLOW}Ende der Logs{Colors.ENDC}")

class Prot7Admin:
    def __init__(self):
        self.db_path = 'prot7.db'
        self.config_path = 'config.json'
        self.env_path = 'prot7.env'
        self.bot_controller = BotController()
        self.ensure_files_exist()
        self.ensure_database_tables()
    
    def ensure_files_exist(self):
        """Ensure database and config files exist"""
        if not os.path.exists(self.config_path):
            default_config = {
                "prefix": "!p7",
                "admin_roles": [],
                "mod_roles": [],
                "log_channel": None,
                "mod_log_channel": None,
                "security_alert_channel": None,
                "blocked_words": ["spam", "badword"],
                "modules": {
                    "anti_spam": True,
                    "auto_mod": True,
                    "channel_guard": True,
                    "user_tracking": True,
                    "advanced_audit": True,
                    "raid_protection": True
                },
                "security": {
                    "min_account_age_days": 7,
                    "spam_threshold": 8,
                    "max_mentions": 5,
                    "mod_commands_require_reason": True,
                    "dm_on_moderation": True,
                    "auto_timeout_spam": True
                }
            }
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created default config at {self.config_path}")
            
        # Stelle sicher, dass die .env-Datei existiert
        if not os.path.exists(self.env_path):
            with open(self.env_path, 'w') as f:
                f.write("# Prot7 Discord Security Bot Configuration\n")
                f.write("DISCORD_TOKEN=\n")
            print(f"{Colors.YELLOW}Created empty environment file at {self.env_path}")
            print(f"Please add your Discord token to this file.{Colors.ENDC}")
    
    def ensure_database_tables(self):
        """Ensure all required database tables exist"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Check if users table exists, if not create it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                joined_at TEXT,
                avatar_url TEXT,
                is_bot INTEGER DEFAULT 0,
                last_seen TEXT,
                notes TEXT
            )
            ''')
            print(f"{Colors.GREEN}Created users table{Colors.ENDC}")
        
        # Check if messages table exists, if not create it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                user_id TEXT,
                username TEXT,
                channel_id TEXT,
                guild_id TEXT,
                content TEXT,
                timestamp TEXT
            )
            ''')
            print(f"{Colors.GREEN}Created messages table{Colors.ENDC}")
        
        # Check if security_events table exists, if not create it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='security_events'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id TEXT,
                details TEXT,
                timestamp TEXT,
                severity TEXT
            )
            ''')
            print(f"{Colors.GREEN}Created security_events table{Colors.ENDC}")
        
        # Check if bot_status table exists, if not create it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_status'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE bot_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT,
                details TEXT,
                timestamp TEXT
            )
            ''')
            print(f"{Colors.GREEN}Created bot_status table{Colors.ENDC}")
        
        # Check if advanced_audit table exists, if not create it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='advanced_audit'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE advanced_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                guild_id TEXT,
                channel_id TEXT,
                user_id TEXT,
                target_id TEXT,
                details TEXT,
                timestamp TEXT
            )
            ''')
            print(f"{Colors.GREEN}Created advanced_audit table{Colors.ENDC}")

        # Check if server_stats table exists, if not create it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='server_stats'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE server_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                member_count INTEGER,
                online_count INTEGER,
                channel_count INTEGER,
                timestamp TEXT
            )
            ''')
            print(f"{Colors.GREEN}Created server_stats table{Colors.ENDC}")
        
        conn.commit()
        conn.close()
    
    def get_db_connection(self):
        """Get database connection"""
        try:
            return sqlite3.connect(self.db_path)
        except Exception as e:
            print(f"{Colors.RED}Database error: {e}{Colors.ENDC}")
            return None
    
    def load_config(self):
        """Load configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Colors.RED}Config error: {e}{Colors.ENDC}")
            return {"modules": {}, "blocked_words": [], "prefix": "!p7"}
    
    def save_config(self, config):
        """Save configuration and notify bot to reload config"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"{Colors.GREEN}Configuration saved successfully!{Colors.ENDC}")
            print(f"{Colors.YELLOW}Bot will reload config automatically within 1 minute.{Colors.ENDC}")
            print(f"{Colors.YELLOW}Use /reload_config in Discord for instant reload.{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Failed to save config: {e}{Colors.ENDC}")
    
    def update_env_token(self, token):
        """Update the token in the environment file"""
        try:
            if os.path.exists(self.env_path):
                # Lese aktuelle Datei
                with open(self.env_path, 'r') as f:
                    lines = f.readlines()
                
                # Aktualisiere oder füge den Token hinzu
                token_found = False
                for i, line in enumerate(lines):
                    if line.startswith('DISCORD_TOKEN='):
                        lines[i] = f"DISCORD_TOKEN={token}\n"
                        token_found = True
                        break
                
                if not token_found:
                    lines.append(f"DISCORD_TOKEN={token}\n")
                
                # Schreibe aktualisierte Datei
                with open(self.env_path, 'w') as f:
                    f.writelines(lines)
            else:
                # Erstelle neue Datei
                with open(self.env_path, 'w') as f:
                    f.write("# Prot7 Discord Security Bot Configuration\n")
                    f.write(f"DISCORD_TOKEN={token}\n")
            
            return True, "Token updated successfully"
        except Exception as e:
            return False, f"Failed to update token: {e}"
    
    def get_env_token(self):
        """Get the token from the environment file"""
        token = ""
        try:
            if os.path.exists(self.env_path):
                with open(self.env_path, 'r') as f:
                    for line in f:
                        if line.startswith('DISCORD_TOKEN='):
                            token = line.split('=', 1)[1].strip()
                            break
        except:
            pass
            
        # Für die Anzeige maskieren wir den Token
        if token and token != "YOUR_DISCORD_TOKEN_HERE" and token != "":
            masked_token = "*" * (len(token) - 4) + token[-4:] if len(token) > 4 else "*" * len(token)
            return masked_token
        return "Not set"
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def show_main_menu(self):
        """Display the main menu"""
        status, status_color = self.bot_controller.get_bot_status()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}              PROT7 ADMIN CONTROL PANEL{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}Bot Status: {status_color}{status}{Colors.ENDC}")
        
        # Show current bot activity if online
        if status == "ONLINE":
            try:
                activity_status, activity_details, _ = self.bot_controller.get_bot_activity()
                print(f"{Colors.BOLD}Bot Activity: {Colors.CYAN}{activity_status}{Colors.ENDC} - {activity_details}")
            except:
                pass
        
        print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
        print(f"{Colors.BOLD} 1.{Colors.ENDC} Bot Control (Start/Stop/Restart)")
        print(f"{Colors.BOLD} 2.{Colors.ENDC} System Status & Statistics")
        print(f"{Colors.BOLD} 3.{Colors.ENDC} Security Logs")
        print(f"{Colors.BOLD} 4.{Colors.ENDC} Message Logs")
        print(f"{Colors.BOLD} 5.{Colors.ENDC} User Management")
        print(f"{Colors.BOLD} 6.{Colors.ENDC} Module Configuration")
        print(f"{Colors.BOLD} 7.{Colors.ENDC} Blocked Words")
        print(f"{Colors.BOLD} 8.{Colors.ENDC} Bot Configuration")
        print(f"{Colors.BOLD} 9.{Colors.ENDC} Data Export")
        print(f"{Colors.BOLD}10.{Colors.ENDC} Advanced Audit Logs")
        print(f"{Colors.BOLD}11.{Colors.ENDC} Maintenance Tools")
        print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
        print(f"{Colors.BOLD} R.{Colors.ENDC} Refresh Status")
        print(f"{Colors.BOLD} 0.{Colors.ENDC} Exit")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
    
    def interactive_menu(self):
        """Main interactive menu"""
        while True:
            try:
                self.clear_screen()
                self.show_main_menu()
                choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
                
                if choice == '1':
                    self.bot_control_menu()
                elif choice == '2':
                    self.show_status_detailed()
                    safe_input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '3':
                    self.security_logs_menu()
                elif choice == '4':
                    self.message_logs_menu()
                elif choice == '5':
                    self.user_management_menu()
                elif choice == '6':
                    self.modules_submenu()
                elif choice == '7':
                    self.blocked_words_submenu()
                elif choice == '8':
                    self.config_submenu()
                elif choice == '9':
                    self.export_submenu()
                elif choice == '10':
                    self.advanced_audit_menu()
                elif choice == '11':
                    self.maintenance_submenu()
                elif choice.lower() in ['r', '0', 'q']:
                    if choice == '0' or choice.lower() == 'q':
                        print(f"\n{Colors.GREEN}Goodbye!{Colors.ENDC}")
                        break
                    continue  # Refresh
                else:
                    print(f"{Colors.RED}Invalid choice!{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.GREEN}Goodbye!{Colors.ENDC}")
                break
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def bot_control_menu(self):
        """Bot control menu (always persistent mode)"""
        while True:
            self.clear_screen()
            status, status_color = self.bot_controller.get_bot_status()
            print(f"{Colors.BLUE}{'='*50}{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.HEADER}         BOT CONTROL PANEL{Colors.ENDC}")
            print(f"{Colors.BLUE}{'='*50}{Colors.ENDC}")
            print(f"{Colors.BOLD}Current Status: {status_color}{status}{Colors.ENDC}")
            
            # Show current bot activity if online
            if status == "ONLINE":
                try:
                    activity_status, activity_details, timestamp = self.bot_controller.get_bot_activity()
                    print(f"{Colors.BOLD}Bot Activity: {Colors.CYAN}{activity_status}{Colors.ENDC}")
                    print(f"{Colors.BOLD}Details: {Colors.CYAN}{activity_details}{Colors.ENDC}")
                    
                    if timestamp:
                        timestamp_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f") if '.' in timestamp else datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        time_diff = datetime.now() - timestamp_dt
                        minutes = int(time_diff.total_seconds() / 60)
                        seconds = int(time_diff.total_seconds() % 60)
                        print(f"{Colors.BOLD}Since: {Colors.CYAN}{minutes}m {seconds}s ago{Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.RED}Error getting activity: {e}{Colors.ENDC}")
            
            # Prüfe, ob der Token gesetzt ist
            token_status = self.get_env_token()
            if token_status == "Not set":
                print(f"{Colors.RED}WARNING: Discord token is not set in prot7.env!{Colors.ENDC}")
                print(f"{Colors.RED}The bot cannot start without a valid token.{Colors.ENDC}")
            
            print(f"{Colors.BLUE}{'-'*50}{Colors.ENDC}")
            if status == "OFFLINE":
                print(f"{Colors.BOLD} 1.{Colors.ENDC} {Colors.GREEN}Start Bot (Persistent){Colors.ENDC}")
            else:
                print(f"{Colors.BOLD} 1.{Colors.ENDC} {Colors.RED}Stop Bot{Colors.ENDC}")
            print(f"{Colors.BOLD} 2.{Colors.ENDC} Restart Bot")
            print(f"{Colors.BOLD} 3.{Colors.ENDC} View Bot Logs")
            print(f"{Colors.BOLD} 4.{Colors.ENDC} Force Kill Bot")
            print(f"{Colors.BOLD} 5.{Colors.ENDC} Advanced Process Info")
            print(f"{Colors.BOLD} 0.{Colors.ENDC} Back to Main Menu")
            print(f"{Colors.BLUE}{'='*50}{Colors.ENDC}")
            choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
            if choice == '1':
                if status == "OFFLINE":
                    print(f"\n{Colors.YELLOW}Starting bot...{Colors.ENDC}")
                    success, message = self.bot_controller.start_bot()
                else:
                    print(f"\n{Colors.YELLOW}Stopping bot...{Colors.ENDC}")
                    success, message = self.bot_controller.stop_bot()
                color = Colors.GREEN if success else Colors.RED
                print(f"{color}{message}{Colors.ENDC}")
                if not success and status == "OFFLINE":
                    print(f"{Colors.YELLOW}Checking logs for errors...{Colors.ENDC}")
                    self.bot_controller.show_bot_logs()
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            elif choice == '2':
                print(f"\n{Colors.YELLOW}Restarting bot...{Colors.ENDC}")
                success, message = self.bot_controller.restart_bot()
                color = Colors.GREEN if success else Colors.RED
                print(f"{color}{message}{Colors.ENDC}")
                if not success:
                    print(f"{Colors.YELLOW}Checking logs for errors...{Colors.ENDC}")
                    self.bot_controller.show_bot_logs()
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            elif choice == '3':
                self.bot_controller.show_bot_logs()
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            elif choice == '4':
                confirm = safe_input(f"\n{Colors.RED}Force kill bot? (y/N): {Colors.ENDC}").strip().lower()
                if confirm == 'y':
                    # Alle Python-Prozesse mit prot7.py im Namen beenden
                    os.system("pkill -f 'python.*prot7.py'")
                    if os.path.exists(self.bot_controller.bot_pid_file):
                        os.remove(self.bot_controller.bot_pid_file)
                    print(f"{Colors.GREEN}Bot force killed{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            elif choice == '5':
                self.show_advanced_process_info()
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            elif choice == '0':
                break
    
    def show_advanced_process_info(self):
        """Show advanced process information"""
        if not self.bot_controller.is_bot_running():
            print(f"{Colors.RED}Bot is not running{Colors.ENDC}")
            return
            
        try:
            process_info = self.bot_controller.get_bot_process_info()
            if not process_info:
                print(f"{Colors.RED}Failed to get process information{Colors.ENDC}")
                return
                
            print(f"\n{Colors.HEADER}ADVANCED PROCESS INFORMATION{Colors.ENDC}")
            print(f"{Colors.BLUE}{'='*50}{Colors.ENDC}")
            
            print(f"{Colors.BOLD}PID:{Colors.ENDC} {Colors.GREEN}{process_info.get('pid', 'Unknown')}{Colors.ENDC}")
            print(f"{Colors.BOLD}Parent PID:{Colors.ENDC} {Colors.GREEN}{process_info.get('ppid', 'Unknown')}{Colors.ENDC}")
            print(f"{Colors.BOLD}Uptime:{Colors.ENDC} {Colors.GREEN}{process_info.get('etime', 'Unknown')}{Colors.ENDC}")
            print(f"{Colors.BOLD}Memory Usage:{Colors.ENDC} {Colors.GREEN}{process_info.get('memory_mb', 'Unknown')} MB{Colors.ENDC}")
            print(f"{Colors.BOLD}CPU Usage:{Colors.ENDC} {Colors.GREEN}{process_info.get('cpu', 'Unknown')}%{Colors.ENDC}")
            print(f"{Colors.BOLD}Command:{Colors.ENDC} {Colors.GREEN}{process_info.get('cmd', 'Unknown')}{Colors.ENDC}")
            
            # Show file handles
            print(f"\n{Colors.BOLD}Open Files:{Colors.ENDC}")
            try:
                with open(self.bot_controller.bot_pid_file, 'r') as f:
                    pid = f.read().strip()
                
                # Get list of open files (limited output)
                lsof_output = subprocess.check_output(f"lsof -p {pid} | head -n 10", shell=True).decode()
                print(f"{Colors.CYAN}{lsof_output}{Colors.ENDC}")
                
                if len(lsof_output.strip().split('\n')) >= 10:
                    print(f"{Colors.YELLOW}(Output truncated, showing first 10 entries){Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Failed to get open files: {e}{Colors.ENDC}")
            
            # Show network connections
            print(f"\n{Colors.BOLD}Network Connections:{Colors.ENDC}")
            try:
                with open(self.bot_controller.bot_pid_file, 'r') as f:
                    pid = f.read().strip()
                
                netstat_output = subprocess.check_output(f"netstat -tunapl | grep {pid} | head -n 10", shell=True, stderr=subprocess.DEVNULL).decode()
                if netstat_output.strip():
                    print(f"{Colors.CYAN}{netstat_output}{Colors.ENDC}")
                else:
                    print(f"{Colors.YELLOW}No active network connections found{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Failed to get network connections: {e}{Colors.ENDC}")
            
        except Exception as e:
            print(f"{Colors.RED}Error getting advanced process info: {e}{Colors.ENDC}")
    
    def show_status_detailed(self):
        """Show detailed status"""
        try:
            conn = self.get_db_connection()
            if conn:
                cursor = conn.cursor()
                
                # Get message count
                cursor.execute("SELECT COUNT(*) FROM messages")
                result = cursor.fetchone()
                msg_count = result[0] if result else 0
                
                # Get recent message count (24h)
                cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp > datetime('now', '-1 day')")
                recent_msg_count = cursor.fetchone()[0] if result else 0
                
                # Get security events count
                cursor.execute("SELECT COUNT(*) FROM security_events")
                events_count = cursor.fetchone()[0] if result else 0
                
                # Get high severity events count
                cursor.execute("SELECT COUNT(*) FROM security_events WHERE severity = 'high'")
                high_severity_count = cursor.fetchone()[0] if result else 0
                
                # Get servers count from stats if available
                try:
                    cursor.execute("SELECT COUNT(DISTINCT guild_id) FROM server_stats")
                    servers_count = cursor.fetchone()[0] if result else 0
                except:
                    servers_count = "N/A"
                
                # Get latest stats for members
                try:
                    cursor.execute("""
                        SELECT SUM(member_count) FROM server_stats 
                        WHERE timestamp = (SELECT MAX(timestamp) FROM server_stats)
                    """)
                    members_count = cursor.fetchone()[0] if result else 0
                except:
                    members_count = "N/A"
                
                conn.close()
            else:
                msg_count = recent_msg_count = events_count = high_severity_count = 0
                servers_count = members_count = "N/A"
            
            config = self.load_config()
            bot_status, status_color = self.bot_controller.get_bot_status()
            
            print(f"\n{Colors.HEADER}DETAILED SYSTEM STATUS{Colors.ENDC}")
            print(f"{Colors.BLUE}{'='*50}{Colors.ENDC}")
            print(f"{Colors.BOLD}Bot Status:{Colors.ENDC} {status_color}{bot_status}{Colors.ENDC}")
            
            # Show bot activity if running
            if bot_status == "ONLINE":
                try:
                    activity_status, activity_details, _ = self.bot_controller.get_bot_activity()
                    print(f"{Colors.BOLD}Bot Activity:{Colors.ENDC} {Colors.CYAN}{activity_status}{Colors.ENDC} - {activity_details}")
                except:
                    pass
            
            # Zeige Token-Status (maskiert)
            token_status = self.get_env_token()
            token_color = Colors.GREEN if token_status != "Not set" else Colors.RED
            print(f"{Colors.BOLD}Bot Token:{Colors.ENDC} {token_color}{token_status}{Colors.ENDC}")
            
            # Zeigt PID an, wenn der Bot läuft
            if bot_status == "ONLINE" and os.path.exists(self.bot_controller.bot_pid_file):
                with open(self.bot_controller.bot_pid_file, 'r') as f:
                    pid = f.read().strip()
                print(f"{Colors.BOLD}Bot PID:{Colors.ENDC} {Colors.CYAN}{pid}{Colors.ENDC}")
                
                # Show uptime
                process_info = self.bot_controller.get_bot_process_info()
                if process_info and 'etime' in process_info:
                    print(f"{Colors.BOLD}Uptime:{Colors.ENDC} {Colors.CYAN}{process_info['etime']}{Colors.ENDC}")
                
                # Zeigt Prozessinformationen an
                print(f"{Colors.BOLD}Process Info:{Colors.ENDC}")
                os.system(f"ps -p {pid} -o pid,ppid,cmd,etime")
            
            # Statistics
            print(f"\n{Colors.BOLD}Statistics:{Colors.ENDC}")
            print(f"{Colors.BOLD}Messages Logged:{Colors.ENDC} {Colors.GREEN}{msg_count:,}{Colors.ENDC} (Last 24h: {Colors.GREEN}{recent_msg_count:,}{Colors.ENDC})")
            print(f"{Colors.BOLD}Security Events:{Colors.ENDC} {Colors.GREEN}{events_count:,}{Colors.ENDC} (High Severity: {Colors.RED}{high_severity_count:,}{Colors.ENDC})")
            print(f"{Colors.BOLD}Servers:{Colors.ENDC} {Colors.GREEN}{servers_count}{Colors.ENDC}")
            print(f"{Colors.BOLD}Members:{Colors.ENDC} {Colors.GREEN}{members_count}{Colors.ENDC}")
            
            # Configuration
            print(f"\n{Colors.BOLD}Configuration:{Colors.ENDC}")
            print(f"{Colors.BOLD}Bot Prefix:{Colors.ENDC} {Colors.CYAN}{config.get('prefix', 'Unknown')}{Colors.ENDC}")
            print(f"{Colors.BOLD}Log Channel:{Colors.ENDC} {Colors.CYAN}{config.get('log_channel', 'None')}{Colors.ENDC}")
            print(f"{Colors.BOLD}Mod Log Channel:{Colors.ENDC} {Colors.CYAN}{config.get('mod_log_channel', 'None')}{Colors.ENDC}")
            print(f"{Colors.BOLD}Blocked Words:{Colors.ENDC} {Colors.CYAN}{len(config.get('blocked_words', []))}{Colors.ENDC}")
            
            # Active modules
            print(f"\n{Colors.BOLD}Active Modules:{Colors.ENDC}")
            modules = config.get('modules', {})
            for module, enabled in modules.items():
                status_color = Colors.GREEN if enabled else Colors.RED
                status_text = "ENABLED" if enabled else "DISABLED"
                print(f"  {Colors.BOLD}{module}:{Colors.ENDC} {status_color}{status_text}{Colors.ENDC}")
            
        except Exception as e:
            print(f"{Colors.RED}Error loading status: {e}{Colors.ENDC}")
    
    def security_logs_menu(self):
        """Security logs menu"""
        while True:
            try:
                self.clear_screen()
                
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.HEADER}              SECURITY LOGS{Colors.ENDC}")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                print(f"{Colors.BOLD} 1.{Colors.ENDC} View All Security Logs")
                print(f"{Colors.BOLD} 2.{Colors.ENDC} View High Severity Events")
                print(f"{Colors.BOLD} 3.{Colors.ENDC} View User-related Events")
                print(f"{Colors.BOLD} 4.{Colors.ENDC} View Channel-related Events")
                print(f"{Colors.BOLD} 5.{Colors.ENDC} View Security Events by Type")
                print(f"{Colors.BOLD} 6.{Colors.ENDC} View Recent Security Events (Last 24h)")
                print(f"{Colors.BOLD} 7.{Colors.ENDC} Export Security Logs")
                print(f"{Colors.BOLD} 0.{Colors.ENDC} Back to Main Menu")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
                
                if choice == '0':
                    break
                elif choice == '1':
                    self.view_security_logs()
                elif choice == '2':
                    self.view_security_logs(severity="high")
                elif choice == '3':
                    user_id = safe_input(f"Enter user ID: ").strip()
                    if user_id:
                        self.view_security_logs(user_id=user_id)
                    else:
                        print(f"{Colors.RED}Invalid user ID{Colors.ENDC}")
                        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '4':
                    self.view_security_logs(event_types=["channel_created", "channel_deleted", "channel_updated", "lockdown", "unlock"])
                elif choice == '5':
                    self.security_event_type_menu()
                elif choice == '6':
                    self.view_security_logs(time_range="24h")
                elif choice == '7':
                    self.export_security_logs()
                else:
                    print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def security_event_type_menu(self):
        """Menu to select security event type"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}           SECURITY EVENT TYPES{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        # Get available event types from database
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
            
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT event_type FROM security_events")
        event_types = cursor.fetchall()
        conn.close()
        
        if not event_types:
            print(f"{Colors.YELLOW}No security events found in database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
        
        for i, (event_type,) in enumerate(event_types, 1):
            print(f"{Colors.BOLD} {i}.{Colors.ENDC} {event_type}")
        
        print(f"{Colors.BOLD} 0.{Colors.ENDC} Back")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
        
        if choice == '0':
            return
            
        try:
            event_index = int(choice) - 1
            if 0 <= event_index < len(event_types):
                selected_event = event_types[event_index][0]
                self.view_security_logs(event_types=[selected_event])
            else:
                print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
        except ValueError:
            print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def view_security_logs(self, user_id=None, severity=None, event_types=None, time_range=None, limit=100):
        """View security logs with filters"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}              SECURITY LOGS{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        # Build filters for display
        filters = []
        if user_id:
            filters.append(f"User ID: {user_id}")
        if severity:
            filters.append(f"Severity: {severity}")
        if event_types:
            filters.append(f"Event Types: {', '.join(event_types)}")
        if time_range:
            filters.append(f"Time Range: Last {time_range}")
        
        if filters:
            print(f"{Colors.BOLD}Filters:{Colors.ENDC} {', '.join(filters)}")
            print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
        
        # Get logs from database
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
            
        try:
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT id, event_type, user_id, details, timestamp, severity FROM security_events WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            if event_types:
                placeholders = ", ".join(["?" for _ in event_types])
                query += f" AND event_type IN ({placeholders})"
                params.extend(event_types)
            
            if time_range == "24h":
                query += " AND timestamp > datetime('now', '-1 day')"
            elif time_range == "7d":
                query += " AND timestamp > datetime('now', '-7 days')"
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            if not logs:
                print(f"{Colors.YELLOW}No security logs found matching the criteria{Colors.ENDC}")
            else:
                # Display logs
                for log in logs:
                    log_id, event_type, user_id, details, timestamp, severity = log
                    
                    # Set color based on severity
                    if severity == "high":
                        severity_color = Colors.RED
                    elif severity == "medium":
                        severity_color = Colors.YELLOW
                    else:
                        severity_color = Colors.GREEN
                    
                    print(f"{Colors.BOLD}ID:{Colors.ENDC} {log_id}")
                    print(f"{Colors.BOLD}Type:{Colors.ENDC} {Colors.BLUE}{event_type}{Colors.ENDC}")
                    print(f"{Colors.BOLD}User ID:{Colors.ENDC} {user_id}")
                    print(f"{Colors.BOLD}Severity:{Colors.ENDC} {severity_color}{severity.upper()}{Colors.ENDC}")
                    print(f"{Colors.BOLD}Time:{Colors.ENDC} {timestamp}")
                    print(f"{Colors.BOLD}Details:{Colors.ENDC} {details}")
                    print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
                
                print(f"{Colors.GREEN}Found {len(logs)} security logs{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error retrieving security logs: {e}{Colors.ENDC}")
        finally:
            conn.close()
            
        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def export_security_logs(self):
        """Export security logs to CSV"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}           EXPORT SECURITY LOGS{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        # Get export parameters
        time_range = safe_input(f"Time range (all/24h/7d/30d): ").strip().lower()
        severity = safe_input(f"Severity (all/high/medium/low): ").strip().lower()
        
        if severity not in ["all", "high", "medium", "low"]:
            severity = "all"
        
        # Get export filename
        export_file = safe_input(f"Export filename (default: security_logs.csv): ").strip()
        if not export_file:
            export_file = "security_logs.csv"
        
        # Add .csv extension if not present
        if not export_file.endswith('.csv'):
            export_file += '.csv'
        
        # Get logs from database
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
            
        try:
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT id, event_type, user_id, details, timestamp, severity FROM security_events WHERE 1=1"
            params = []
            
            if severity != "all":
                query += " AND severity = ?"
                params.append(severity)
            
            if time_range == "24h":
                query += " AND timestamp > datetime('now', '-1 day')"
            elif time_range == "7d":
                query += " AND timestamp > datetime('now', '-7 days')"
            elif time_range == "30d":
                query += " AND timestamp > datetime('now', '-30 days')"
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            if not logs:
                print(f"{Colors.YELLOW}No security logs found matching the criteria{Colors.ENDC}")
            else:
                # Write to CSV
                with open(export_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['ID', 'Event Type', 'User ID', 'Details', 'Timestamp', 'Severity'])
                    
                    for log in logs:
                        writer.writerow(log)
                
                print(f"{Colors.GREEN}Successfully exported {len(logs)} logs to {export_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error exporting security logs: {e}{Colors.ENDC}")
        finally:
            conn.close()
            
        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def message_logs_menu(self):
        """Message logs menu"""
        while True:
            try:
                self.clear_screen()
                
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.HEADER}              MESSAGE LOGS{Colors.ENDC}")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                print(f"{Colors.BOLD} 1.{Colors.ENDC} View Recent Messages")
                print(f"{Colors.BOLD} 2.{Colors.ENDC} Search Messages by User")
                print(f"{Colors.BOLD} 3.{Colors.ENDC} Search Messages by Channel")
                print(f"{Colors.BOLD} 4.{Colors.ENDC} Search Messages by Content")
                print(f"{Colors.BOLD} 5.{Colors.ENDC} View Message Statistics")
                print(f"{Colors.BOLD} 6.{Colors.ENDC} Export Message Logs")
                print(f"{Colors.BOLD} 0.{Colors.ENDC} Back to Main Menu")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
                
                if choice == '0':
                    break
                elif choice == '1':
                    self.view_message_logs()
                elif choice == '2':
                    user_id = safe_input(f"Enter user ID: ").strip()
                    if user_id:
                        self.view_message_logs(user_id=user_id)
                    else:
                        print(f"{Colors.RED}Invalid user ID{Colors.ENDC}")
                        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '3':
                    channel_id = safe_input(f"Enter channel ID: ").strip()
                    if channel_id:
                        self.view_message_logs(channel_id=channel_id)
                    else:
                        print(f"{Colors.RED}Invalid channel ID{Colors.ENDC}")
                        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '4':
                    search_term = safe_input(f"Enter search term: ").strip()
                    if search_term:
                        self.view_message_logs(search_term=search_term)
                    else:
                        print(f"{Colors.RED}Invalid search term{Colors.ENDC}")
                        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '5':
                    self.view_message_statistics()
                elif choice == '6':
                    self.export_message_logs()
                else:
                    print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def view_message_logs(self, user_id=None, channel_id=None, search_term=None, limit=50):
        """View message logs with filters"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}              MESSAGE LOGS{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        # Build filters for display
        filters = []
        if user_id:
            filters.append(f"User ID: {user_id}")
        if channel_id:
            filters.append(f"Channel ID: {channel_id}")
        if search_term:
            filters.append(f"Search: \"{search_term}\"")
        
        if filters:
            print(f"{Colors.BOLD}Filters:{Colors.ENDC} {', '.join(filters)}")
            print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
        
        # Get logs from database
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
            
        try:
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT id, user_id, username, channel_id, guild_id, content, timestamp FROM messages WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if channel_id:
                query += " AND channel_id = ?"
                params.append(channel_id)
            
            if search_term:
                query += " AND content LIKE ?"
                params.append(f"%{search_term}%")
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            if not logs:
                print(f"{Colors.YELLOW}No message logs found matching the criteria{Colors.ENDC}")
            else:
                # Display logs
                for log in logs:
                    msg_id, user_id, username, channel_id, guild_id, content, timestamp = log
                    
                    print(f"{Colors.BOLD}ID:{Colors.ENDC} {msg_id}")
                    print(f"{Colors.BOLD}User:{Colors.ENDC} {Colors.CYAN}{username}{Colors.ENDC} ({user_id})")
                    print(f"{Colors.BOLD}Channel:{Colors.ENDC} {channel_id}")
                    print(f"{Colors.BOLD}Time:{Colors.ENDC} {timestamp}")
                    print(f"{Colors.BOLD}Content:{Colors.ENDC} {content}")
                    print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
                
                print(f"{Colors.GREEN}Found {len(logs)} messages{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error retrieving message logs: {e}{Colors.ENDC}")
        finally:
            conn.close()
            
        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def view_message_statistics(self):
        """View message statistics"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}           MESSAGE STATISTICS{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        # Get statistics from database
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
            
        try:
            cursor = conn.cursor()
            
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Messages in last 24 hours
            cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp > datetime('now', '-1 day')")
            messages_24h = cursor.fetchone()[0]
            
            # Messages in last 7 days
            cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp > datetime('now', '-7 days')")
            messages_7d = cursor.fetchone()[0]
            
            # Most active users
            cursor.execute("""
                SELECT user_id, username, COUNT(*) as msg_count
                FROM messages
                GROUP BY user_id
                ORDER BY msg_count DESC
                LIMIT 10
            """)
            active_users = cursor.fetchall()
            
            # Most active channels
            cursor.execute("""
                SELECT channel_id, COUNT(*) as msg_count
                FROM messages
                GROUP BY channel_id
                ORDER BY msg_count DESC
                LIMIT 10
            """)
            active_channels = cursor.fetchall()
            
            # Messages per day (last 7 days)
            cursor.execute("""
                SELECT date(timestamp) as day, COUNT(*) as msg_count
                FROM messages
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY day
                ORDER BY day
            """)
            messages_per_day = cursor.fetchall()
            
            # Display statistics
            print(f"{Colors.BOLD}Total Messages:{Colors.ENDC} {Colors.GREEN}{total_messages:,}{Colors.ENDC}")
            print(f"{Colors.BOLD}Messages (24h):{Colors.ENDC} {Colors.GREEN}{messages_24h:,}{Colors.ENDC}")
            print(f"{Colors.BOLD}Messages (7d):{Colors.ENDC} {Colors.GREEN}{messages_7d:,}{Colors.ENDC}")
            
            # Most active users
            print(f"\n{Colors.BOLD}Most Active Users:{Colors.ENDC}")
            for i, (user_id, username, count) in enumerate(active_users, 1):
                print(f"  {i}. {Colors.CYAN}{username}{Colors.ENDC} ({user_id}): {count:,} messages")
            
            # Most active channels
            print(f"\n{Colors.BOLD}Most Active Channels:{Colors.ENDC}")
            for i, (channel_id, count) in enumerate(active_channels, 1):
                print(f"  {i}. Channel {Colors.CYAN}{channel_id}{Colors.ENDC}: {count:,} messages")
            
            # Messages per day
            print(f"\n{Colors.BOLD}Messages per Day (Last 7 Days):{Colors.ENDC}")
            for day, count in messages_per_day:
                print(f"  {day}: {Colors.GREEN}{count:,}{Colors.ENDC} messages")
            
        except Exception as e:
            print(f"{Colors.RED}Error retrieving message statistics: {e}{Colors.ENDC}")
        finally:
            conn.close()
            
        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def modules_submenu(self):
        """Submenu for module configuration"""
        while True:
            try:
                self.clear_screen()
                
                config = self.load_config()
                modules = config.get('modules', {})
                
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.HEADER}              MODULE CONFIGURATION{Colors.ENDC}")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                # Display current module status
                print(f"{Colors.BOLD}Current Module Status:{Colors.ENDC}")
                i = 1
                module_list = []
                for module, enabled in modules.items():
                    status_color = Colors.GREEN if enabled else Colors.RED
                    status_text = "ENABLED" if enabled else "DISABLED"
                    print(f"{Colors.BOLD} {i}.{Colors.ENDC} {module}: {status_color}{status_text}{Colors.ENDC}")
                    module_list.append(module)
                    i += 1
                
                print(f"{Colors.BOLD} 0.{Colors.ENDC} Back to Main Menu")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                choice = safe_input(f"\n{Colors.CYAN}Enter module number to toggle (0 to return): {Colors.ENDC}").strip()
                
                if choice == '0':
                    break
                    
                try:
                    module_index = int(choice) - 1
                    if 0 <= module_index < len(module_list):
                        selected_module = module_list[module_index]
                        # Toggle module status
                        modules[selected_module] = not modules[selected_module]
                        self.save_config(config)
                        status = "enabled" if modules[selected_module] else "disabled"
                        print(f"{Colors.GREEN}Module {selected_module} {status} successfully!{Colors.ENDC}")
                        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                    else:
                        print(f"{Colors.RED}Invalid module number{Colors.ENDC}")
                        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                except ValueError:
                    print(f"{Colors.RED}Invalid input{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def blocked_words_submenu(self):
        """Submenu for blocked words management"""
        while True:
            try:
                self.clear_screen()
                
                config = self.load_config()
                blocked_words = config.get('blocked_words', [])
                
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.HEADER}              BLOCKED WORDS MANAGEMENT{Colors.ENDC}")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                print(f"{Colors.BOLD}Current Blocked Words ({len(blocked_words)}):{Colors.ENDC}")
                for i, word in enumerate(blocked_words, 1):
                    print(f"{Colors.BOLD} {i}.{Colors.ENDC} {Colors.RED}{word}{Colors.ENDC}")
                
                print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
                print(f"{Colors.BOLD} 1.{Colors.ENDC} Add Blocked Word")
                print(f"{Colors.BOLD} 2.{Colors.ENDC} Remove Blocked Word")
                print(f"{Colors.BOLD} 3.{Colors.ENDC} Clear All Blocked Words")
                print(f"{Colors.BOLD} 0.{Colors.ENDC} Back to Main Menu")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
                
                if choice == '0':
                    break
                elif choice == '1':
                    new_word = safe_input(f"Enter new word to block: ").strip().lower()
                    if new_word:
                        if new_word not in blocked_words:
                            blocked_words.append(new_word)
                            config['blocked_words'] = blocked_words
                            self.save_config(config)
                            print(f"{Colors.GREEN}Added '{new_word}' to blocked words{Colors.ENDC}")
                        else:
                            print(f"{Colors.YELLOW}Word already in blocked list{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '2':
                    if blocked_words:
                        word_index = safe_input(f"Enter word number to remove (1-{len(blocked_words)}): ").strip()
                        try:
                            idx = int(word_index) - 1
                            if 0 <= idx < len(blocked_words):
                                removed = blocked_words.pop(idx)
                                config['blocked_words'] = blocked_words
                                self.save_config(config)
                                print(f"{Colors.GREEN}Removed '{removed}' from blocked words{Colors.ENDC}")
                            else:
                                print(f"{Colors.RED}Invalid word number{Colors.ENDC}")
                        except ValueError:
                            print(f"{Colors.RED}Invalid input{Colors.ENDC}")
                    else:
                        print(f"{Colors.YELLOW}No words to remove{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '3':
                    confirm = safe_input(f"{Colors.RED}Are you sure you want to clear all blocked words? (y/N): {Colors.ENDC}").strip().lower()
                    if confirm == 'y':
                        config['blocked_words'] = []
                        self.save_config(config)
                        print(f"{Colors.GREEN}All blocked words cleared{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                    
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def config_submenu(self):
        """Submenu for bot configuration"""
        while True:
            try:
                self.clear_screen()
                
                config = self.load_config()
                
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.HEADER}              BOT CONFIGURATION{Colors.ENDC}")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                print(f"{Colors.BOLD}Current Configuration:{Colors.ENDC}")
                print(f"{Colors.BOLD} 1.{Colors.ENDC} Bot Prefix: {Colors.CYAN}{config.get('prefix', '!p7')}{Colors.ENDC}")
                print(f"{Colors.BOLD} 2.{Colors.ENDC} Log Channel: {Colors.CYAN}{config.get('log_channel', 'None')}{Colors.ENDC}")
                print(f"{Colors.BOLD} 3.{Colors.ENDC} Mod Log Channel: {Colors.CYAN}{config.get('mod_log_channel', 'None')}{Colors.ENDC}")
                print(f"{Colors.BOLD} 4.{Colors.ENDC} Security Alert Channel: {Colors.CYAN}{config.get('security_alert_channel', 'None')}{Colors.ENDC}")
                print(f"{Colors.BOLD} 5.{Colors.ENDC} Min Account Age: {Colors.CYAN}{config.get('security', {}).get('min_account_age_days', 7)} days{Colors.ENDC}")
                print(f"{Colors.BOLD} 6.{Colors.ENDC} Spam Threshold: {Colors.CYAN}{config.get('security', {}).get('spam_threshold', 8)} messages{Colors.ENDC}")
                print(f"{Colors.BOLD} 7.{Colors.ENDC} Max Mentions: {Colors.CYAN}{config.get('security', {}).get('max_mentions', 5)}{Colors.ENDC}")
                print(f"{Colors.BOLD} 8.{Colors.ENDC} Update Discord Token")
                
                print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
                print(f"{Colors.BOLD} 0.{Colors.ENDC} Back to Main Menu")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                choice = safe_input(f"\n{Colors.CYAN}Enter setting number to change (0 to return): {Colors.ENDC}").strip()
                
                if choice == '0':
                    break
                elif choice == '1':
                    new_prefix = safe_input(f"Enter new bot prefix (current: {config.get('prefix', '!p7')}): ").strip()
                    if new_prefix:
                        config['prefix'] = new_prefix
                        self.save_config(config)
                        print(f"{Colors.GREEN}Bot prefix updated to {new_prefix}{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '2':
                    new_channel = safe_input(f"Enter new log channel ID (current: {config.get('log_channel', 'None')}): ").strip()
                    if new_channel:
                        config['log_channel'] = new_channel
                        self.save_config(config)
                        print(f"{Colors.GREEN}Log channel updated to {new_channel}{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '3':
                    new_channel = safe_input(f"Enter new mod log channel ID (current: {config.get('mod_log_channel', 'None')}): ").strip()
                    if new_channel:
                        config['mod_log_channel'] = new_channel
                        self.save_config(config)
                        print(f"{Colors.GREEN}Mod log channel updated to {new_channel}{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '4':
                    new_channel = safe_input(f"Enter new security alert channel ID (current: {config.get('security_alert_channel', 'None')}): ").strip()
                    if new_channel:
                        config['security_alert_channel'] = new_channel
                        self.save_config(config)
                        print(f"{Colors.GREEN}Security alert channel updated to {new_channel}{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '5':
                    try:
                        new_age = int(safe_input(f"Enter new minimum account age in days (current: {config.get('security', {}).get('min_account_age_days', 7)}): ").strip())
                        if new_age >= 0:
                            if 'security' not in config:
                                config['security'] = {}
                            config['security']['min_account_age_days'] = new_age
                            self.save_config(config)
                            print(f"{Colors.GREEN}Minimum account age updated to {new_age} days{Colors.ENDC}")
                        else:
                            print(f"{Colors.RED}Value must be non-negative{Colors.ENDC}")
                    except ValueError:
                        print(f"{Colors.RED}Invalid input, must be a number{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '6':
                    try:
                        new_threshold = int(safe_input(f"Enter new spam threshold (current: {config.get('security', {}).get('spam_threshold', 8)}): ").strip())
                        if new_threshold > 0:
                            if 'security' not in config:
                                config['security'] = {}
                            config['security']['spam_threshold'] = new_threshold
                            self.save_config(config)
                            print(f"{Colors.GREEN}Spam threshold updated to {new_threshold}{Colors.ENDC}")
                        else:
                            print(f"{Colors.RED}Value must be positive{Colors.ENDC}")
                    except ValueError:
                        print(f"{Colors.RED}Invalid input, must be a number{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '7':
                    try:
                        new_max = int(safe_input(f"Enter new maximum mentions (current: {config.get('security', {}).get('max_mentions', 5)}): ").strip())
                        if new_max > 0:
                            if 'security' not in config:
                                config['security'] = {}
                            config['security']['max_mentions'] = new_max
                            self.save_config(config)
                            print(f"{Colors.GREEN}Maximum mentions updated to {new_max}{Colors.ENDC}")
                        else:
                            print(f"{Colors.RED}Value must be positive{Colors.ENDC}")
                    except ValueError:
                        print(f"{Colors.RED}Invalid input, must be a number{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '8':
                    token = safe_input(f"Enter new Discord token (will be hidden): ").strip()
                    if token:
                        success, message = self.update_env_token(token)
                        if success:
                            print(f"{Colors.GREEN}{message}{Colors.ENDC}")
                        else:
                            print(f"{Colors.RED}{message}{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def export_submenu(self):
        """Submenu for data export"""
        while True:
            try:
                self.clear_screen()
                
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.HEADER}              DATA EXPORT{Colors.ENDC}")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                print(f"{Colors.BOLD} 1.{Colors.ENDC} Export Security Logs")
                print(f"{Colors.BOLD} 2.{Colors.ENDC} Export Message Logs")
                print(f"{Colors.BOLD} 3.{Colors.ENDC} Export User Data")
                print(f"{Colors.BOLD} 4.{Colors.ENDC} Export Configuration")
                print(f"{Colors.BOLD} 5.{Colors.ENDC} Export Server Statistics")
                print(f"{Colors.BOLD} 0.{Colors.ENDC} Back to Main Menu")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
                
                if choice == '0':
                    break
                elif choice == '1':
                    self.export_security_logs()
                elif choice == '2':
                    self.export_message_logs()
                elif choice == '3':
                    self.export_user_data()
                elif choice == '4':
                    self.export_configuration()
                elif choice == '5':
                    self.export_server_statistics()
                else:
                    print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def export_configuration(self):
        """Export bot configuration to JSON file"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}           EXPORT CONFIGURATION{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        # Get export filename
        export_file = safe_input(f"Export filename (default: config_export.json): ").strip()
        if not export_file:
            export_file = "config_export.json"
        
        # Add .json extension if not present
        if not export_file.endswith('.json'):
            export_file += '.json'
        
        try:
            config = self.load_config()
            
            # Create a sanitized copy (remove sensitive data if needed)
            export_config = config.copy()
            
            # Write to file
            with open(export_file, 'w') as f:
                json.dump(export_config, f, indent=4)
            
            print(f"{Colors.GREEN}Successfully exported configuration to {export_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error exporting configuration: {e}{Colors.ENDC}")
        
        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def export_server_statistics(self):
        """Export server statistics to CSV"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}           EXPORT SERVER STATISTICS{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        # Get export parameters
        time_range = safe_input(f"Time range (all/24h/7d/30d): ").strip().lower()
        
        # Get export filename
        export_file = safe_input(f"Export filename (default: server_stats.csv): ").strip()
        if not export_file:
            export_file = "server_stats.csv"
        
        # Add .csv extension if not present
        if not export_file.endswith('.csv'):
            export_file += '.csv'
        
        # Get data from database
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
            
        try:
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT guild_id, member_count, online_count, channel_count, timestamp FROM server_stats WHERE 1=1"
            params = []
            
            if time_range == "24h":
                query += " AND timestamp > datetime('now', '-1 day')"
            elif time_range == "7d":
                query += " AND timestamp > datetime('now', '-7 days')"
            elif time_range == "30d":
                query += " AND timestamp > datetime('now', '-30 days')"
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            stats = cursor.fetchall()
            
            if not stats:
                print(f"{Colors.YELLOW}No server statistics found matching the criteria{Colors.ENDC}")
            else:
                # Write to CSV
                with open(export_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Guild ID', 'Member Count', 'Online Count', 'Channel Count', 'Timestamp'])
                    
                    for stat in stats:
                        writer.writerow(stat)
                
                print(f"{Colors.GREEN}Successfully exported {len(stats)} statistics records to {export_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error exporting server statistics: {e}{Colors.ENDC}")
        finally:
            conn.close()
            
        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def advanced_audit_menu(self):
        """Advanced audit logs menu"""
        while True:
            try:
                self.clear_screen()
                
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.HEADER}              ADVANCED AUDIT LOGS{Colors.ENDC}")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                print(f"{Colors.BOLD} 1.{Colors.ENDC} View All Audit Logs")
                print(f"{Colors.BOLD} 2.{Colors.ENDC} View Member Action Logs")
                print(f"{Colors.BOLD} 3.{Colors.ENDC} View Message Action Logs")
                print(f"{Colors.BOLD} 4.{Colors.ENDC} View Channel Action Logs")
                print(f"{Colors.BOLD} 5.{Colors.ENDC} View Role Action Logs")
                print(f"{Colors.BOLD} 6.{Colors.ENDC} View Server Action Logs")
                print(f"{Colors.BOLD} 7.{Colors.ENDC} Search Audit Logs by User")
                print(f"{Colors.BOLD} 8.{Colors.ENDC} Export Audit Logs")
                print(f"{Colors.BOLD} 0.{Colors.ENDC} Back to Main Menu")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
                
                if choice == '0':
                    break
                elif choice == '1':
                    self.view_audit_logs()
                elif choice == '2':
                    self.view_audit_logs(action_types=["member_ban", "member_unban", "member_kick", "member_timeout"])
               
                elif choice == '3':
                    self.view_audit_logs(action_types=["message_delete", "message_bulk_delete", "message_pin", "message_unpin"])
                elif choice == '4':
                    self.view_audit_logs(action_types=["channel_create", "channel_delete", "channel_update"])
                elif choice == '5':
                    self.view_audit_logs(action_types=["role_create", "role_delete", "role_update", "member_role_update"])
                elif choice == '6':
                    self.view_audit_logs(action_types=["guild_update", "webhook_create", "webhook_update", "webhook_delete"])
                elif choice == '7':
                    user_id = safe_input(f"Enter user ID: ").strip()
                    if user_id:
                        self.view_audit_logs(user_id=user_id)
                    else:
                        print(f"{Colors.RED}Invalid user ID{Colors.ENDC}")
                        safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                elif choice == '8':
                    self.export_audit_logs()
                else:
                    print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def view_audit_logs(self, user_id=None, action_types=None, limit=50):
        """View advanced audit logs with filters"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}              ADVANCED AUDIT LOGS{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        # Build filters for display
        filters = []
        if user_id:
            filters.append(f"User ID: {user_id}")
        if action_types:
            filters.append(f"Action Types: {', '.join(action_types)}")
        
        if filters:
            print(f"{Colors.BOLD}Filters:{Colors.ENDC} {', '.join(filters)}")
            print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
        
        # Get logs from database
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
            
        try:
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT id, action_type, guild_id, channel_id, user_id, target_id, details, timestamp FROM advanced_audit WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND (user_id = ? OR target_id = ?)"
                params.extend([user_id, user_id])
            
            if action_types:
                placeholders = ", ".join(["?" for _ in action_types])
                query += f" AND action_type IN ({placeholders})"
                params.extend(action_types)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            if not logs:
                print(f"{Colors.YELLOW}No audit logs found matching the criteria{Colors.ENDC}")
            else:
                # Display logs
                for log in logs:
                    log_id, action_type, guild_id, channel_id, user_id, target_id, details, timestamp = log
                    
                    print(f"{Colors.BOLD}ID:{Colors.ENDC} {log_id}")
                    print(f"{Colors.BOLD}Action:{Colors.ENDC} {Colors.BLUE}{action_type}{Colors.ENDC}")
                    print(f"{Colors.BOLD}User ID:{Colors.ENDC} {user_id}")
                    if target_id:
                        print(f"{Colors.BOLD}Target ID:{Colors.ENDC} {target_id}")
                    print(f"{Colors.BOLD}Guild ID:{Colors.ENDC} {guild_id}")
                    if channel_id:
                        print(f"{Colors.BOLD}Channel ID:{Colors.ENDC} {channel_id}")
                    print(f"{Colors.BOLD}Time:{Colors.ENDC} {timestamp}")
                    print(f"{Colors.BOLD}Details:{Colors.ENDC} {details}")
                    print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
                
                print(f"{Colors.GREEN}Found {len(logs)} audit logs{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error retrieving audit logs: {e}{Colors.ENDC}")
        finally:
            conn.close()
            
        safe_input(f"{Colors.YELLOW}Press Enter to continue...")
    
    def export_audit_logs(self):
        """Export audit logs to CSV"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}           EXPORT AUDIT LOGS{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        # Get export parameters
        time_range = safe_input(f"Time range (all/24h/7d/30d): ").strip().lower()
        action_type = safe_input(f"Action type (all or specific type): ").strip()
        
        if action_type.lower() == 'all':
            action_type = None
        
        # Get export filename
        export_file = safe_input(f"Export filename (default: audit_logs.csv): ").strip()
        if not export_file:
            export_file = "audit_logs.csv"
        
        # Add .csv extension if not present
        if not export_file.endswith('.csv'):
            export_file += '.csv'
        
        # Get logs from database
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
            
        try:
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT id, action_type, guild_id, channel_id, user_id, target_id, details, timestamp FROM advanced_audit WHERE 1=1"
            params = []
            
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)
            
            if time_range == "24h":
                query += " AND timestamp > datetime('now', '-1 day')"
            elif time_range == "7d":
                query += " AND timestamp > datetime('now', '-7 days')"
            elif time_range == "30d":
                query += " AND timestamp > datetime('now', '-30 days')"
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            if not logs:
                print(f"{Colors.YELLOW}No audit logs found matching the criteria{Colors.ENDC}")
            else:
                # Write to CSV
                with open(export_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['ID', 'Action Type', 'Guild ID', 'Channel ID', 'User ID', 'Target ID', 'Details', 'Timestamp'])
                    
                    for log in logs:
                        writer.writerow(log)
                
                print(f"{Colors.GREEN}Successfully exported {len(logs)} audit logs to {export_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error exporting audit logs: {e}{Colors.ENDC}")
        finally:
            conn.close()
            
        safe_input(f"{Colors.YELLOW}Press Enter to continue...")
    
    def maintenance_submenu(self):
        """Maintenance tools submenu"""
        while True:
            try:
                self.clear_screen()
                
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                print(f"{Colors.BOLD}{Colors.HEADER}              MAINTENANCE TOOLS{Colors.ENDC}")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                print(f"{Colors.BOLD} 1.{Colors.ENDC} Database Cleanup")
                print(f"{Colors.BOLD} 2.{Colors.ENDC} Database Vacuum")
                print(f"{Colors.BOLD} 3.{Colors.ENDC} Database Statistics")
                print(f"{Colors.BOLD} 4.{Colors.ENDC} Log File Management")
                print(f"{Colors.BOLD} 5.{Colors.ENDC} Delete Old Records")
                print(f"{Colors.BOLD} 0.{Colors.ENDC} Back to Main Menu")
                print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
                
                choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
                
                if choice == '0':
                    break
                elif choice == '1':
                    self.database_cleanup()
                elif choice == '2':
                    self.database_vacuum()
                elif choice == '3':
                    self.database_statistics()
                elif choice == '4':
                    self.log_file_management()
                elif choice == '5':
                    self.delete_old_records()
                else:
                    print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
                    safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
    
    def database_cleanup(self):
        """Clean up database by removing duplicate entries"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}              DATABASE CLEANUP{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
        
        try:
            cursor = conn.cursor()
            
            # Backup tables with potential duplicates
            print(f"{Colors.YELLOW}Creating temporary backup tables...{Colors.ENDC}")
            cursor.execute("CREATE TABLE IF NOT EXISTS messages_backup AS SELECT * FROM messages")
            cursor.execute("CREATE TABLE IF NOT EXISTS security_events_backup AS SELECT * FROM security_events")
            
            # Clean up messages table
            print(f"{Colors.YELLOW}Cleaning up messages table...{Colors.ENDC}")
            cursor.execute("CREATE TABLE IF NOT EXISTS messages_temp AS SELECT DISTINCT * FROM messages")
            cursor.execute("DROP TABLE messages")
            cursor.execute("ALTER TABLE messages_temp RENAME TO messages")
            
            # Clean up security_events table
            print(f"{Colors.YELLOW}Cleaning up security events table...{Colors.ENDC}")
            cursor.execute("CREATE TABLE IF NOT EXISTS security_events_temp AS SELECT DISTINCT * FROM security_events")
            cursor.execute("DROP TABLE security_events")
            cursor.execute("ALTER TABLE security_events_temp RENAME TO security_events")
            
            conn.commit()
            print(f"{Colors.GREEN}Database cleanup completed successfully{Colors.ENDC}")
            
        except Exception as e:
            print(f"{Colors.RED}Error during database cleanup: {e}{Colors.ENDC}")
            conn.rollback()
        finally:
            conn.close()
        
        safe_input(f"{Colors.YELLOW}Press Enter to continue...")
    
    def database_vacuum(self):
        """Vacuum database to optimize storage"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}              DATABASE VACUUM{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        print(f"{Colors.YELLOW}Starting database vacuum, this may take a while...{Colors.ENDC}")
        
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
        
        try:
            # Get size before vacuum
            db_size_before = os.path.getsize(self.db_path)
            
            # Perform vacuum
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            conn.commit()
            
            # Get size after vacuum
            db_size_after = os.path.getsize(self.db_path)
            
            # Calculate size difference
            size_diff = db_size_before - db_size_after
            size_diff_mb = size_diff / (1024 * 1024)
            
            print(f"{Colors.GREEN}Database vacuum completed successfully{Colors.ENDC}")
            print(f"{Colors.BOLD}Size before:{Colors.ENDC} {db_size_before / (1024 * 1024):.2f} MB")
            print(f"{Colors.BOLD}Size after:{Colors.ENDC} {db_size_after / (1024 * 1024):.2f} MB")
            print(f"{Colors.BOLD}Space saved:{Colors.ENDC} {size_diff_mb:.2f} MB")
            
        except Exception as e:
            print(f"{Colors.RED}Error during database vacuum: {e}{Colors.ENDC}")
        finally:
            conn.close()
        
        safe_input(f"{Colors.YELLOW}Press Enter to continue...")
    
    def database_statistics(self):
        """Show database statistics"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}              DATABASE STATISTICS{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
        
        try:
            cursor = conn.cursor()
            
            # Get database file size
            db_size = os.path.getsize(self.db_path)
            db_size_mb = db_size / (1024 * 1024)
            
            print(f"{Colors.BOLD}Database File Size:{Colors.ENDC} {db_size_mb:.2f} MB")
            
            # Get table counts
            tables = [
                ('messages', 'Messages'),
                ('security_events', 'Security Events'),
                ('users', 'Users'),
                ('advanced_audit', 'Audit Logs'),
                ('server_stats', 'Server Stats')
            ]
            
            print(f"\n{Colors.BOLD}Table Record Counts:{Colors.ENDC}")
            for table, display_name in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"  {display_name}: {Colors.CYAN}{count:,}{Colors.ENDC}")
                except:
                    print(f"  {display_name}: {Colors.RED}Table not found{Colors.ENDC}")
            
            # Get oldest and newest records
            print(f"\n{Colors.BOLD}Data Time Range:{Colors.ENDC}")
            for table, display_name in tables:
                if table in ['messages', 'security_events', 'advanced_audit', 'server_stats']:
                    try:
                        cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table}")
                        min_date, max_date = cursor.fetchone()
                        if min_date and max_date:
                            print(f"  {display_name}: {Colors.CYAN}{min_date}{Colors.ENDC} to {Colors.CYAN}{max_date}{Colors.ENDC}")
                        else:
                            print(f"  {display_name}: {Colors.YELLOW}No data{Colors.ENDC}")
                    except:
                        print(f"  {display_name}: {Colors.RED}Error retrieving date range{Colors.ENDC}")
            
        except Exception as e:
            print(f"{Colors.RED}Error retrieving database statistics: {e}{Colors.ENDC}")
        finally:
            conn.close()
        
        safe_input(f"{Colors.YELLOW}Press Enter to continue...")
    
    def log_file_management(self):
        """Manage log files"""
        while True:
            self.clear_screen()
            
            print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.HEADER}              LOG FILE MANAGEMENT{Colors.ENDC}")
            print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
            
            # List log files
            log_files = []
            for file in os.listdir('.'):
                if file.endswith('.log'):
                    size = os.path.getsize(file) / 1024  # KB
                    modified = datetime.fromtimestamp(os.path.getmtime(file))
                    log_files.append((file, size, modified))
            
            if not log_files:
                print(f"{Colors.YELLOW}No log files found{Colors.ENDC}")
            else:
                print(f"{Colors.BOLD}Available Log Files:{Colors.ENDC}")
                for i, (file, size, modified) in enumerate(log_files, 1):
                    print(f"{Colors.BOLD} {i}.{Colors.ENDC} {file} - {Colors.CYAN}{size:.2f} KB{Colors.ENDC} - {modified.strftime('%Y-%m-%d %H:%M:%S')}")
            
            print(f"{Colors.BLUE}{'-'*60}{Colors.ENDC}")
            print(f"{Colors.BOLD} 1.{Colors.ENDC} View Log File")
            print(f"{Colors.BOLD} 2.{Colors.ENDC} Delete Log File")
            print(f"{Colors.BOLD} 3.{Colors.ENDC} Archive Old Logs")
            print(f"{Colors.BOLD} 4.{Colors.ENDC} Truncate Log File")
            print(f"{Colors.BOLD} 0.{Colors.ENDC} Back")
            print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
            
            choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                # View log file
                if not log_files:
                    print(f"{Colors.YELLOW}No log files available to view{Colors.ENDC}")
                else:
                    file_num = safe_input(f"Enter log file number to view (1-{len(log_files)}): ").strip()
                    try:
                        idx = int(file_num) - 1
                        if 0 <= idx < len(log_files):
                            filename = log_files[idx][0]
                            self.view_log_file(filename)
                        else:
                            print(f"{Colors.RED}Invalid file number{Colors.ENDC}")
                    except ValueError:
                        print(f"{Colors.RED}Invalid input{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            elif choice == '2':
                # Delete log file
                if not log_files:
                    print(f"{Colors.YELLOW}No log files available to delete{Colors.ENDC}")
                else:
                    file_num = safe_input(f"Enter log file number to delete (1-{len(log_files)}): ").strip()
                    try:
                        idx = int(file_num) - 1
                        if 0 <= idx < len(log_files):
                            filename = log_files[idx][0]
                            confirm = safe_input(f"{Colors.RED}Are you sure you want to delete {filename}? (y/N): {Colors.ENDC}").strip().lower()
                            if confirm == 'y':
                                os.remove(filename)
                                print(f"{Colors.GREEN}File {filename} deleted{Colors.ENDC}")
                        else:
                            print(f"{Colors.RED}Invalid file number{Colors.ENDC}")
                    except ValueError:
                        print(f"{Colors.RED}Invalid input{Colors.ENDC}")
                    except Exception as e:
                        print(f"{Colors.RED}Error deleting file: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            elif choice == '3':
                # Archive old logs
                if not log_files:
                    print(f"{Colors.YELLOW}No log files available to archive{Colors.ENDC}")
                else:
                    try:
                        import zipfile
                        from datetime import datetime
                        
                        archive_name = f"logs_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                        
                        with zipfile.ZipFile(archive_name, 'w') as zipf:
                            for file, _, _ in log_files:
                                zipf.write(file)
                        
                        print(f"{Colors.GREEN}Logs archived to {archive_name}{Colors.ENDC}")
                        print(f"{Colors.YELLOW}Note: Original log files were not deleted{Colors.ENDC}")
                    except Exception as e:
                        print(f"{Colors.RED}Error archiving logs: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            elif choice == '4':
                # Truncate log file
                if not log_files:
                    print(f"{Colors.YELLOW}No log files available to truncate{Colors.ENDC}")
                else:
                    file_num = safe_input(f"Enter log file number to truncate (1-{len(log_files)}): ").strip()
                    try:
                        idx = int(file_num) - 1
                        if 0 <= idx < len(log_files):
                            filename = log_files[idx][0]
                            confirm = safe_input(f"{Colors.RED}Are you sure you want to truncate {filename}? (y/N): {Colors.ENDC}").strip().lower()
                            if confirm == 'y':
                                with open(filename, 'w') as f:
                                    f.write(f"Log file truncated on {datetime.now()}\n")
                                print(f"{Colors.GREEN}File {filename} truncated{Colors.ENDC}")
                        else:
                            print(f"{Colors.RED}Invalid file number{Colors.ENDC}")
                    except ValueError:
                        print(f"{Colors.RED}Invalid input{Colors.ENDC}")
                    except Exception as e:
                        print(f"{Colors.RED}Error truncating file: {e}{Colors.ENDC}")
                safe_input(f"{Colors.YELLOW}Press Enter to continue...")
    
    def view_log_file(self, filename):
        """View contents of a log file"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}              LOG FILE: {filename}{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        try:
            with open(filename, 'r') as f:
                content = f.read()
            
            if not content:
                print(f"{Colors.YELLOW}Log file is empty{Colors.ENDC}")
            else:
                # Show last 50 lines of the log file
                lines = content.splitlines()
                if len(lines) > 50:
                    print(f"{Colors.YELLOW}Showing last 50 lines of {len(lines)} total lines...{Colors.ENDC}")
                    lines = lines[-50:]
                
                for line in lines:
                    # Apply some color based on log level
                    if "ERROR" in line or "CRITICAL" in line:
                        print(f"{Colors.RED}{line}{Colors.ENDC}")
                    elif "WARNING" in line:
                        print(f"{Colors.YELLOW}{line}{Colors.ENDC}")
                    elif "INFO" in line:
                        print(f"{Colors.GREEN}{line}{Colors.ENDC}")
                    else:
                        print(line)
        except Exception as e:
            print(f"{Colors.RED}Error reading log file: {e}")
    
    def delete_old_records(self):
        """Delete old records from database"""
        self.clear_screen()
        
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}              DELETE OLD RECORDS{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
        print(f"{Colors.YELLOW}This will permanently delete old records from the database.{Colors.ENDC}")
        print(f"{Colors.YELLOW}It is recommended to export data before deleting.{Colors.ENDC}")
        
        # Ask which table to clean up
        print(f"\n{Colors.BOLD}Select table to clean up:{Colors.ENDC}")
        print(f"{Colors.BOLD} 1.{Colors.ENDC} Messages")
        print(f"{Colors.BOLD} 2.{Colors.ENDC} Security Events")
        print(f"{Colors.BOLD} 3.{Colors.ENDC} Audit Logs")
        print(f"{Colors.BOLD} 4.{Colors.ENDC} Server Stats")
        print(f"{Colors.BOLD} 0.{Colors.ENDC} Cancel")
        
        table_choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
        
        if table_choice == '0':
            return
        elif table_choice == '1':
            table = "messages"
            id_field = "id"
        elif table_choice == '2':
            table = "security_events"
            id_field = "id"
        elif table_choice == '3':
            table = "advanced_audit"
            id_field = "id"
        elif table_choice == '4':
            table = "server_stats"
            id_field = "id"
        else:
            print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Ask for time threshold
        print(f"\n{Colors.BOLD}Delete records older than:{Colors.ENDC}")
        print(f"{Colors.BOLD} 1.{Colors.ENDC} 30 days")
        print(f"{Colors.BOLD} 2.{Colors.ENDC} 60 days")
        print(f"{Colors.BOLD} 3.{Colors.ENDC} 90 days")
        print(f"{Colors.BOLD} 4.{Colors.ENDC} 180 days")
        print(f"{Colors.BOLD} 5.{Colors.ENDC} 1 year")
        print(f"{Colors.BOLD} 0.{Colors.ENDC} Cancel")
        
        age_choice = safe_input(f"\n{Colors.CYAN}Enter your choice: {Colors.ENDC}").strip()
        
        if age_choice == '0':
            return
        elif age_choice == '1':
            days = 30
        elif age_choice == '2':
            days = 60
        elif age_choice == '3':
            days = 90
        elif age_choice == '4':
            days = 180
        elif age_choice == '5':
            days = 365
        else:
            print(f"{Colors.RED}Invalid choice{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Final confirmation
        confirm = safe_input(f"\n{Colors.RED}Are you sure you want to delete all {table} older than {days} days? (yes/NO): {Colors.ENDC}").strip().lower()
        
        if confirm != 'yes':
            print(f"{Colors.YELLOW}Operation cancelled{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Delete records
        conn = self.get_db_connection()
        if not conn:
            print(f"{Colors.RED}Could not connect to database{Colors.ENDC}")
            safe_input(f"{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            return
        
        try:
            cursor = conn.cursor()
            
            # Count records before deletion
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE timestamp < datetime('now', '-{days} days')")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(f"{Colors.YELLOW}No records found older than {days} days{Colors.ENDC}")
            else:
                # Delete records
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < datetime('now', '-{days} days')")
                conn.commit()
                
                print(f"{Colors.GREEN}Successfully deleted {count} records from {table}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error deleting records: {e}{Colors.ENDC}")
            conn.rollback()
        finally:
            conn.close()
        
        safe_input(f"{Colors.YELLOW}Press Enter to continue...")
    
# Add main entry point to run the admin interface
if __name__ == "__main__":
    try:
        print(f"{Colors.GREEN}Starting Prot7 Admin Control Panel...{Colors.ENDC}")
        admin = Prot7Admin()
        admin.interactive_menu()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Program terminated by user.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}Fatal error: {e}{Colors.ENDC}")
