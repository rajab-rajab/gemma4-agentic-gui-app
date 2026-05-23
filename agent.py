"""
Agentic AI - A Desktop AI Agent with Local LLM Integration
Enhanced with additional tools, better security, and improved error handling.
"""

import os
import sys
import subprocess
import datetime
import threading
import psutil
import re
import socket
import shutil
import json
import ast
import secrets
import string
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import customtkinter as ctk
from openai import OpenAI
from tavily import TavilyClient
import html
from bs4 import BeautifulSoup
import tempfile
from pathlib import Path
from tkinter import filedialog  

# --- CONFIGURATION ---
LOCAL_LLM_URL = "http://127.0.0.1:5000/v1"
LOCAL_MODEL = "gemma"  # Change this to your actual model name

client = OpenAI(base_url=LOCAL_LLM_URL, api_key="not-needed")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None


# --- SAFE CALCULATOR (Replaces unsafe eval) ---

class SafeCalculator:
    """Secure math expression evaluator using AST parsing."""
    
    # Allowed operators and functions
    SAFE_FUNCTIONS = {
        'abs': abs, 'round': round, 'min': min, 'max': max,
        'sum': sum, 'pow': pow, 'divmod': divmod,
        'float': float, 'int': int,
    }
    
    SAFE_OPS = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a ** b,
        ast.UAdd: lambda a: a,
        ast.USub: lambda a: -a,
    }
    
    @classmethod
    def evaluate(cls, expression: str) -> Optional[str]:
        """Safely evaluate a mathematical expression."""
        try:
            # Disallow dangerous characters
            if re.search(r'[a-zA-Z_][a-zA-Z0-9_]*', expression) and \
               not all(word in cls.SAFE_FUNCTIONS for word in re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', expression)):
                return "Error: Invalid identifiers in expression"
            
            tree = ast.parse(expression, mode='eval')
            
            def evaluate_node(node):
                if isinstance(node, ast.Constant):
                    return node.value
                elif isinstance(node, ast.BinOp):
                    left = evaluate_node(node.left)
                    right = evaluate_node(node.right)
                    return cls.SAFE_OPS[type(node.op)](left, right)
                elif isinstance(node, ast.UnaryOp):
                    operand = evaluate_node(node.operand)
                    return cls.SAFE_OPS[type(node.op)](operand)
                elif isinstance(node, ast.Call):
                    func = cls.SAFE_FUNCTIONS.get(node.func.id)
                    if func and len(node.args) <= 2:
                        args = [evaluate_node(arg) for arg in node.args]
                        return func(*args)
                    raise ValueError("Unsafe function call")
                elif isinstance(node, ast.Expression):
                    return evaluate_node(node.body)
                else:
                    raise ValueError(f"Unsupported operation: {type(node).__name__}")
            
            result = evaluate_node(tree.body)
            return str(result) if result is not None else "Error: Could not evaluate"
        except Exception as e:
            return f"Error: {str(e)}"


# --- TOOL DEFINITIONS ---

class AgentTools:
    """Collection of tools available to the AI agent."""
    
    @staticmethod
    def get_datetime(format_type: str = "default") -> str:
        """
        Get current date and time.
        
        Args:
            format_type: "default" for YYYY-MM-DD HH:MM:SS, "date" for date only,
                        "time" for time only, "iso" for ISO format, "day" for day name,
                        "full" for full date with day name
        """
        now = datetime.datetime.now()
        formats = {
            "default": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "iso": now.isoformat(),
            "unix": str(int(now.timestamp())),
            "day": now.strftime("%A"),  # Monday, Tuesday, etc.
            "day_short": now.strftime("%a"),  # Mon, Tue, etc.
            "full": now.strftime("%A, %B %d, %Y"),  # Monday, May 10, 2026
            "full_with_time": now.strftime("%A, %B %d, %Y at %H:%M:%S"),
        }
        return formats.get(format_type, formats["default"])
    
    def save_session(self, filename: str = None) -> str:
        """Saves Brain & Heart state to JSON for the Dev Project session."""
        if not self.gui or not self.gui.chat_history:
            return "❌ No session history to save."
            
        if not filename:
            filename = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        data = {
            "metadata": {
                "project": "Gemma 4 Challenge",
                "brain": "Mr. Perfect",
                "heart": "Gemma 4 E4B",
                "timestamp": self.get_datetime("iso")
            },
            "history": self.gui.chat_history
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            return f"✅ Session saved to {filename}"
        except Exception as e:
            return f"❌ Save error: {str(e)}"

    def load_session(self, filepath: str) -> str:
        """The Brain reads the JSON and restores it to the GUI's memory."""
        if not os.path.exists(filepath):
            return f"❌ File not found: {filepath}"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Support both 'history' and 'chat_history' keys for compatibility
                history_data = data.get("history") or data.get("chat_history", [])
                
                if not history_data:
                    return "⚠️ Loaded file contains no conversation history."
                
                # IMPORTANT: Overwrite the GUI history list
                # This prevents the list from growing indefinitely
                self.gui.chat_history = [] 
                self.gui.chat_history = history_data
                
                # Trigger the UI refresh on the main thread
                self.gui.after(0, self.gui.refresh_chat_display)
                
                return f"Memory restored: {len(history_data)} messages."
        except Exception as e:
            return f"❌ Load error: {str(e)}"
    
    @staticmethod
    def run_powershell(command: str, timeout: int = 30) -> str:
        """Execute a PowerShell command and return output."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True, text=True, timeout=timeout
            )
            output = f"STDOUT: {result.stdout.strip()}" if result.stdout.strip() else ""
            output += f"\nSTDERR: {result.stderr.strip()}" if result.stderr.strip() else ""
            return output if output else "Command executed successfully (no output)"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def run_command(command: str, shell: bool = False) -> str:
        """Execute a system command (cross-platform)."""
        try:
            result = subprocess.run(
                command if shell else command.split(),
                capture_output=True, text=True, shell=shell, timeout=30
            )
            output = f"STDOUT: {result.stdout.strip()}" if result.stdout.strip() else ""
            output += f"\nSTDERR: {result.stderr.strip()}" if result.stderr.strip() else ""
            return output if output else "Command executed successfully (no output)"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def web_search(query: str) -> str:
        """
        Search the web for up-to-date information, news, or facts.
        Returns the top 4 most relevant results.
        """
        # 1. Try Tavily (Premium Search)
        if 'tavily' in globals():
            try:
                # Reduced to 4 results for faster processing and less token noise
                results = tavily.search(query=query, search_depth="advanced", max_results=4)
                
                if isinstance(results, dict) and 'results' in results:
                    formatted = [f"🔍 Search Results for: {query}", "=" * 50]
                    
                    for i, r in enumerate(results['results'], 1):
                        title = r.get('title', 'No title')
                        url = r.get('url', '')
                        # Shortened content to 180 chars for faster LLM reasoning
                        content = r.get('content', '')[:180]
                        formatted.append(f"[{i}] {title}\n   🔗 {url}\n   📝 {content}...\n")
                    
                    return "\n".join(formatted)
            except Exception as e:
                pass # Fallback to DuckDuckGo silently

        # 2. Fallback to DuckDuckGo (Simple Search)
        try:
            import urllib.request
            from urllib.parse import quote
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            # Simple parsing for search results (limited to top 3 for fallback)
            results = re.findall(r'<a class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
            snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]*)</a>', html)
            
            output = [f"🔍 Search (Fallback): {query}", "=" * 50]
            for i, (link, title) in enumerate(results[:3], 1):
                snippet = snippets[i-1] if i-1 < len(snippets) else "No description available."
                output.append(f"\n{i}. {title}\n   📎 {link}\n   💬 {snippet[:150]}...")
            
            return "\n".join(output)
        except Exception as e:
            return f"Error: All search providers failed. {str(e)}"
    @staticmethod
    def open_web(url: str) -> str:
        """
        Open a specific URL in the user's default web browser. 
        Use this when the user wants to 'visit', 'open', or 'see' a website directly.
        """
        try:
            if not url or not url.strip():
                return "Error: No URL provided."
            
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                if "." in url: # Basic check for domain-like strings
                    url = f"https://{url}"
                else:
                    return "Error: Invalid URL format."
            
            import webbrowser
            webbrowser.open(url, new=2)
            return f"✅ Successfully opened: {url}"
        except Exception as e:
            return f"❌ Error opening URL: {str(e)}"
    
    @staticmethod
    def get_system_info() -> str:
        """Get current system resource usage (CPU, RAM, and Swap)."""
        cpu = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return (
            f"CPU: {cpu}% ({cpu_count} cores)\n"
            f"RAM: {ram.percent}% used ({ram.used // (2**30)}GB / {ram.total // (2**30)}GB)\n"
            f"Swap: {swap.percent}% used ({swap.used // (2**30)}GB / {swap.total // (2**30)}GB)"
        )
    
    @staticmethod
    def list_files(path: str = ".", pattern: str = "*", include_hidden: bool = False) -> str:
        """List files in a directory."""
        try:
            p = Path(path)
            if not p.exists():
                return f"Error: Path does not exist: {path}"
            if not p.is_dir():
                return f"Error: Not a directory: {path}"
            
            files = []
            for item in p.iterdir():
                if not include_hidden and item.name.startswith('.'):
                    continue
                if pattern != "*" and not re.match(pattern.replace('*', '.*'), item.name):
                    continue
                size = item.stat().st_size if item.is_file() else 0
                files.append(f"{'[D]' if item.is_dir() else '[F]'} {item.name} ({size:,} bytes)")
            
            return "\n".join(sorted(files)) if files else "Directory is empty"
        except PermissionError:
            return "Error: Permission denied"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def read_file(filepath: str, max_lines: int = 100, encoding: str = "utf-8") -> str:
        """Read contents of a file."""
        try:
            p = Path(filepath)
            if not p.exists():
                return f"Error: File does not exist: {filepath}"
            if p.stat().st_size > 5 * 1024 * 1024:
                return "Error: File too large (>5MB). Use read_file_lines for large files."
            
            with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                lines = [f.readline() for _ in range(max_lines)]
                content = ''.join(lines)
            
            file_info = f"File: {filepath} | Size: {p.stat().st_size:,} bytes | Lines: {len(lines)}\n"
            return file_info + ("-" * 50) + "\n" + content
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def read_file_lines(filepath: str, start_line: int = 1, count: int = 50) -> str:
        """Read specific lines from a file."""
        try:
            p = Path(filepath)
            if not p.exists():
                return f"Error: File does not exist: {filepath}"
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f, 1):
                    if i >= start_line:
                        lines.append(line.rstrip())
                    if len(lines) >= count:
                        break
            
            return f"Lines {start_line}-{start_line + len(lines) - 1}:\n" + ("-" * 50) + "\n" + "\n".join(lines)
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def write_file(filepath: str, content: str, append: bool = False) -> str:
        """Write content to a file."""
        try:
            mode = 'a' if append else 'w'
            with open(filepath, mode, encoding='utf-8') as f:
                f.write(content)
            return f"Successfully {'appended to' if append else 'wrote'} file: {filepath}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def calculate(expression: str) -> str:
        """Safely evaluate a mathematical expression."""
        return SafeCalculator.evaluate(expression)
    
    @staticmethod
    def get_weather(location: str) -> str:
        """Get current weather for a location using Tavily API."""
        if not tavily:
            return "Error: Tavily API not configured. Set TAVILY_API_KEY environment variable for weather."
        
        try:
            results = tavily.search(query=f"current weather in {location}", search_depth="advanced", max_results=3)
            
            if isinstance(results, dict) and 'results' in results:
                formatted = [f"🌤️ Weather for: {location}"]
                formatted.append("=" * 60)
                
                for r in results['results'][:3]:
                    title = r.get('title', 'Weather Info')
                    url = r.get('url', '')
                    content = r.get('content', '')[:300]
                    formatted.append(f"\n📍 {title}")
                    formatted.append(f"🔗 {url}")
                    formatted.append(f"📝 {content}")
                
                return "\n".join(formatted)
            
            return str(results)[:1000]
        except Exception as e:
            return f"Weather Error: {str(e)}"
    
    @staticmethod
    def ping_host(host: str, count: int = 4) -> str:
        """Ping a host to check connectivity."""
        try:
            # Determine OS and use appropriate ping command
            param = '-n' if os.name == 'nt' else '-c'
            result = subprocess.run(
                ['ping', param, str(count), host],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout if result.stdout else result.stderr
        except subprocess.TimeoutExpired:
            return "Error: Ping timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_current_directory() -> str:
        """Get current working directory."""
        return os.getcwd()
    
    @staticmethod
    def change_directory(path: str) -> str:
        """Change current working directory."""
        try:
            new_path = Path(path).resolve()
            if not new_path.exists():
                return f"Error: Directory does not exist: {path}"
            if not new_path.is_dir():
                return f"Error: Not a directory: {path}"
            os.chdir(new_path)
            return f"Changed directory to: {new_path}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def generate_password(length: int = 16, include_special: bool = True) -> str:
        """Generate a secure random password."""
        length = max(8, min(128, length))  # Clamp between 8 and 128
        alphabet = string.ascii_letters + string.digits
        if include_special:
            alphabet += string.punctuation
        
        while True:
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            # Ensure password has good entropy
            if (any(c.islower() for c in password) and
                any(c.isupper() for c in password) and
                any(c.isdigit() for c in password) and
                (not include_special or any(c in string.punctuation for c in password))):
                return password
    
    @staticmethod
    def get_disk_usage(path: str = "/") -> str:
        """Get disk usage statistics."""
        try:
            usage = psutil.disk_usage(path)
            return (
                f"Path: {path}\n"
                f"Total: {usage.total // (2**30):,} GB\n"
                f"Used: {usage.used // (2**30):,} GB ({usage.percent}%)\n"
                f"Free: {usage.free // (2**30):,} GB"
            )
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_network_info() -> str:
        """Get network connection information."""
        try:
            info = []
            interfaces = psutil.net_if_addrs()
            for iface, addrs in interfaces.items():
                info.append(f"{iface}:")
                for addr in addrs:
                    info.append(f"  {addr.family.name}: {addr.address}")
            return "\n".join(info)
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_processes(limit: int = 10) -> str:
        """Get running processes sorted by CPU or memory usage."""
        try:
            processes = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(p.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by memory usage
            processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
            
            output = [f"Top {min(limit, len(processes))} Processes by Memory:\n{'-' * 60}"]
            for proc in processes[:limit]:
                output.append(
                    f"PID: {proc['pid']:>6} | {proc['name'][:30]:<30} | "
                    f"CPU: {proc['cpu_percent'] or 0:>5.1f}% | RAM: {proc['memory_percent'] or 0:>5.1f}%"
                )
            return "\n".join(output)
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def kill_process(pid: int) -> str:
        """Terminate a process by PID."""
        try:
            process = psutil.Process(pid)
            name = process.name()
            process.terminate()
            return f"Terminated process: {name} (PID: {pid})"
        except psutil.NoSuchProcess:
            return f"Error: Process with PID {pid} not found"
        except psutil.AccessDenied:
            return f"Error: Access denied to process {pid}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_clipboard() -> str:
        """Get current clipboard content."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            content = root.clipboard_get()
            root.destroy()
            return content[:1000] if len(content) > 1000 else content
        except Exception:
            return "Clipboard is empty or contains non-text data"
    
    @staticmethod
    def set_clipboard(text: str) -> str:
        """Set clipboard content."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
            return f"Copied {len(text)} characters to clipboard"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_ip_info() -> str:
        """Get public IP address information."""
        try:
            import urllib.request
            url = "https://ipapi.co/json/"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            return (
                f"Public IP: {data.get('ip', 'Unknown')}\n"
                f"City: {data.get('city', 'Unknown')}\n"
                f"Region: {data.get('region', 'Unknown')}\n"
                f"Country: {data.get('country_name', 'Unknown')}\n"
                f"ISP: {data.get('org', 'Unknown')}\n"
                f"ASN: {data.get('asn', 'Unknown')}"
            )
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def check_port(host: str, port: int, timeout: int = 3) -> str:
        """Check if a port is open on a host."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return f"Port {port} on {host} is OPEN"
            else:
                return f"Port {port} on {host} is CLOSED"
        except socket.gaierror:
            return f"Error: Could not resolve host {host}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def dns_lookup(hostname: str) -> str:
        """Perform DNS lookup for a hostname."""
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            return f"Error: Could not resolve {hostname}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_file_info(filepath: str) -> str:
        """Get detailed file information."""
        try:
            p = Path(filepath)
            if not p.exists():
                return f"Error: File does not exist: {filepath}"
            
            stat = p.stat()
            created = datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            return (
                f"Path: {p.resolve()}\n"
                f"Size: {stat.st_size:,} bytes ({stat.st_size / (2**20):.2f} MB)\n"
                f"Created: {created}\n"
                f"Modified: {modified}\n"
                f"Type: {'Directory' if p.is_dir() else 'File'}\n"
                f"Permissions: {oct(stat.st_mode)[-3:]}"
            )
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def search_files(pattern: str, path: str = ".", max_results: int = 20) -> str:
        """Search for files matching a pattern."""
        try:
            results = list(Path(path).rglob(f"*{pattern}*"))[:max_results]
            if not results:
                return f"No files found matching '{pattern}' in {path}"
            
            output = [f"Found {len(results)} matching files:\n{'-' * 50}"]
            for r in results:
                size = r.stat().st_size if r.is_file() else 0
                output.append(f"{'[D]' if r.is_dir() else '[F]'} {r} ({size:,} bytes)")
            return "\n".join(output)
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_uptime() -> str:
        """Get system uptime."""
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"System Uptime: {days}d {hours}h {minutes}m {seconds}s"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_battery_status() -> str:
        """Get battery status (if available)."""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return "No battery detected"
            
            percent = battery.percent
            plugged = battery.power_plugged
            status = "Charging" if plugged else "On Battery"
            
            return (
                f"Battery: {percent}% {'[CHARGING]' if plugged else '[DISCHARGING]'}\n"
                f"Status: {status}"
            )
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_cpu_info() -> str:
        """Get detailed CPU information."""
        try:
            cpu_freq = psutil.cpu_freq()
            return (
                f"Physical Cores: {psutil.cpu_count(logical=False)}\n"
                f"Logical Cores: {psutil.cpu_count(logical=True)}\n"
                f"Current Frequency: {cpu_freq.current:.0f} MHz\n"
                f"Min Frequency: {cpu_freq.min:.0f} MHz\n"
                f"Max Frequency: {cpu_freq.max:.0f} MHz"
            )
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_memory_info() -> str:
        """Get detailed memory information."""
        try:
            vm = psutil.virtual_memory()
            sm = psutil.swap_memory()
            return (
                f"Virtual Memory:\n"
                f"  Total: {vm.total // (2**30):,} GB\n"
                f"  Available: {vm.available // (2**30):,} GB\n"
                f"  Used: {vm.used // (2**30):,} GB ({vm.percent}%)\n"
                f"Swap Memory:\n"
                f"  Total: {sm.total // (2**30):,} GB\n"
                f"  Used: {sm.used // (2**30):,} GB ({sm.percent}%)\n"
                f"  Free: {sm.free // (2**30):,} GB"
            )
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def delete_file(filepath: str) -> str:
        """
        Delete a file or empty folder with security restrictions.
        
        Restrictions:
        - Requires user confirmation (handled by GUI)
        - Cannot delete system partitions (C:, D:, etc.)
        - Cannot delete system directories (Windows, System32, etc.)
        - Only one file or empty folder at a time
        - Cannot delete non-empty folders
        
        Args:
            filepath: Path to the file or folder to delete
            
        Returns:
            Confirmation message or error
        """
        # Protected paths that cannot be deleted
        PROTECTED_PATHS = {
            'C:', 'D:', 'E:', 'F:', 'G:', 'H:',  # Windows drives
            '/', '/bin', '/boot', '/dev', '/etc', '/lib', '/lib64',  # Linux system dirs
            '/proc', '/root', '/run', '/sbin', '/sys', '/tmp',  # Linux system dirs
            '/usr', '/var', '/home',
            'Windows', 'Program Files', 'Program Files (x86)',
            'System32', 'SysWOW64', 'SystemRoot',
        }
        
        # Patterns for system files that cannot be deleted
        PROTECTED_PATTERNS = [
            'bootmgr', 'boot.ini', 'config.sys', 'autoexec.bat',
            '.sys', '.dll',
        ]
        
        # Agent self-protection patterns
        PROTECTED_AGENT_FILES = {
            'agent.py', 'agent.exe', 'main.py', 'main.exe',
            'requirements.txt', 'README.md', 'LICENSE', 'README.txt',
            'python.exe', 'python3.exe', 'pythonw.exe', 'py.exe',
            'ollama.exe', 'lm studio.exe', 'lmstudio.exe',
        }
        
        try:
            p = Path(filepath).resolve()
            
            # Check 1: File/folder exists
            if not p.exists():
                return f"Error: Path does not exist: {filepath}"
            
            # Check 2: Normalize and check for partition/system paths
            path_str = str(p)
            path_lower = path_str.lower()
            filename_lower = p.name.lower()
            
            # Check for system drive/partition
            for protected in PROTECTED_PATHS:
                if path_lower.startswith(protected.lower()) and len(path_str) <= len(protected) + 3:
                    return f"Error: CANNOT DELETE protected partition: {protected}"
            
            # Check if path IS a partition root
            if p.match('?:\\') or p == Path('/'):
                return f"Error: CANNOT DELETE partition root: {path_str}"
            
            # Check for Windows system directories
            if 'windows' in path_lower or 'system32' in path_lower or 'syswow64' in path_lower:
                return f"Error: CANNOT DELETE system directory: {path_str}"
            
            # Check for protected patterns in filename
            for pattern in PROTECTED_PATTERNS:
                if pattern.lower() in filename_lower:
                    return f"Error: CANNOT DELETE system file: {p.name}"
            
            # Check for agent self-protection
            for agent_file in PROTECTED_AGENT_FILES:
                if agent_file.lower() == filename_lower:
                    return f"Error: CANNOT DELETE protected agent file: {p.name}\n" \
                           f"This is a critical file for the agent's operation."
            
            # Check for venv or virtual environment
            if 'venv' in path_lower or '.venv' in path_lower or 'env' in path_lower:
                return f"Error: CANNOT DELETE virtual environment: {p.name}\n" \
                       f"Virtual environments contain critical dependencies."
            
            # Check for LLM related files
            llm_patterns = ['ollama', 'lm studio', 'llama.cpp', 'gemma', 'mistral', 'model']
            for llm_pattern in llm_patterns:
                if llm_pattern in path_lower:
                    return f"Error: CANNOT DELETE LLM related file: {p.name}\n" \
                           f"This may be critical for the LLM server operation."
            
            # Check 3: Check if it's a directory
            if p.is_dir():
                # Check if directory is empty
                try:
                    contents = list(p.iterdir())
                    if contents:
                        return f"Error: Cannot delete non-empty folder: {p.name}\nFolder contains {len(contents)} items.\nDelete contents first or use a different path."
                except PermissionError:
                    return f"Error: Permission denied accessing: {p.name}"
                
                # Ask for confirmation (will be handled by GUI)
                return f"CONFIRM_DELETE:{path_str}|FOLDER:{p.name}"
            else:
                # It's a file - ask for confirmation
                file_size = p.stat().st_size
                return f"CONFIRM_DELETE:{path_str}|FILE:{p.name}|SIZE:{file_size}"
        
        except PermissionError:
            return f"Error: Permission denied: {filepath}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def confirm_delete(filepath: str) -> str:
        """
        Actually perform the deletion after user confirmation.
        
        Args:
            filepath: Path to delete (MUST be from a previous delete_file call)
        """
        try:
            p = Path(filepath)
            
            if not p.exists():
                return f"Error: Path no longer exists: {filepath}"
            
            if p.is_dir():
                # Double-check it's still empty
                try:
                    contents = list(p.iterdir())
                    if contents:
                        return f"Error: Folder is no longer empty. Aborted."
                except:
                    pass
                p.rmdir()
                return f"✅ Deleted empty folder: {p.name}"
            else:
                p.unlink()
                return f"✅ Deleted file: {p.name}"
        
        except PermissionError:
            return f"Error: Permission denied"
        except FileNotFoundError:
            return f"Error: File not found"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def create_folder(folderpath: str) -> str:
        """
        Create a new folder/directory.
        
        Args:
            folderpath: Path for the new folder
            
        Returns:
            Success or error message
        """
        try:
            p = Path(folderpath)
            
            if p.exists():
                return f"Error: Folder already exists: {folderpath}"
            
            p.mkdir(parents=True, exist_ok=False)
            return f"✅ Created folder: {p.name}\nPath: {p.resolve()}"
        except FileExistsError:
            return f"Error: Folder already exists: {folderpath}"
        except PermissionError:
            return f"Error: Permission denied: {folderpath}"
        except Exception as e:
            return f"Error: {str(e)}"
    
       
    @staticmethod
    def copy_file(source: str, destination: str) -> str:
        """
        Copy a file or folder to destination.
        
        Args:
            source: Source path
            destination: Destination path
            
        Returns:
            Success or error message
        """
        try:
            src = Path(source)
            dst = Path(destination)
            
            if not src.exists():
                return f"Error: Source does not exist: {source}"
            
            # If destination is a directory, preserve filename
            if dst.is_dir():
                dst = dst / src.name
            
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=False)
            else:
                shutil.copy2(src, dst)
            
            return f"✅ Copied {'folder' if src.is_dir() else 'file'}: {src.name}\nTo: {dst.resolve()}"
        except FileExistsError:
            return f"Error: Destination already exists: {destination}"
        except PermissionError:
            return f"Error: Permission denied"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def move_file(source: str, destination: str) -> str:
        """
        Move a file or folder to destination.
        
        Args:
            source: Source path
            destination: Destination path
            
        Returns:
            Success or error message
        """
        try:
            src = Path(source)
            dst = Path(destination)
            
            if not src.exists():
                return f"Error: Source does not exist: {source}"
            
            # If destination is a directory, preserve filename
            if dst.is_dir():
                dst = dst / src.name
            
            shutil.move(str(src), str(dst))
            return f"✅ Moved {'folder' if src.is_dir() else 'file'}: {src.name}\nTo: {dst.resolve()}"
        except FileExistsError:
            return f"Error: Destination already exists: {destination}"
        except PermissionError:
            return f"Error: Permission denied"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def rename_file(oldpath: str, newname: str) -> str:
        """
        Rename a file or folder.
        
        Args:
            oldpath: Current path
            newname: New name (not full path)
            
        Returns:
            Success or error message
        """
        try:
            src = Path(oldpath)
            
            if not src.exists():
                return f"Error: Path does not exist: {oldpath}"
            
            # Get parent directory and new name
            parent = src.parent
            dst = parent / newname
            
            if dst.exists():
                return f"Error: Name already exists: {newname}"
            
            src.rename(dst)
            return f"✅ Renamed: {src.name} → {newname}\nNew path: {dst.resolve()}"
        except PermissionError:
            return f"Error: Permission denied"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_file_hash(filepath: str, algorithm: str = "md5") -> str:
        """
        Calculate hash of a file.
        
        Args:
            filepath: Path to file
            algorithm: "md5", "sha1", "sha256" (default: md5)
            
        Returns:
            Hash string or error
        """
        import hashlib
        
        if not Path(filepath).exists():
            return f"Error: File does not exist: {filepath}"
        
        try:
            hash_funcs = {
                "md5": hashlib.md5,
                "sha1": hashlib.sha1,
                "sha256": hashlib.sha256,
            }
            
            if algorithm.lower() not in hash_funcs:
                return f"Error: Unknown algorithm. Use: {', '.join(hash_funcs.keys())}"
            
            hash_obj = hash_funcs[algorithm.lower()]()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_obj.update(chunk)
            
            return f"{algorithm.upper()}={hash_obj.hexdigest()}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    # ===== POWERSHELL COMMAND TOOLS =====
    
    @staticmethod
    def ps_get_services(status: str = "all") -> str:
        """
        Get Windows services using PowerShell.
        
        Args:
            status: "all", "running", "stopped" (default: all)
        """
        try:
            status_filter = {
                "all": "Get-Service",
                "running": "Get-Service | Where-Object {$_.Status -eq 'Running'}",
                "stopped": "Get-Service | Where-Object {$_.Status -eq 'Stopped'}",
            }.get(status, "Get-Service")
            
            cmd = f"""
            $services = {status_filter} | Select-Object Name, DisplayName, Status | Format-Table -AutoSize | Out-String
            Write-Output $services
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_service_action(service_name: str, action: str) -> str:
        """
        Start, stop, or restart a Windows service.
        
        Args:
            service_name: Name of the service
            action: "start", "stop", "restart"
        """
        try:
            actions = {
                "start": f"Start-Service -Name '{service_name}'",
                "stop": f"Stop-Service -Name '{service_name}'",
                "restart": f"Restart-Service -Name '{service_name}'",
            }
            
            if action not in actions:
                return f"Error: Invalid action. Use: start, stop, restart"
            
            cmd = f"{actions[action]}; Write-Output 'Service {action} completed successfully'"
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_eventlog(logname: str = "System", count: int = 10) -> str:
        """
        Get Windows Event Log entries.
        
        Args:
            logname: "Application", "System", "Security" (default: System)
            count: Number of entries (default: 10)
        """
        try:
            cmd = f"""
            Get-EventLog -LogName '{logname}' -Newest {count} | 
            Select-Object TimeGenerated, EntryType, Source, Message | 
            Format-Table -AutoSize -Wrap | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_processes_detailed() -> str:
        """
        Get detailed process information with PowerShell.
        """
        try:
            cmd = """
            Get-Process | Sort-Object CPU -Descending | 
            Select-Object Name, Id, CPU, WorkingSet, Path | 
            Format-Table -AutoSize | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_registry(key_path: str) -> str:
        """
        Read Windows Registry keys.
        
        Args:
            key_path: Registry path (e.g., HKLM:\\SOFTWARE\\Microsoft)
        """
        try:
            cmd = f"Get-Item -Path '{key_path}' -ErrorAction SilentlyContinue | Select-Object Name, Property; Get-ItemProperty -Path '{key_path}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Property | ForEach-Object {{ Write-Output \"$_=$( (Get-ItemProperty -Path '{key_path}' -Name $_).$_ )\" }}"
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else f"Registry key not found or access denied: {key_path}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_scheduled_tasks() -> str:
        """
        Get Windows Scheduled Tasks.
        """
        try:
            cmd = """
            Get-ScheduledTask | Select-Object TaskName, State, TaskPath | 
            Format-Table -AutoSize | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_installed_programs() -> str:
        """
        Get list of installed programs (Windows).
        """
        try:
            cmd = """
            $programs = @()
            $paths = @(
                'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
                'HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
                'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'
            )
            foreach ($path in $paths) {
                Get-ItemProperty -Path $path -ErrorAction SilentlyContinue | 
                Where-Object { $_.DisplayName } | 
                Select-Object DisplayName, DisplayVersion, Publisher, InstallDate, UninstallString | 
                ForEach-Object { $programs += $_ }
            }
            $programs | Sort-Object DisplayName -Unique | 
            Format-Table -AutoSize | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=60)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_environment_vars() -> str:
        """
        Get Windows Environment Variables.
        """
        try:
            cmd = """
            Write-Output "=== USER VARIABLES ==="
            Get-ChildItem Env: -ErrorAction SilentlyContinue | 
            Where-Object { $_.Scope -eq 'User' } | 
            Format-Table Name, Value -AutoSize | Out-String
            Write-Output "`n=== MACHINE VARIABLES ==="
            Get-ChildItem Env: -ErrorAction SilentlyContinue | 
            Where-Object { $_.Scope -eq 'Machine' } | 
            Format-Table Name, Value -AutoSize | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_network_adapters() -> str:
        """
        Get Windows Network Adapter information.
        """
        try:
            cmd = """
            Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } |
            Select-Object Name, InterfaceDescription, Status, LinkSpeed, MacAddress |
            Format-Table -AutoSize | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_firewall_rules(enabled_only: bool = True) -> str:
        """
        Get Windows Firewall Rules.
        
        Args:
            enabled_only: Show only enabled rules (default: True)
        """
        try:
            filter_ps = "Where-Object { $_.Enabled -eq 'True' }" if enabled_only else ""
            cmd = f"""
            Get-NetFirewallRule {filter_ps} |
            Select-Object Name, DisplayName, Direction, Action, Enabled |
            Sort-Object DisplayName |
            Format-Table -AutoSize | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_disk_partitions() -> str:
        """
        Get Windows Disk Partition information.
        """
        try:
            cmd = """
            Get-Disk | Select-Object Number, FriendlyName, Size, PartitionStyle, OperationalStatus |
            Format-Table -AutoSize | Out-String
            Write-Output "`n=== PARTITIONS ==="
            Get-Partition | Select-Object DiskNumber, PartitionNumber, DriveLetter, Size, Type |
            Format-Table -AutoSize | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_wifi_networks() -> str:
        """
        Get available WiFi networks.
        """
        try:
            cmd = """
            netsh wlan show networks mode=bssid | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_hotfixes() -> str:
        """
        Get installed Windows Hotfixes.
        """
        try:
            cmd = """
            Get-HotFix | Sort-Object InstalledOn -Descending |
            Select-Object HotFixID, Description, InstalledOn, InstalledBy |
            Format-Table -AutoSize | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_running_tasks() -> str:
        """
        Get running tasks (similar to tasklist).
        """
        try:
            cmd = """
            Get-Process | Select-Object Name, Id, CPU, WorkingSet64, @{N='RAM(MB)';E={[math]::Round($_.WorkingSet64/1MB,2)}}, Path |
            Sort-Object CPU -Descending |
            Format-Table -AutoSize | Out-String
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def ps_get_systeminfo() -> str:
        """
        Get comprehensive Windows System Information.
        """
        try:
            cmd = """
            $os = Get-CimInstance Win32_OperatingSystem
            $cs = Get-CimInstance Win32_ComputerSystem
            $cpu = Get-CimInstance Win32_Processor
            Write-Output "=== SYSTEM INFO ==="
            Write-Output "Computer Name: $($cs.Name)"
            Write-Output "Domain: $($cs.Domain)"
            Write-Output ""
            Write-Output "=== OPERATING SYSTEM ==="
            Write-Output "OS: $($os.Caption) $($os.Version)"
            Write-Output "Architecture: $($os.OSArchitecture)"
            Write-Output "Build: $($os.BuildNumber)"
            Write-Output ""
            Write-Output "=== HARDWARE ==="
            Write-Output "CPU: $($cpu.Name)"
            Write-Output "Cores: $($cpu.NumberOfCores)"
            Write-Output "Logical Processors: $($cpu.NumberOfLogicalProcessors)"
            Write-Output "RAM: $([math]::Round($cs.TotalPhysicalMemory/1GB,2)) GB"
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    # ===== PROGRAM INSTALLATION/UNINSTALLATION TOOLS =====
    
    # System programs that CANNOT be uninstalled
    PROTECTED_PROGRAMS = {
        # Windows core
        'microsoft', 'windows', 'kernel', 'system', 'runtime',
        'visual c++', 'vcruntime', 'msvc', '.net framework', 'dotnet',
        'intel', 'nvidia', 'amd', 'radeon', 'geforce', '驱动', '驱动程序',
        'realtek', 'audio', 'graphics', 'wireless', 'bluetooth',
        # System services
        'service', 'spooler', 'print', 'dhcp', 'dns', 'winsock',
        # Boot and recovery
        'boot', 'recovery', 'backup', 'restore', 'system restore',
    }
    
    @staticmethod
    def search_program(program_name: str) -> str:
        """
        Search for a program online to get download information.
        
        Args:
            program_name: Name of program to search
            
        Returns:
            Search results with download URLs and info
        """
        try:
            # Search for official download page
            search_results = tavily.search(
                query=f"{program_name} official download site:filepost, filedrop, download",
                search_depth="advanced",
                max_results=5
            ) if tavily else None
            
            if not search_results:
                # Fallback to simple search
                return AgentTools.web_search_simple(f"{program_name} official download site:official")
            
            formatted = ["🔍 Search Results for: " + program_name + "\n"]
            formatted.append("=" * 50)
            
            if isinstance(search_results, dict) and 'results' in search_results:
                for r in search_results['results'][:5]:
                    title = r.get('title', 'No title')
                    url = r.get('url', '')
                    snippet = r.get('content', '')[:200]
                    
                    # Check for suspicious keywords
                    is_official = any(official in title.lower() for official in ['official', 'download', 'site'])
                    badge = "✅ OFFICIAL" if is_official else "⚠️ VERIFY"
                    
                    formatted.append(f"\n{badge}: {title}")
                    formatted.append(f"URL: {url}")
                    formatted.append(f"Info: {snippet}...")
            
            return "\n".join(formatted)
        except Exception as e:
            return f"Search Error: {str(e)}"
    
    @staticmethod
    def validate_program_safety(program_name: str, url: str = "") -> str:
        """
        Validate if a program is safe to install (basic checks).
        
        Args:
            program_name: Name of the program
            url: Download URL (optional)
            
        Returns:
            "SAFE", "WARNING: <reason>", or "UNSAFE: <reason>"
        """
        name_lower = program_name.lower()
        url_lower = url.lower() if url else ""
        
        # Check for protected/system programs
        for protected in AgentTools.PROTECTED_PROGRAMS:
            if protected in name_lower:
                return f"UNSAFE: '{program_name}' appears to be a system program that should not be removed"
        
        # Check for suspicious patterns in URL
        suspicious_domains = ['torrent', 'crack', 'keygen', 'serial', 'patch', ' activator']
        for suspicious in suspicious_domains:
            if suspicious in url_lower:
                return f"UNSAFE: Download source appears to be pirated software"
        
        # Check for common malware keywords
        malware_keywords = ['malware', 'trojan', 'virus', 'keylogger', 'ransomware', 'spyware']
        for keyword in malware_keywords:
            if keyword in name_lower or keyword in url_lower:
                return f"UNSAFE: Program name or URL contains suspicious keyword: {keyword}"
        
        # Check URL security (HTTPS only)
        if url and not url.startswith('https'):
            return f"WARNING: Download URL is not using HTTPS (insecure connection)"
        
        # Check for known safe download sources
        safe_domains = [
            'microsoft.com', 'google.com', 'adobe.com', 'github.com',
            'python.org', 'nodejs.org', 'git-scm.com', 'visualstudio.com',
            'download.com', 'softonic.com', 'filehippo.com', 'chip.de',
            'sourceforge.net', 'npmjs.com', 'pypi.org', 'rubygems.org'
        ]
        
        if url:
            from urllib.parse import urlparse
            try:
                domain = urlparse(url).netloc.lower()
                if any(safe in domain for safe in safe_domains):
                    return "SAFE"
                elif domain:
                    return f"WARNING: Download from third-party site ({domain}). Verify before installing."
            except:
                pass
        
        return "VERIFY_NEEDED"
    
    @staticmethod
    def get_installed_programs_list() -> str:
        """
        Get list of installed programs for uninstallation selection.
        
        Returns:
            Formatted list of installed programs
        """
        try:
            cmd = """
            $programs = @()
            $paths = @(
                'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
                'HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
                'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'
            )
            foreach ($path in $paths) {{
                $prog = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue | 
                    Where-Object {{ $_.DisplayName -eq '{program_display_name}' }}
                if ($prog) {{ $programs += $prog }}
            }}
            if ($programs.Count -gt 0) {{
                $programs[0] | Select-Object DisplayName, UninstallString, Publisher | Format-List | Out-String
            }} else {{
                Write-Output "NOT_FOUND"
            }}
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=60)
            output = result.stdout if result.stdout else result.stderr
            
            # Mark potential system programs
            lines = output.split('\n')
            marked_lines = []
            for line in lines:
                marked = line
                for protected in AgentTools.PROTECTED_PROGRAMS:
                    if protected in line.lower():
                        marked = line + " ⚠️ SYSTEM"
                        break
                marked_lines.append(marked)
            
            return '\n'.join(marked_lines)
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def check_program_removable(program_display_name: str) -> str:
        """
        Check if a program can be safely uninstalled.
        
        Args:
            program_display_name: Display name of program to check
            
        Returns:
            Confirmation message with safety status
        """
        name_lower = program_display_name.lower()
        
        # Check for system programs
        for protected in AgentTools.PROTECTED_PROGRAMS:
            if protected in name_lower:
                return f"UNSAFE: '{program_display_name}' is a SYSTEM program and should NOT be uninstalled. " \
                       f"Uninstalling this may damage your operating system."
        
        # Check if program has uninstall string
        try:
            cmd = f"""
            $programs = @()
            $paths = @(
                'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
                'HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
                'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'
            )
            foreach ($path in $paths) {{
                $prog = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue | 
                    Where-Object {{ $_.DisplayName -eq '{program_display_name}' }}
                if ($prog -and $prog.UninstallString) {{
                    Write-Output $prog.UninstallString
                    break
                }}
            }}
            """
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            output = result.stdout.strip()
            
            if "NOT_FOUND" in output:
                return f"Program '{program_display_name}' not found in installed programs list."
            
            return f"CHECK_PASSED: '{program_display_name}' appears to be safe for uninstallation.\n\n{output}"
        except Exception as e:
            return f"Error checking program: {str(e)}"
    
    @staticmethod
    def prepare_install_command(program_name: str, download_url: str) -> str:
        """
        Prepare installation command for user confirmation.
        
        Args:
            program_name: Name of program
            download_url: Download URL
            
        Returns:
            Installation command info for confirmation dialog
        """
        safety = AgentTools.validate_program_safety(program_name, download_url)
        
        if safety.startswith("UNSAFE"):
            return f"ERROR: {safety}"
        
        if safety.startswith("WARNING"):
            return f"CONFIRM_INSTALL:{program_name}|URL:{download_url}|WARNING:{safety}"
        
        return f"CONFIRM_INSTALL:{program_name}|URL:{download_url}|STATUS:{safety}"
    
    @staticmethod
    def prepare_uninstall_command(program_name: str, uninstall_string: str = "") -> str:
        """
        Prepare uninstallation command for user confirmation.
        
        Args:
            program_name: Display name of program
            uninstall_string: Uninstall command string (optional)
            
        Returns:
            Confirmation message or error
        """
        # First check if it's a system program
        safety_check = AgentTools.check_program_removable(program_name)
        if "UNSAFE" in safety_check:
            return f"ERROR: {safety_check}"
        
        if not uninstall_string:
            # Get uninstall string from registry
            try:
                cmd = f"""
                $paths = @(
                    'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
                    'HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',
                    'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'
                )
                foreach ($path in $paths) {{
                    $prog = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue | 
                        Where-Object {{ $_.DisplayName -eq '{program_name}' }}
                    if ($prog -and $prog.UninstallString) {{
                        Write-Output $prog.UninstallString
                        break
                    }}
                }}
                """
                result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
                uninstall_string = result.stdout.strip()
            except Exception as e:
                return f"Error getting uninstall string: {str(e)}"
        
        if not uninstall_string:
            return f"ERROR: Could not find uninstall information for '{program_name}'"
        
        return f"CONFIRM_UNINSTALL:{program_name}|CMD:{uninstall_string}"
    
    @staticmethod
    def execute_install(program_name: str, download_url: str) -> str:
        """
        Execute program installation after user confirmation.
        
        Args:
            program_name: Name of program
            download_url: Download URL
            
        Returns:
            Installation result
        """
        try:
            import urllib.request
            import tempfile
            
            # Download to temp folder
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, f"{program_name}_installer.exe")
            
            # Try to download
            try:
                req = urllib.request.Request(
                    download_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, timeout=60) as response:
                    with open(file_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
            except Exception as e:
                return f"Download failed: {str(e)}\n\n" \
                       f"Please download manually from:\n{download_url}\n\n" \
                       f"Then run the installer manually."
            
            # Run installer with admin privileges
            if os.path.exists(file_path):
                result = subprocess.run(
                    [file_path],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=300
                )
                
                # Cleanup
                try:
                    os.remove(file_path)
                except:
                    pass
                
                if result.returncode == 0:
                    return f"✅ Installation of '{program_name}' completed successfully!"
                else:
                    return f"⚠️ Installation completed with issues:\n{result.stderr or result.stdout}"
            else:
                return f"Please download manually from:\n{download_url}"
        
        except Exception as e:
            return f"Installation error: {str(e)}"
    
    @staticmethod
    def execute_uninstall(program_name: str, uninstall_string: str) -> str:
        """
        Execute program uninstallation after user confirmation.
        
        Args:
            program_name: Display name of program
            uninstall_string: Uninstall command
            
        Returns:
            Uninstall result
        """
        try:
            # Execute uninstall command
            # Handle MSI and EXE uninstallers differently
            if 'MsiExec' in uninstall_string:
                # MSI uninstaller
                cmd = uninstall_string + ' /qn /norestart'
                result = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            else:
                # EXE uninstaller
                cmd = uninstall_string
                result = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            
            if result.returncode == 0:
                return f"✅ Uninstallation of '{program_name}' completed successfully!"
            else:
                return f"⚠️ Uninstallation completed with issues:\n{result.stderr or result.stdout}"
        
        except subprocess.TimeoutExpired:
            return "Uninstallation timed out. The program may still be removing. Please wait and check manually."
        except Exception as e:
            return f"Uninstallation error: {str(e)}"
    
    # ===== PROGRAM UPDATE TOOLS =====
    
    @staticmethod
    def check_program_updates(program_name: str) -> str:
        """
        Check for program updates online (REQUIRES USER REQUEST).
        NEVER auto-check or auto-update without user permission.
        Uses Tavily API ONLY.
        
        Args:
            program_name: Name of program to check for updates
            
        Returns:
            Search results showing available updates
        """
        if not tavily:
            return "Error: Tavily API not configured. Set TAVILY_API_KEY environment variable for update checks."
        
        try:
            search_results = tavily.search(
                query=f"{program_name} latest version 2024 2025 official download update",
                search_depth="advanced",
                max_results=5
            )
            
            if isinstance(search_results, dict) and 'results' in search_results:
                formatted = [f"🔍 Checking for updates: {program_name}\n"]
                formatted.append("=" * 50)
                
                for r in search_results['results'][:5]:
                    title = r.get('title', 'No title')
                    url = r.get('url', '')
                    snippet = r.get('content', '')[:300]
                    
                    formatted.append(f"\n📦 {title}")
                    formatted.append(f"🔗 {url}")
                    formatted.append(f"📝 {snippet}")
                
                formatted.append("\n" + "=" * 50)
                formatted.append("\n⚠️ To update, please request 'update [program_name]'")
                return "\n".join(formatted)
            else:
                return "Error: Could not fetch update information. Please try again."
        except Exception as e:
            return f"Update check error: {str(e)}"
    
    @staticmethod
    def validate_update_safety(program_name: str, download_url: str) -> str:
        """
        Validate if an update source is safe.
        
        Args:
            program_name: Name of program
            download_url: Download URL for update
            
        Returns:
            Safety status
        """
        # Reuse validation from install safety
        return AgentTools.validate_program_safety(program_name, download_url)
    
    @staticmethod
    def prepare_update_command(program_name: str, download_url: str) -> str:
        """
        Prepare update command with user confirmation.
        UPDATES ARE TREATED AS NEW INSTALLATIONS.
        
        Args:
            program_name: Name of program to update
            download_url: Download URL for new version
            
        Returns:
            Confirmation message
        """
        # First check if it's not a system program
        name_lower = program_name.lower()
        for protected in AgentTools.PROTECTED_PROGRAMS:
            if protected in name_lower:
                return f"ERROR: '{program_name}' is a system program and should NOT be updated."
        
        # Validate safety
        safety = AgentTools.validate_update_safety(program_name, download_url)
        
        if safety.startswith("UNSAFE"):
            return f"ERROR: {safety}"
        
        return f"CONFIRM_UPDATE:{program_name}|URL:{download_url}|STATUS:{safety}"
    
    @staticmethod
    def execute_update(program_name: str, download_url: str) -> str:
        """
        Execute program update after user confirmation.
        Downloads and runs the latest version installer.
        
        Args:
            program_name: Name of program
            download_url: Download URL
            
        Returns:
            Update result
        """
        try:
            import urllib.request
            import tempfile
            
            # Download to temp folder
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, f"{program_name}_update.exe")
            
            # Try to download
            try:
                req = urllib.request.Request(
                    download_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, timeout=60) as response:
                    with open(file_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
            except Exception as e:
                return f"Download failed: {str(e)}\n\n" \
                       f"Please download manually from:\n{download_url}"
            
            # Run updater/installer
            if os.path.exists(file_path):
                result = subprocess.run(
                    [file_path],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=300
                )
                
                # Cleanup
                try:
                    os.remove(file_path)
                except:
                    pass
                
                if result.returncode == 0:
                    return f"✅ Update of '{program_name}' completed successfully!"
                else:
                    return f"⚠️ Update completed with issues:\n{result.stderr or result.stdout}"
            else:
                return f"Please download manually from:\n{download_url}"
        
        except Exception as e:
            return f"Update error: {str(e)}"
    
    # ===== SELF-PROTECTION TOOLS =====
    
    # Critical files that CANNOT be modified/deleted
    PROTECTED_SELF_FILES = {
        'agent.py', 'agent.exe', 'main.py', 'main.exe',
        'requirements.txt', 'README.md', 'LICENSE',
        'venv', '.venv', 'env', '.env',
        'python.exe', 'python3.exe', 'pythonw.exe',
        'ollama', 'ollama.exe',
    }
    
    @staticmethod
    def validate_self_protection(path: str) -> str:
        """
        Check if a path is protected (agent itself or critical files).
        
        Args:
            path: Path to check
            
        Returns:
            "PROTECTED" or "OK"
        """
        try:
            path_obj = Path(path)
            path_lower = str(path_obj).lower()
            name = path_obj.name.lower()
            
            # Check if trying to modify this agent
            for protected in AgentTools.PROTECTED_SELF_FILES:
                if protected.lower() in name or protected.lower() in path_lower:
                    return f"PROTECTED: Cannot modify '{path}' - this is a critical agent file"
            
            # Check for running LLM processes
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        proc_name = proc.info['name'].lower()
                        if 'ollama' in proc_name or 'lm studio' in proc_name:
                            # Check if the path contains references to the LLM
                            if 'llm' in path_lower or 'ollama' in path_lower or 'model' in path_lower:
                                return f"PROTECTED: Cannot modify '{path}' - this is a critical LLM file"
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except:
                pass
            
            return "OK"
        except Exception as e:
            return f"OK"  # If we can't check, allow it (will be caught by other checks)
    
    @staticmethod
    def get_agent_info() -> str:
        """
        Get information about this agent.
        
        Returns:
            Agent details and statistics
        """
        try:
            agent_path = Path(__file__).resolve() if '__file__' in globals() else Path.cwd()
            tool_count = len(TOOL_MAP)
            
            return (
                f"🤖 Agentic AI - Local LLM Assistant\n"
                f"{'=' * 40}\n"
                f"Version: 2.0.0\n"
                f"Agent Path: {agent_path}\n"
                f"Total Tools: {tool_count}\n"
                f"Available Functions: {len(AgentTools.__dict__)}\n"
                f"{'=' * 40}\n"
                f"⚠️ Note: This agent cannot modify or delete itself.\n"
                f"⚠️ Local LLM processes are also protected."
            )
        except Exception as e:
            return f"Error getting agent info: {str(e)}"
    
    # ===== SYSTEM SHUTDOWN TOOL =====
    
    @staticmethod
    def shutdown_computer(force: bool = False) -> str:
        """
        Prepare to shutdown the computer. REQUIRES USER CONFIRMATION.
        
        Args:
            force: If True, force close all programs (default: False)
            
        Returns:
            Confirmation message for GUI dialog
        """
        return f"CONFIRM_SHUTDOWN:{'FORCE' if force else 'NORMAL'}|Close all programs and shutdown this computer?"
    
    @staticmethod
    def prepare_shutdown(force: bool = False) -> str:
        """
        Prepare shutdown with user confirmation.
        """
        return f"CONFIRM_SHUTDOWN:{'FORCE' if force else 'NORMAL'}"
    
    @staticmethod
    def execute_shutdown(force: bool = False) -> str:
        """
        Execute system shutdown after user confirmation.
        This will close all programs and shutdown the computer.
        
        Args:
            force: If True, force close all programs
        """
        try:
            if os.name == 'nt':  # Windows
                if force:
                    os.system('shutdown /s /f /t 0')
                else:
                    os.system('shutdown /s /t 0')
                return "🖥️ Computer will shutdown in a moment. Goodbye!"
            else:  # Linux/Mac
                os.system('sudo shutdown -h now')
                return "🖥️ Computer will shutdown in a moment. Goodbye!"
        except Exception as e:
            return f"Shutdown error: {str(e)}"
    
    @staticmethod
    def restart_computer() -> str:
        """
        Prepare to restart the computer. REQUIRES USER CONFIRMATION.
        """
        return "CONFIRM_RESTART"
    
    @staticmethod
    def execute_restart() -> str:
        """
        Execute system restart after user confirmation.
        """
        try:
            if os.name == 'nt':  # Windows
                os.system('shutdown /r /t 0')
            else:  # Linux/Mac
                os.system('sudo shutdown -r now')
            return "🖥️ Computer will restart in a moment. See you soon!"
        except Exception as e:
            return f"Restart error: {str(e)}"
    
    @staticmethod
    def sleep_computer() -> str:
        """
        Put computer to sleep mode.
        """
        try:
            if os.name == 'nt':  # Windows
                os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            else:  # Linux/Mac
                os.system('systemctl suspend')
            return "💤 Computer will enter sleep mode."
        except Exception as e:
            return f"Sleep error: {str(e)}"
    
    # ===== CODING TOOLS =====
    
    @staticmethod
    def execute_code(code: str = None, language: str = "python", **kwargs) -> str:
        """
        Executes code snippets dynamically. 
        Handles JSON-wrapped inputs and ensures code is shown in the output.
        """
        import json
        import subprocess
        import sys
        import os
        import tempfile
        import re

        # 1. Flexible Argument Extraction
        # Handles 'code', 'content', 'script' etc.
        input_val = code or kwargs.get('code') or kwargs.get('content') or kwargs.get('script')
        lang_val = language or kwargs.get('language') or "python"

        # 2. JSON Unwrapping
        # If the LLM sent a JSON string like {"code": "...", "language": "python"}
        if input_val and str(input_val).strip().startswith("{"):
            try:
                data = json.loads(input_val)
                input_val = data.get('code') or data.get('content') or input_val
                lang_val = data.get('language') or lang_val
            except:
                pass

        if not input_val:
            return "❌ Error: No code provided to execute."

        # 3. Clean Markdown Backticks
        if "```" in str(input_val):
            input_val = re.sub(r"```[\w]*\n", "", str(input_val)).replace("```", "").strip()

        # Create a display block for the UI so the user sees the code
        display_header = f"--- EXECUTING {lang_val.upper()} ---\n```python\n{input_val}\n```\n"

        # 4. Execution Logic via Temp File
        suffix = ".py" if "python" in lang_val.lower() else ".js"
        tmp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode='w', encoding='utf-8')
        
        try:
            tmp_file.write(input_val)
            tmp_file.close()
            tmp_path = tmp_file.name

            # Select interpreter
            if suffix == ".py":
                cmd = [sys.executable, tmp_path]
            else:
                cmd = ['node', tmp_path]

            # Run with a 30-second timeout
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            os.unlink(tmp_path) # Cleanup

            # 5. Format the Result
            output = result.stdout.strip()
            errors = result.stderr.strip()

            if result.returncode == 0:
                final_out = f"📤 Output:\n{output}" if output else "✅ Execution successful (No printed output)."
                return f"{display_header}{final_out}"
            else:
                return f"{display_header}❌ Runtime Error:\n{errors}"

        except subprocess.TimeoutExpired:
            if os.path.exists(tmp_path): os.unlink(tmp_path)
            return f"{display_header}❌ Error: Execution timed out (30s limit)."
        except Exception as e:
            if 'tmp_path' in locals() and os.path.exists(tmp_path): os.unlink(tmp_path)
            return f"❌ System Error: {str(e)}"
    @staticmethod
    def run_file(filepath: str = None, **kwargs) -> str:
        """
        Executes scripts and opens HTML. Now with Emergency Unpacking for messy AI inputs.
        """
        import subprocess
        import sys
        import os
        import webbrowser
        import json
        from pathlib import Path

        # 1. FORCE ABSOLUTE PATH
        BASE_DIR = Path(r"C:\Users\RAJAB BAIG\Documents\GitHub\BAIG\PERFECT")
        
        # --- 2. EMERGENCY UNPACKER (Fixes "No filepath provided" errors) ---
        # If the input is a JSON string, we extract the actual path
        if filepath and str(filepath).strip().startswith("{"):
            try:
                data = json.loads(filepath)
                filepath = data.get('filepath') or data.get('path')
            except:
                pass

        raw_path = filepath or kwargs.get('filepath') or kwargs.get('path')
        
        if not raw_path:
            return "❌ Error: No filepath provided (Received empty input)."

        # 3. GARBAGE CLEANER
        # Cleans trailing quotes or braces: MYRAJAB.html"} -> MYRAJAB.html
        clean_name = str(raw_path).split('"')[0].split('}')[0].strip().strip("'\"")
        p = (BASE_DIR / Path(clean_name).name).absolute()

        if not p.exists():
            return f"❌ Error: File not found at {p}"

        try:
            ext = p.suffix.lower()
            cwd = str(p.parent)
            
            # --- 4. EXECUTION LOGIC ---
            if ext in ['.html', '.htm']:
                file_uri = p.as_uri()
                webbrowser.open(file_uri)
                return f"✅ HTML file opened in browser: {file_uri}"

            elif ext == '.py':
                cmd = [sys.executable, str(p)]
            elif ext == '.js':
                cmd = ['node', str(p)]
            elif ext == '.php':
                cmd = ['php', str(p)]
            elif ext == '.java':
                cmd = ['java', str(p)]
            elif ext == '.c':
                exe_path = p.with_suffix('.exe')
                subprocess.run(['gcc', str(p), '-o', str(exe_path)], capture_output=True)
                cmd = [str(exe_path)]
            elif ext == '.cpp':
                exe_path = p.with_suffix('.exe')
                subprocess.run(['g++', str(p), '-o', str(exe_path)], capture_output=True)
                cmd = [str(exe_path)]
            else:
                os.startfile(str(p))
                return f"✅ Opened {p.name} with default application."

            # 5. RUN COMMAND
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd)
            if result.returncode == 0:
                return f"✅ Execution Successful: {p.name}\n📤 Output:\n{result.stdout.strip() or '(No output)'}"
            else:
                return f"❌ Execution Failed: {p.name}\n⚠️ Error:\n{result.stderr.strip()}"

        except Exception as e:
            return f"❌ System Error: {str(e)}"
    @staticmethod
    def create_code_file(filepath: str = None, content: str = None, **kwargs) -> str:
        """The most robust version: Extracts clean code and filename, skipping JSON envelopes."""
        import json, re, os
        from pathlib import Path

        # 1. SET MANDATORY DIRECTORY
        BASE_DIR = Path(r"C:\Users\RAJAB BAIG\Documents\GitHub\BAIG\PERFECT")
        BASE_DIR.mkdir(parents=True, exist_ok=True)

        # 2. EXTRACT FILENAME AND CONTENT (Handing JSON-in-a-string)
        # Check if the 'filepath' argument is actually a full JSON block
        raw_input = str(filepath) if filepath else str(kwargs.get('filepath', ''))
        
        extracted_filepath = filepath
        extracted_content = content or kwargs.get('content') or kwargs.get('code')

        # Logic to unpack if the AI sent the whole dictionary as one string
        if raw_input.strip().startswith("{") or '"filepath":' in raw_input:
            try:
                # Use regex for quick extraction of filepath
                match = re.search(r'"filepath":\s*"([^"]+)"', raw_input)
                if match:
                    extracted_filepath = match.group(1)
                
                # Try standard JSON parsing to get content
                data = json.loads(raw_input)
                extracted_filepath = data.get('filepath') or data.get('path') or extracted_filepath
                extracted_content = data.get('content') or data.get('code') or extracted_content
            except:
                pass

        # --- FIX: RE-PURIFY CONTENT ---
        # If 'extracted_content' is still a JSON string, we must unpack it to get the PURE code
        if extracted_content and str(extracted_content).strip().startswith("{"):
            try:
                data = json.loads(str(extracted_content))
                # Only take the value of 'content' or 'code' if it exists
                extracted_content = data.get('content') or data.get('code') or extracted_content
            except:
                pass

        # Final fallback check
        final_filename = extracted_filepath or "script.py"
        final_code = extracted_content or ""

        # 3. CLEAN THE FILENAME (Remove any remaining JSON garbage)
        clean_name = str(final_filename).replace('{', '').replace('}', '').replace('"', '').replace("'", "").strip()
        clean_name = Path(clean_name).name # Get just the filename (e.g. index.html)

        if not clean_name or clean_name == ".":
            clean_name = "generated_code.py"

        final_full_path = BASE_DIR / clean_name

        # 4. CLEAN CODE CONTENT (Remove Markdown backticks)
        if "```" in str(final_code):
            final_code = re.sub(r"```[\w]*\n", "", str(final_code)).replace("```", "").strip()

        # 5. WRITE FILE
        try:
            # We ensure we are writing a string and not a dictionary/list
            final_full_path.write_text(str(final_code), encoding='utf-8')
            return f"✅ File saved successfully at: {final_full_path.resolve()}"
        except Exception as e:
            return f"❌ System File Error: {str(e)}"
    @staticmethod
    def generate_code_template(task: str = None, language: str = "python", **kwargs) -> str:
        """
        Generate code templates. (Self removed)
        """
        actual_task = task or kwargs.get('task')
        actual_lang = (language or kwargs.get('language') or "python").lower()

        if not actual_task:
            return "❌ Error: No task provided."

        templates = {
            "python": {
                "web_server": "import http.server\nimport socketserver\nPORT = 8080\nHandler = http.server.SimpleHTTPRequestHandler\nwith socketserver.TCPServer(('', PORT), Handler) as httpd:\n    print(f'Server running at http://localhost:{PORT}')\n    httpd.serve_forever()",
                "api": "from flask import Flask, jsonify\napp = Flask(__name__)\n@app.route('/api')\ndef home(): return jsonify({'status': 'online'})\nif __name__ == '__main__': app.run()",
                "class": "class MyClass:\n    def __init__(self, name):\n        self.name = name\n    def greet(self): return f'Hello {self.name}'",
                "function": "def my_function(data):\n    return data"
            },
            "javascript": {
                "web_server": "const http = require('http');\nhttp.createServer((req, res) => { res.end('Hello'); }).listen(3000);",
                "class": "class MyClass { constructor(name) { this.name = name; } }",
                "function": "function myFunc(data) { return data; }"
            }
        }

        task_lower = str(actual_task).lower()
        lang_dict = templates.get(actual_lang, templates["python"])
        selected = None

        if any(w in task_lower for w in ['server', 'web']): selected = lang_dict.get('web_server')
        elif any(w in task_lower for w in ['api', 'rest']): selected = lang_dict.get('api')
        elif any(w in task_lower for w in ['class', 'object']): selected = lang_dict.get('class')
        elif any(w in task_lower for w in ['function', 'def']): selected = lang_dict.get('function')

        if selected:
            md = "javascript" if actual_lang == "javascript" else "python"
            return f"📝 **{actual_lang.upper()} Code Template Generated:**\n```{md}\n{selected}\n```"
        
        return "❌ No specific template found for that description."

    @staticmethod
    def check_code_syntax(code: str, language: str = "python", **kwargs) -> str:
        """
        Verify syntax without running. Shows the code being checked.
        """
        code = code or kwargs.get('code')
        if not code: return "❌ No code provided."
        
        if "```" in code:
            code = re.sub(r"```[\w]*\n", "", code).replace("```", "").strip()

        try:
            if language.lower() == "python":
                ast.parse(code)
                return f"✅ Python syntax is valid.\n```python\n{code}\n```"
            
            elif language.lower() == "javascript":
                temp = tempfile.NamedTemporaryFile(suffix='.js', delete=False)
                temp.write(code.encode())
                temp.close()
                result = subprocess.run(['node', '--check', temp.name], capture_output=True, text=True)
                os.unlink(temp.name)
                if result.returncode == 0:
                    return f"✅ JavaScript syntax is valid.\n```javascript\n{code}\n```"
                return f"❌ JS Syntax Error:\n{result.stderr}"

            return f"❌ Syntax check not supported for {language}"
        except SyntaxError as e:
            return f"❌ Syntax Error: {e.msg} at line {e.lineno}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def local_html_file(filepath: str = None, **kwargs) -> str:
        """
        Starts a local HTTP server and opens HTML files via http://localhost:8000.
        """
        import http.server
        import socketserver
        import threading
        import webbrowser
        import time
        import os
        from pathlib import Path

        # 1. SETUP PATHS
        BASE_DIR = Path(r"C:\Users\RAJAB BAIG\Documents\GitHub\BAIG\PERFECT")
        PORT = 8000

        # 2. CLEAN FILENAME
        raw_path = filepath or kwargs.get('filepath') or kwargs.get('path')
        if not raw_path:
            return "❌ Error: No filename provided."
        
        # Strip JSON garbage
        clean_name = str(raw_path).split('"')[0].split('}')[0].strip().strip("'\"")
        filename = Path(clean_name).name
        target_file = BASE_DIR / filename

        if not target_file.exists():
            return f"❌ Error: {filename} does not exist in the PERFECT folder."

        # 3. BACKGROUND SERVER LOGIC
        def start_background_server():
            # This class serves files specifically from our PERFECT directory
            class MyHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(BASE_DIR), **kwargs)
                def log_message(self, format, *args): pass # Silence console logs

            socketserver.TCPServer.allow_reuse_address = True
            try:
                with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
                    httpd.serve_forever()
            except Exception:
                # If server is already running, this will catch the "Address in use" error silently
                pass

        # Start server thread if not already active
        server_thread = threading.Thread(target=start_background_server, daemon=True)
        server_thread.start()
        
        # Give it a split second to initialize
        time.sleep(0.2)

        # 4. OPEN VIA HTTP
        url = f"http://localhost:{PORT}/{filename}"
        try:
            webbrowser.open(url)
            return f"✅ Success! File is now serving at: {url}"
        except Exception as e:
            return f"❌ Failed to open browser: {str(e)}"
    @staticmethod
    def get_code_snippet_info(language: str) -> str:
        """
        Get helpful information and common patterns for a language.
        
        Args:
            language: Programming language name
            
        Returns:
            Language info and examples
        """
        language_info = {
            "python": {
                "name": "Python",
                "version": "3.x",
                "extensions": [".py"],
                "info": """
🐍 **Python Information:**

• **Extensions:** .py
• **Comment:** # single line, \"\"\"docstring\"\"\" for multi-line
• **Variables:** x = 10, name = "John"
• **Lists:** [1, 2, 3], list.append(), list[0]
• **Dicts:** {'key': 'value'}, dict.keys()
• **Loops:** for i in range(10):, while True:
• **Functions:** def func(args): return value
• **Classes:** class ClassName: pass
• **Import:** import module_name

💡 Ask me to generate specific code templates!
""",
            },
            "javascript": {
                "name": "JavaScript",
                "version": "ES6+",
                "extensions": [".js", ".mjs"],
                "info": """
🟨 **JavaScript Information:**

• **Extensions:** .js, .mjs
• **Comment:** // single line, /* multi-line */
• **Variables:** let x = 10, const PI = 3.14
• **Arrays:** [1, 2, 3], arr.push(), arr[0]
• **Objects:** {key: 'value'}, obj.property
• **Loops:** for (let i=0; i<n; i++), arr.forEach()
• **Functions:** function name() {}, const name = () => {}
• **Classes:** class Name { constructor() {} }
• **Import:** import { name } from 'module'

💡 Ask me to generate specific code templates!
""",
            },
            "html": {
                "name": "HTML",
                "version": "HTML5",
                "extensions": [".html", ".htm"],
                "info": """
🌐 **HTML Information:**

• **Extensions:** .html, .htm
• **Basic Structure:**
```html
<!DOCTYPE html>
<html>
<head><title>Page Title</title></head>
<body>
    <h1>Heading</h1>
    <p>Paragraph</p>
</body>
</html>
```
• **Elements:** div, span, p, a, img, ul, li, table
• **Forms:** <form>, <input>, <button>, <select>

💡 Ask me to generate specific HTML templates!
""",
            },
            "css": {
                "name": "CSS",
                "version": "CSS3",
                "extensions": [".css"],
                "info": """
🎨 **CSS Information:**

• **Extensions:** .css
• **Selectors:** element, .class, #id
• **Properties:** color, margin, padding, display
• **Flexbox:** display: flex
• **Grid:** display: grid
• **Responsive:** @media queries

💡 Ask me to generate specific CSS templates!
""",
            },
            "sql": {
                "name": "SQL",
                "version": "SQL92+",
                "extensions": [".sql"],
                "info": """
🗄️ **SQL Information:**

• **Extensions:** .sql
• **Select:** SELECT columns FROM table WHERE condition
• **Insert:** INSERT INTO table (cols) VALUES (values)
• **Update:** UPDATE table SET col=value WHERE condition
• **Delete:** DELETE FROM table WHERE condition
• **Create:** CREATE TABLE table_name (...)

💡 Ask me to generate specific SQL queries!
""",
            },
        }
        
        lang_key = language.lower()
        if lang_key in language_info:
            return language_info[lang_key]["info"]
        
        return f"❌ Language not recognized: {language}\n\nSupported languages:\n" + \
               "\n".join([f"• {lang}" for lang in language_info.keys()])


# -# --- TOOL MAP ---
# Maps tool names to their functions for the agent to use

# Create a single instance of AgentTools
AGENT_TOOLS = AgentTools()

# Maps tool names to their functions for the agent to use
TOOL_MAP: Dict[str, Any] = {
    # Date/Time
    "get_datetime": AGENT_TOOLS.get_datetime,
    "save_session": AGENT_TOOLS.save_session,
    "load_session": AGENT_TOOLS.load_session,
    # System Commands
    "run_powershell": AGENT_TOOLS.run_powershell,
    "run_command": AGENT_TOOLS.run_command,
    
    # Web & Search
    "web_search": AGENT_TOOLS.web_search,
    "get_weather": AGENT_TOOLS.get_weather,
    "get_ip_info": AGENT_TOOLS.get_ip_info,
    "open_web": AGENT_TOOLS.open_web,
     "local_html_file": AGENT_TOOLS.local_html_file,
    
    # System Info
    "get_system_info": AGENT_TOOLS.get_system_info,
    "get_uptime": AGENT_TOOLS.get_uptime,
    "get_battery_status": AGENT_TOOLS.get_battery_status,
    "get_cpu_info": AGENT_TOOLS.get_cpu_info,
    "get_memory_info": AGENT_TOOLS.get_memory_info,
    
    # Disk & Files
    "list_files": AGENT_TOOLS.list_files,
    "read_file": AGENT_TOOLS.read_file,
    "read_file_lines": AGENT_TOOLS.read_file_lines,
    "write_file": AGENT_TOOLS.write_file,
    "get_file_info": AGENT_TOOLS.get_file_info,
    "get_disk_usage": AGENT_TOOLS.get_disk_usage,
    "search_files": AGENT_TOOLS.search_files,
    "delete_file": AGENT_TOOLS.delete_file,
    "confirm_delete": AGENT_TOOLS.confirm_delete,
    "create_folder": AGENT_TOOLS.create_folder,
    "copy_file": AGENT_TOOLS.copy_file,
    "move_file": AGENT_TOOLS.move_file,
    "rename_file": AGENT_TOOLS.rename_file,
    "get_file_hash": AGENT_TOOLS.get_file_hash,
    
    # PowerShell Windows Admin Tools
    "ps_get_services": AGENT_TOOLS.ps_get_services,
    "ps_service_action": AGENT_TOOLS.ps_service_action,
    "ps_get_eventlog": AGENT_TOOLS.ps_get_eventlog,
    "ps_get_processes_detailed": AGENT_TOOLS.ps_get_processes_detailed,
    "ps_get_registry": AGENT_TOOLS.ps_get_registry,
    "ps_get_scheduled_tasks": AGENT_TOOLS.ps_get_scheduled_tasks,
    "ps_get_installed_programs": AGENT_TOOLS.ps_get_installed_programs,
    "ps_get_environment_vars": AGENT_TOOLS.ps_get_environment_vars,
    "ps_get_network_adapters": AGENT_TOOLS.ps_get_network_adapters,
    "ps_get_firewall_rules": AGENT_TOOLS.ps_get_firewall_rules,
    "ps_get_disk_partitions": AGENT_TOOLS.ps_get_disk_partitions,
    "ps_get_wifi_networks": AGENT_TOOLS.ps_get_wifi_networks,
    "ps_get_hotfixes": AGENT_TOOLS.ps_get_hotfixes,
    "ps_get_running_tasks": AGENT_TOOLS.ps_get_running_tasks,
    "ps_get_systeminfo": AGENT_TOOLS.ps_get_systeminfo,
        # Program Installation/Uninstallation
    "search_program": AGENT_TOOLS.search_program,
    "validate_program_safety": AGENT_TOOLS.validate_program_safety,
    "get_installed_programs_list": AGENT_TOOLS.get_installed_programs_list,
    "check_program_removable": AGENT_TOOLS.check_program_removable,
    "prepare_install_command": AGENT_TOOLS.prepare_install_command,
    "prepare_uninstall_command": AGENT_TOOLS.prepare_uninstall_command,
    "execute_install": AGENT_TOOLS.execute_install,
    "execute_uninstall": AGENT_TOOLS.execute_uninstall,
    
    # Program Updates
    "check_program_updates": AGENT_TOOLS.check_program_updates,
    "validate_update_safety": AGENT_TOOLS.validate_update_safety,
    "prepare_update_command": AGENT_TOOLS.prepare_update_command,
    "execute_update": AGENT_TOOLS.execute_update,
    
    # Agent Self-Protection
    "validate_self_protection": AGENT_TOOLS.validate_self_protection,
    "get_agent_info": AGENT_TOOLS.get_agent_info,
    
    # System Control (Shutdown/Restart)
    "shutdown_computer": AGENT_TOOLS.shutdown_computer,
    "prepare_shutdown": AGENT_TOOLS.prepare_shutdown,
    "execute_shutdown": AGENT_TOOLS.execute_shutdown,
    "restart_computer": AGENT_TOOLS.restart_computer,
    "execute_restart": AGENT_TOOLS.execute_restart,
    "sleep_computer": AGENT_TOOLS.sleep_computer,
    
    # Coding Tools
    "execute_code": AGENT_TOOLS.execute_code,
    "run_file": AgentTools.run_file,
    "create_code_file": AGENT_TOOLS.create_code_file,
    "generate_code_template": AGENT_TOOLS.generate_code_template,
    "check_code_syntax": AGENT_TOOLS.check_code_syntax,
    "get_code_snippet_info": AGENT_TOOLS.get_code_snippet_info,
    
    # Calculator
    "calculate": AGENT_TOOLS.calculate,
    
    # Network
    "ping_host": AGENT_TOOLS.ping_host,
    "check_port": AGENT_TOOLS.check_port,
    "dns_lookup": AGENT_TOOLS.dns_lookup,
    "get_network_info": AGENT_TOOLS.get_network_info,
    
    # File System Navigation
    "get_current_directory": AGENT_TOOLS.get_current_directory,
    "change_directory": AGENT_TOOLS.change_directory,
    
    # Security
    "generate_password": AGENT_TOOLS.generate_password,
    
    # Process Management
    "get_processes": AGENT_TOOLS.get_processes,
    "kill_process": AGENT_TOOLS.kill_process,
    
    # Clipboard
    "get_clipboard": AGENT_TOOLS.get_clipboard,
    "set_clipboard": AGENT_TOOLS.set_clipboard,
}
SYSTEM_PROMPT = r"""You are a helpful AI Agent. 
### TOOL DEFINITIONS ###
1. create_code_file: Use this to SAVE code or HTML to the PERFECT folder.
2. local_html_file: Use this ONLY for .html files. It opens them in the browser via http://localhost:8000.
3. run_file: Use this to execute Python (.py), Java, C++, or other scripts.
4. read_file: Use ONLY to see the source code text. DO NOT use this to "open" or "view" a page for the user.

### CRITICAL RULES ###
- If a user says "Open [filename].html", you MUST use 'local_html_file' to serve it via HTTP.
- If a user says "Open [filename].py", you MUST use 'run_file' to execute the script.
- NEVER use 'read_file' when the user wants to "view" a GUI or a web page.
- BASE FOLDER: C:\Users\RAJAB BAIG\Documents\GitHub\BAIG\PERFECT

### COMMAND STRUCTURE ###
THOUGHT: <your reasoning>
ACTION: <tool_name>
ARGS: {"filepath": "filename.ext", "content": "CLEAN_CODE_HERE"}

### SAVING & RUNNING RULES ###
1. ALWAYS save code or HTML using 'create_code_file' before trying to open it.
2. Ensure the "content" argument in 'create_code_file' contains ONLY raw code (no JSON wrappers).
3. After saving an HTML file, immediately use 'local_html_file' to display it.
4. After saving a Python file, immediately use 'run_file' to execute it.

### EXAMPLES ###

USER: Create a hello world HTML and show me.
THOUGHT: I will save the HTML first and then use the local_html_file tool to open it via http.
ACTION: create_code_file
ARGS: {"filepath": "hello.html", "content": "<html><body><h1>Hello!</h1></body></html>"}
THOUGHT: Now I will serve it via local HTTP.
ACTION: local_html_file
ARGS: {"filepath": "hello.html"}

USER: open MYRAJAB.html
THOUGHT: The user wants to view a local HTML file. I will use 'local_html_file' to open it in the browser via http.
ACTION: local_html_file
ARGS: {"filepath": "MYRAJAB.html"}

USER: run my_script.py
THOUGHT: The user wants to execute a Python script. I will use 'run_file'.
ACTION: run_file
ARGS: {"filepath": "my_script.py"}
# --- WEB SEARCH & INFO (Priority: Tavily API) ---
- web_search: Search the web. Args: {"query": "string"}
- get_weather: Get weather info. Args: {"location": "string"}
- open_web: Open a URL. Args: {"url": "string"}
- get_datetime: Get date/time. Args: {"format_type": "default/date/time/iso/unix/day/full"}

# --- CODING TOOLS ---
- execute_code: Run code. Args: {"code": "string", "language": "python/javascript/bash"}
- create_code_file: Create file. Args: {"filepath": "string", "content": "string"}
- generate_code_template: Templates. Args: {"task": "string", "language": "python"}
CRITICAL: Use '\\n' for new lines in "code" values. Do not include 'code=' labels in the string.

# --- FILE & DISK MANAGEMENT ---
- list_files: List folder contents. Args: {"path": "string", "pattern": "*", "include_hidden": false}
- read_file: Read file. Args: {"filepath": "string", "max_lines": null, "encoding": "utf-8"}
- write_file: Write/Append file. Args: {"filepath": "string", "content": "string", "append": false}
- get_file_info: Get file details. Args: {"filepath": "string"}
- create_folder: Create directory. Args: {"folderpath": "string"}
- copy_file: Copy. Args: {"source": "string", "destination": "string"}
- move_file: Move. Args: {"source": "string", "destination": "string"}
- rename_file: Rename. Args: {"oldpath": "string", "newname": "string"}
- delete_file: Request deletion. Args: {"filepath": "string"}
- get_disk_usage: Disk space. Args: {"path": "C:\\\\"}

# --- SYSTEM & WINDOWS ADMIN ---
- run_command: Execute CMD. Args: {"command": "string"}
- run_powershell: Execute PS. Args: {"command": "string"}
- ps_get_services: Windows services. Args: {"status": "all/running/stopped"}
- ps_service_action: Control service. Args: {"service_name": "string", "action": "start/stop/restart"}
- ps_get_installed_programs: List programs. ARGS: {}
- ps_get_systeminfo: System details. ARGS: {}

# --- PROGRAM MANAGEMENT (Install/Uninstall/Update) ---
- search_program: Find official source. Args: {"program_name": "string"}
- execute_install: Install program. Args: {"program_name": "string", "download_url": "string"}
- execute_uninstall: Uninstall program. Args: {"program_name": "string", "uninstall_string": "string"}
- check_program_updates: Check for updates. Args: {"program_name": "string"}

# --- SAFETY & SELF-PROTECTION RULES ---
1. CONFIRMATION: ALWAYS ask user for confirmation BEFORE deleting files, shutting down, or installing software.
2. PROTECTION: You CANNOT modify or delete: agent.py, requirements.txt, .venv, or ollama processes.
3. FALLBACK: If a tool fails or you lack data, ALWAYS use web_search (Tavily).
4. DELETE RULES: You cannot delete non-empty folders or system directories (Windows, System32).

# --- NETWORK & PROCESSES ---
- ping_host: Ping. Args: {"host": "string", "count": 4}
- get_ip_info: Public IP. ARGS: {}
- get_processes: List processes. ARGS: {}
- kill_process: Kill by name. Args: {"name": "string"}
- set_clipboard: Copy to clipboard. Args: {"text": "string"}

# --- RESPONSE FORMAT ---
Be concise. Once you find the answer in the search results, provide the Final Answer immediately. Do not perform redundant searches if the information is already present in the history.If you have the answer, say:
FINAL ANSWER: <your answer>

If writing a poem, story, or simple greeting, reply directly without tool calls.
"""
import re
import datetime
import webbrowser
import customtkinter as ctk

# NOTE: This file assumes TOOL_MAP and AgentTools are defined elsewhere in your project.

# --- REQUIRED IMPORTS ---
import webbrowser
import datetime
import re
import threading
import customtkinter as ctk
# ------------------------

class AgentGUI(ctk.CTk):
    """Main GUI application for the AI Agent."""
    
    # ==================== Helper Methods ====================
    
    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.append_chat("System", "Chat cleared!", tag="timestamp")
    
    def copy_output(self):
        """Copy entire chat history to clipboard."""
        content = self.chat_display.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()
        self.append_chat("System", "Chat copied to clipboard!", tag="success")
    
    def copy_last_response(self):
        """Copy only the last AI response."""
        content = self.chat_display.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()
        self.append_chat("System", "Last response copied!", tag="success")
    
    def clear_input(self):
        """Clear the input field."""
        self.user_input.delete("1.0", "end")
    
    def set_prompt(self, prompt):
        """Set the input field with a quick prompt."""
        self.user_input.delete("1.0", "end")
        self.user_input.insert("1.0", prompt)
        self.user_input.focus()
    
    def update_status(self, status):
        """Update the status label."""
        self.status_label.configure(text=f"Status: {status}")
    
    def set_status(self, text: str, color: str = "white"):
        """Thread-safe status update."""
        self.after(0, lambda: self.status_label.configure(text=f"Status: {text}", text_color=color))

    def set_button_state(self, enabled: bool):
        """Enable or disable the send button and toggle stop button."""
        state = "normal" if enabled else "disabled"
        self.is_processing = not enabled
        def _update():
            self.send_btn.configure(state=state)
            if not enabled:
                self.stop_btn.grid()
                self.send_btn.grid_remove()
            else:
                self.stop_btn.grid_remove()
                self.send_btn.grid()
        self.after(0, _update)

    # ---------------- Safe tag helpers ----------------
    def safe_tag_config(self, tag: str, **options):
        """Safely configure a text tag (works with Tk Text, ignores CTkTextbox)."""
        try:
            if hasattr(self.chat_display, "tag_config"):
                self.chat_display.tag_config(tag, **options)
            elif hasattr(self.chat_display, "tag_configure"):
                self.chat_display.tag_configure(tag, **options)
        except Exception:
            pass

    def safe_tag_bind(self, tag: str, sequence: str, func):
        """Safely bind an event to a text tag."""
        try:
            self.chat_display.tag_bind(tag, sequence, func)
        except Exception:
            pass

    # ==================== CORE CHAT DISPLAY ====================
    
    def append_chat(self, sender: str, text: str, tag: str = None):
        """Add a message to the chat display with clickable URLs."""
        # Fix: Convert to string and ensure it's captured before the nested function
        message_text = str(text) if text is not None else ""
         # --- ADD THIS LOGIC HERE ---
        # Record the message in history for the JSON session file
        self.chat_history.append({
            "sender": sender,
            "text": message_text,
            "tag": tag,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        def _update():
            self.chat_display.configure(state="normal")
            timestamp = datetime.datetime.now().strftime("%H:%M")
            
            # Determine tag based on sender
            if sender == "You":
                msg_tag = "you"
            elif sender == "Agent":
                msg_tag = "agent"
            elif sender == "Error":
                msg_tag = "error"
            elif sender == "Tool":
                msg_tag = "tool_call"
            else:
                msg_tag = tag or "normal"
            
            # Insert timestamp
            try:
                self.chat_display.insert("end", f"[{timestamp}] ", "timestamp")
            except Exception:
                self.chat_display.insert("end", f"[{timestamp}] ")
            
            # Insert sender label
            try:
                self.chat_display.insert("end", f"{sender.upper()}: ", msg_tag)
            except Exception:
                self.chat_display.insert("end", f"{sender.upper()}: ")
            
            # Parse message_text for URLs and make them clickable
            # Regex matches http(s)://... or www....
            url_pattern = re.compile(r'(https?://[^\s\)"\']+|www\.[^\s\)"\']+)')
            last_end = 0
            
            for match in url_pattern.finditer(message_text):
                # Insert text before URL with sender's tag (color)
                before_url = message_text[last_end:match.start()]
                if before_url:
                    try:
                        self.chat_display.insert("end", before_url, msg_tag)
                    except Exception:
                        self.chat_display.insert("end", before_url)
                
                # Insert clickable URL
                raw_url = match.group(0)
                # Ensure URL has scheme for browser
                url = raw_url if raw_url.startswith(('http://', 'https://')) else f"https://{raw_url}"
                
                start_index = self.chat_display.index("end-1c")
                self.chat_display.insert("end", raw_url)
                end_index = self.chat_display.index(f"{start_index}+{len(raw_url)}c")
                
                # Create UNIQUE tag for this specific link
                link_tag = f"url_{self._url_counter}"
                self._url_counter += 1
                self._url_registry[link_tag] = url
                
                # Style: Blue, Underline, Hand Cursor (via tag)
                self.safe_tag_config(link_tag, foreground="#4da6ff", underline=True, cursor="hand2")
                # Bind click event
                self.safe_tag_bind(link_tag, "<Button-1>", lambda e, u=url: self.open_url(u))
                
                last_end = match.end()
            
            # Insert remaining text with sender's tag
            remaining = message_text[last_end:]
            if remaining:
                try:
                    self.chat_display.insert("end", remaining, msg_tag)
                except Exception:
                    self.chat_display.insert("end", remaining)
            
            self.chat_display.insert("end", "\n\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")
            
        self.after(0, _update)
    def open_url(self, url: str):
        """Open URL in default browser."""
        try:
            if not url.startswith(('http://', 'https://')):
                url = "https://" + url
            webbrowser.open(url, new=2) # new=2 opens in new tab
            self.set_status(f"Opened: {url}", "cyan")
        except Exception as e:
            self.append_chat("System", f"Error opening URL: {str(e)}", tag="error")

    # ==================== __init__ ====================
    
    def __init__(self):
        super().__init__()
        self.title("Agentic AI - Local LLM Assistant")
        self.geometry("1100x800")
        
        # Appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Agent state
        self.is_processing = False
        self.should_stop = False
        # Add this line to track data for JSON saving
        self.chat_history = [] 
        
        # Link the GUI to your AGENT_TOOLS instance
        AGENT_TOOLS.gui = self
        # --- URL TRACKING FOR CLICKABLE LINKS ---
        self._url_counter = 0
        self._url_registry = {}
        # -----------------------------------------
        
        # Configure grid - 3 columns: main content, buttons
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ===== LEFT SIDE: Main content area =====
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=0)
        self.main_frame.grid_rowconfigure(2, weight=0)
        
        # Chat display with scrollbar
        self.chat_frame = ctk.CTkFrame(self.main_frame)
        self.chat_frame.grid(row=0, column=0, padx=(10, 10), pady=(10, 5), sticky="nsew")
        self.chat_frame.grid_columnconfigure(0, weight=1)
        self.chat_frame.grid_rowconfigure(0, weight=1)
        
        self.chat_display = ctk.CTkTextbox(
            self.chat_frame,
            font=("Consolas", 14),
            wrap="word",
            state="disabled"
        )
        self.chat_display.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        
        # Scrollbar for chat
        self.chat_scrollbar = ctk.CTkScrollbar(self.chat_frame, command=self.chat_display.yview)
        self.chat_scrollbar.grid(row=0, column=1, padx=0, pady=0, sticky="ns")
        self.chat_display.configure(yscrollcommand=self.chat_scrollbar.set)
        
        # Configure text tags for styling (safe)
        self.safe_tag_config("timestamp", foreground="gray")
        self.safe_tag_config("tool_call", foreground="cyan")
        self.safe_tag_config("error", foreground="#ff6b6b")
        self.safe_tag_config("success", foreground="#51cf66")
        self.safe_tag_config("you", foreground="#74c0fc")
        self.safe_tag_config("agent", foreground="#ffd43b")
        
        # Status bar
        self.status_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.status_frame.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Status: Ready",
            text_color="gray",
            font=("Arial", 12, "italic")
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        
        self.tools_label = ctk.CTkLabel(
            self.status_frame,
            text=f"Tools: {len(TOOL_MAP)}",
            text_color="gray",
            font=("Arial", 10)
        )
        self.tools_label.grid(row=0, column=0, sticky="e")
        
        # Input frame
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        # Input field with scrollbar
        self.input_scroll_frame = ctk.CTkFrame(self.input_frame)
        self.input_scroll_frame.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")
        self.input_scroll_frame.grid_columnconfigure(0, weight=1)
        
        self.user_input = ctk.CTkTextbox(
            self.input_scroll_frame,
            height=80,
            font=("Arial", 13),
            wrap="word",
            activate_scrollbars=False
        )
        self.user_input.grid(row=0, column=0, sticky="ew")
        
        self.input_scrollbar = ctk.CTkScrollbar(self.input_scroll_frame, command=self.user_input.yview)
        self.input_scrollbar.grid(row=0, column=1, padx=0, pady=0, sticky="ns")
        self.user_input.configure(yscrollcommand=self.input_scrollbar.set)
        # ===== RIGHT SIDE: Buttons =====
        self.buttons_frame = ctk.CTkFrame(self, width=120)
        self.buttons_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.buttons_frame.grid_columnconfigure(0, weight=1)

        # --- 1. DEFINE DATA FIRST (Fixes the AttributeError) ---
        self.quick_prompts = [
            ("📅 Today", "what day and date is today?"),
            ("🌤️ Weather", "what's the weather in Attock Pakistan?"),
            ("💻 System", "give me my window PC info"),
            ("📁 Files", "list files in directory path="),
        ]

        # --- 2. LAYOUT BUTTONS ---

        # Row 0: Spacer at top
        spacer_top = ctk.CTkLabel(self.buttons_frame, text="")
        spacer_top.grid(row=0, pady=(0, 10))
        
        # Row 1: Send / Stop
        self.send_btn = ctk.CTkButton(
            self.buttons_frame, text="Send ➤", command=self.handle_send,
            width=100, height=45, font=("Arial", 13, "bold")
        )
        self.send_btn.grid(row=1, padx=10, pady=5)
        
        self.stop_btn = ctk.CTkButton(
            self.buttons_frame, text="■ Stop", command=self.stop_processing,
            width=100, height=45, font=("Arial", 13, "bold"),
            fg_color="#e74c3c", hover_color="#c0392b"
        )
        self.stop_btn.grid(row=1, padx=10, pady=5)
        self.stop_btn.grid_remove()

        # Row 2: Clear Chat
        self.clear_btn = ctk.CTkButton(
            self.buttons_frame, text="Clear Chat", command=self.clear_chat,
            width=100, height=35
        )
        self.clear_btn.grid(row=2, padx=10, pady=5)
        
        # Row 3: Copy Output
        self.copy_btn = ctk.CTkButton(
            self.buttons_frame, text="Copy Output", command=self.copy_output,
            width=100, height=35
        )
        self.copy_btn.grid(row=3, padx=10, pady=5)
        
        # Row 4: Copy Last Response
        self.copy_last_btn = ctk.CTkButton(
            self.buttons_frame, text="Copy Last", command=self.copy_last_response,
            width=100, height=35
        )
        self.copy_last_btn.grid(row=4, padx=10, pady=5)
        
        # Row 5: Clear Input
        self.clear_input_btn = ctk.CTkButton(
            self.buttons_frame, text="Clear Input", command=self.clear_input,
            width=100, height=35
        )
        self.clear_input_btn.grid(row=5, padx=10, pady=5)

        # Row 6: Save Session (Green)
        self.save_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Save Session",
            command=self.handle_save,
            width=100,
            height=40,
            fg_color="#27ae60",
            hover_color="#1e8449"
        )
        self.save_btn.grid(row=6, padx=10, pady=10)
        
        # Row 7: Load Session (Blue)
        self.load_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Load Session",
            command=self.handle_load,
            width=100,
            height=40,
            fg_color="#2980b9",
            hover_color="#1f618d"
        )
        self.load_btn.grid(row=7, padx=10, pady=5)
        
        # Row 8: Spacer
        spacer_mid = ctk.CTkLabel(self.buttons_frame, text="")
        spacer_mid.grid(row=8, pady=(10, 0))
        
        # Row 9: Quick Prompts Label
        prompts_label = ctk.CTkLabel(
            self.buttons_frame, text="Quick Prompts", font=("Arial", 11, "bold")
        )
        prompts_label.grid(row=9, pady=(0, 5))
        
        # Row 10+: Quick Prompts Loop
        for i, (label, prompt) in enumerate(self.quick_prompts):
            btn = ctk.CTkButton(
                self.buttons_frame, text=label,
                command=lambda p=prompt: self.set_prompt(p),
                width=100, height=32
            )
            btn.grid(row=10 + i, padx=10, pady=3)
        
        # Welcome message
        self.append_chat("System", f"Welcome! I'm your AI Agent.\n\nI have {len(TOOL_MAP)} tools available:\n" +
                        "• System info & monitoring\n• File operations\n• Network tools\n" +
                        "• Web search\n• Calculator\n• Open Web URLs\n\n" +
                        "Type your question or task below!", tag="success")

    # ==================== EVENT HANDLERS ====================
    
    def handle_send(self):
        """Handle user input and start agent thread."""
        query = self.user_input.get("1.0", "end").strip()
        if not query:
            return
        
        self.append_chat("You", query)
        self.user_input.delete("1.0", "end")
        self.should_stop = False  # Reset stop flag
        self.set_button_state(False)
        threading.Thread(target=self.run_agent_thread, args=(query,), daemon=True).start()
    
    def handle_save(self):
        """Invoke the Brain to save the session history."""
        from tkinter import filedialog
        try:
            # FIX: Changed 'initialfilename' to 'initialfile'
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile=f"session_{datetime.datetime.now().strftime('%H%M%S')}.json",
                title="Save Mr. Perfect's Session"
            )
            
            if path:
                # Call the tool to perform the actual file writing
                result = AGENT_TOOLS.save_session(path)
                self.append_chat("System", result, tag="success")
                self.set_status("Session Saved Successfully", "green")
        except Exception as e:
            self.append_chat("Error", f"Save failed: {str(e)}", tag="error")
    def handle_load(self):
        """Restore history into the chat display safely and instantly."""
        from tkinter import filedialog
        try:
            path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                title="Load Session"
            )
            if not path:
                return

            # 1. Clear UI and internal memory first
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", "end")
            self.chat_history = [] 
            
            # 2. Use the tool to load JSON data into self.chat_history
            res = AGENT_TOOLS.load_session(path)
            
            # 3. THE LOOP: Display each message from the loaded list
            # We use _render_history_item to avoid the 'append' loop freeze
            for msg in self.chat_history:
                self._render_history_item(
                    msg.get('sender', 'System'), 
                    msg.get('text', ''), 
                    msg.get('tag'),
                    msg.get('timestamp')
                )
            
            # 4. Show success message
            self.append_chat("System", res, tag="success")
            self.set_status("Session Loaded Successfully", "cyan")

        except Exception as e:
            self.append_chat("Error", f"Load failed: {str(e)}", tag="error")
    def _render_history_item(self, sender, text, tag, timestamp=None):
        """Helper to draw text on UI WITHOUT re-saving to the history list."""
        self.chat_display.configure(state="normal")
        
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%H:%M")
            
        # Match your existing logic for sender tags
        if sender == "You":
            msg_tag = "you"
        elif sender == "Agent":
            msg_tag = "agent"
        elif sender == "Tool":
            msg_tag = "tool_call"
        elif sender == "Error":
            msg_tag = "error"
        else:
            msg_tag = tag or "normal"
            
        # Insert timestamp and sender
        self.chat_display.insert("end", f"[{timestamp}] ", "timestamp")
        self.chat_display.insert("end", f"{sender.upper()}: ", msg_tag)
        
        # Insert message body
        self.chat_display.insert("end", f"{text}\n\n")
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
    def stop_processing(self):
        """Stop the current agent processing."""
        self.should_stop = True
        self.set_status("Stopping...", "orange")
        self.append_chat("System", "⏹️ Processing stopped by user.", tag="error")

    # ==================== AGENT LOGIC (run_agent_thread) ====================
    # PASTE YOUR FULL 'run_agent_thread' METHOD HERE FROM THE BOTTOM OF YOUR FILE
    # (The one that handles TOOL_MAP, confirmations, LLM loop, etc.)
    # 
    # Example structure:
    #
    # def run_agent_thread(self, user_prompt: str):
    #     self.set_status("Thinking...", "yellow")
    #     messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}]
    #     # ... your loop logic ...
    #     # ... your tool calling logic ...
    #     # ... your confirmation dialog calls (show_delete_confirmation, etc.) ...
    
    # ==================== CONFIRMATION DIALOGS ====================
    # PASTE ALL YOUR CONFIRMATION DIALOG METHODS HERE:
    # - show_delete_confirmation
    # - show_install_confirmation
    # - show_uninstall_confirmation
    # - show_update_confirmation
    # - show_shutdown_confirmation
    # - show_restart_confirmation
    # - format_delete_info
    # - get_chat_content, get_last_response, copy_to_clipboard
    
    # (I have omitted the full 500 lines of dialogs/agent-loop for brevity, 
    # but you MUST paste your existing implementations of those methods below this line)


# --- MAIN ENTRY POINT ---

    def show_delete_confirmation(self, delete_info: str):
        """Show a confirmation dialog for delete operations."""
        parts = delete_info.replace("CONFIRM_DELETE:", "").split("|")
        path = parts[0]
        item_type = parts[1].split(":")[0] if len(parts) > 1 else "unknown"
        item_name = parts[1].split(":")[1] if len(parts) > 1 else "unknown"
        size = parts[2].replace("SIZE:", "") if len(parts) > 2 and parts[2].startswith("SIZE:") else ""
        
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚠️ Confirm Delete")
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # Make it modal
        dialog.focus()
        
        # Warning icon and title
        title_label = ctk.CTkLabel(
            dialog,
            text="⚠️ DELETE CONFIRMATION REQUIRED",
            font=("Arial", 16, "bold"),
            text_color="#e74c3c"
        )
        title_label.pack(pady=(20, 10))
        
        # Info frame
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        type_label = ctk.CTkLabel(info_frame, text=f"Type: {item_type}", font=("Arial", 12))
        type_label.pack(anchor="w", pady=2)
        
        name_label = ctk.CTkLabel(info_frame, text=f"Name: {item_name}", font=("Arial", 12, "bold"))
        name_label.pack(anchor="w", pady=2)
        
        path_label = ctk.CTkLabel(info_frame, text=f"Path: {path}", font=("Arial", 10))
        path_label.pack(anchor="w", pady=2)
        
        if size:
            size_label = ctk.CTkLabel(info_frame, text=f"Size: {int(size):,} bytes", font=("Arial", 11))
            size_label.pack(anchor="w", pady=2)
        
        # Warning message
        warning = ctk.CTkLabel(
            dialog,
            text="This action cannot be undone!",
            font=("Arial", 12, "italic"),
            text_color="orange"
        )
        warning.pack(pady=10)
        
        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        result = {"confirmed": False}
        
        def on_confirm():
            result["confirmed"] = True
            dialog.destroy()
            # Actually perform the deletion
            delete_result = AgentTools.confirm_delete(path)
            self.append_chat("System", delete_result, tag="success" if "✅" in delete_result else "error")
        
        def on_cancel():
            dialog.destroy()
            self.append_chat("System", "❌ Delete operation cancelled by user.", tag="error")
        
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️ DELETE",
            command=on_confirm,
            width=120,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        confirm_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖ Cancel",
            command=on_cancel,
            width=120,
            height=40
        )
        cancel_btn.pack(side="left", padx=10)
        
        # Wait for dialog to close
        self.wait_window(dialog)
    
    def show_install_confirmation(self, install_info: str):
        """Show a confirmation dialog for program installation."""
        parts = install_info.replace("CONFIRM_INSTALL:", "").split("|")
        program_name = parts[0].replace("URL:", "") if parts[0] else "Unknown"
        download_url = ""
        status = "VERIFY_NEEDED"
        warning = ""
        
        for part in parts:
            if part.startswith("URL:"):
                download_url = part.replace("URL:", "")
            elif part.startswith("STATUS:"):
                status = part.replace("STATUS:", "")
            elif part.startswith("WARNING:"):
                warning = part.replace("WARNING:", "")
        
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚠️ Confirm Installation")
        dialog.geometry("550x400")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus()
        
        # Warning icon and title
        title_label = ctk.CTkLabel(
            dialog,
            text="⚠️ INSTALLATION CONFIRMATION REQUIRED",
            font=("Arial", 16, "bold"),
            text_color="#e67e22"
        )
        title_label.pack(pady=(20, 10))
        
        # Safety status
        if "SAFE" in status:
            safety_color = "#27ae60"
            safety_text = "✅ SAFETY CHECK: PASSED"
        elif warning:
            safety_color = "#f39c12"
            safety_text = f"⚠️ WARNING: {warning}"
        else:
            safety_color = "#e74c3c"
            safety_text = "❌ VERIFICATION NEEDED"
        
        safety_label = ctk.CTkLabel(
            dialog,
            text=safety_text,
            font=("Arial", 12, "bold"),
            text_color=safety_color
        )
        safety_label.pack(pady=5)
        
        # Info frame
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        name_label = ctk.CTkLabel(info_frame, text=f"Program: {program_name}", font=("Arial", 13, "bold"))
        name_label.pack(anchor="w", pady=2)
        
        url_label = ctk.CTkLabel(info_frame, text=f"URL:\n{download_url}", font=("Arial", 10), wraplength=500)
        url_label.pack(anchor="w", pady=2)
        
        # Safety info
        safety_info = ctk.CTkLabel(
            dialog,
            text="📋 Safety Info:\n" +
                 "• Always download from official sources\n" +
                 "• Review permissions during installation\n" +
                 "• Close other programs before installing\n" +
                 "• Restart computer if prompted",
            font=("Arial", 10),
            text_color="gray",
            justify="left"
        )
        safety_info.pack(pady=10)
        
        # Warning message
        warning_msg = ctk.CTkLabel(
            dialog,
            text="⚠️ This action cannot be undone!",
            font=("Arial", 12, "italic"),
            text_color="orange"
        )
        warning_msg.pack(pady=10)
        
        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_confirm():
            dialog.destroy()
            try:
                self.update_status("Installing...")
            except Exception:
                pass
            self.append_chat("System", f"📥 Installing {program_name}...", tag="warning")
            install_result = AgentTools.execute_install(program_name, download_url)
            self.append_chat("System", install_result, tag="success" if "✅" in install_result else "error")
            try:
                self.update_status("Ready")
            except Exception:
                pass
        
        def on_cancel():
            dialog.destroy()
            self.append_chat("System", "❌ Installation cancelled by user.", tag="error")
        
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="📥 INSTALL",
            command=on_confirm,
            width=120,
            height=40,
            fg_color="#27ae60",
            hover_color="#219a52"
        )
        confirm_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖ Cancel",
            command=on_cancel,
            width=120,
            height=40
        )
        cancel_btn.pack(side="left", padx=10)
        
        self.wait_window(dialog)
    
    def show_uninstall_confirmation(self, uninstall_info: str):
        """Show a confirmation dialog for program uninstallation."""
        parts = uninstall_info.replace("CONFIRM_UNINSTALL:", "").split("|")
        program_name = parts[0] if parts else "Unknown"
        uninstall_cmd = ""
        
        for part in parts:
            if part.startswith("CMD:"):
                uninstall_cmd = part.replace("CMD:", "")
        
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚠️ Confirm Uninstallation")
        dialog.geometry("550x350")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus()
        
        # Warning icon and title
        title_label = ctk.CTkLabel(
            dialog,
            text="⚠️ UNINSTALLATION CONFIRMATION REQUIRED",
            font=("Arial", 16, "bold"),
            text_color="#e74c3c"
        )
        title_label.pack(pady=(20, 10))
        
        # Safety warning
        safety_label = ctk.CTkLabel(
            dialog,
            text="✅ SAFETY CHECK: Program verified as safe to uninstall",
            font=("Arial", 11, "bold"),
            text_color="#27ae60"
        )
        safety_label.pack(pady=5)
        
        # Info frame
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        name_label = ctk.CTkLabel(info_frame, text=f"Program: {program_name}", font=("Arial", 13, "bold"))
        name_label.pack(anchor="w", pady=2)
        
        # Warning message
        warning = ctk.CTkLabel(
            dialog,
            text="⚠️ WARNING:\n" +
                 "• This will remove the program completely\n" +
                 "• User data may be deleted\n" +
                 "• You may need to restart your computer\n" +
                 "• This action cannot be undone!",
            font=("Arial", 11),
            text_color="orange",
            justify="left"
        )
        warning.pack(pady=10)
        
        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_confirm():
            dialog.destroy()
            try:
                self.update_status("Uninstalling...")
            except Exception:
                pass
            self.append_chat("System", f"🗑️ Uninstalling {program_name}...", tag="warning")
            uninstall_result = AgentTools.execute_uninstall(program_name, uninstall_cmd)
            self.append_chat("System", uninstall_result, tag="success" if "✅" in uninstall_result else "error")
            try:
                self.update_status("Ready")
            except Exception:
                pass
        
        def on_cancel():
            dialog.destroy()
            self.append_chat("System", "❌ Uninstallation cancelled by user.", tag="error")
        
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️ UNINSTALL",
            command=on_confirm,
            width=130,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        confirm_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖ Cancel",
            command=on_cancel,
            width=120,
            height=40
        )
        cancel_btn.pack(side="left", padx=10)
        
        self.wait_window(dialog)
    
    def show_update_confirmation(self, update_info: str):
        """Show a confirmation dialog for program updates."""
        parts = update_info.replace("CONFIRM_UPDATE:", "").split("|")
        program_name = ""
        download_url = ""
        status = "VERIFY_NEEDED"
        
        for part in parts:
            if part.startswith("URL:"):
                download_url = part.replace("URL:", "")
            elif part.startswith("STATUS:"):
                status = part.replace("STATUS:", "")
        
        # Extract program name from URL or use default
        if not program_name:
            program_name = parts[0] if parts else "Unknown Program"
        
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("🔄 Confirm Update")
        dialog.geometry("550x380")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus()
        
        # Warning icon and title
        title_label = ctk.CTkLabel(
            dialog,
            text="🔄 UPDATE CONFIRMATION",
            font=("Arial", 16, "bold"),
            text_color="#3498db"
        )
        title_label.pack(pady=(20, 10))
        
        # Info frame
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        name_label = ctk.CTkLabel(info_frame, text=f"Program: {program_name}", font=("Arial", 13, "bold"))
        name_label.pack(anchor="w", pady=2)
        
        url_label = ctk.CTkLabel(info_frame, text=f"URL:\n{download_url}", font=("Arial", 10), wraplength=500)
        url_label.pack(anchor="w", pady=2)
        
        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_confirm():
            dialog.destroy()
            try:
                self.update_status("Updating...")
            except Exception:
                pass
            self.append_chat("System", f"⬆️ Updating {program_name}...", tag="warning")
            update_result = AgentTools.execute_update(program_name, download_url)
            self.append_chat("System", update_result, tag="success" if "✅" in update_result else "error")
            try:
                self.update_status("Ready")
            except Exception:
                pass
        
        def on_cancel():
            dialog.destroy()
            self.append_chat("System", "❌ Update cancelled by user.", tag="error")
        
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="⬆️ UPDATE",
            command=on_confirm,
            width=120,
            height=40,
            fg_color="#3498db",
            hover_color="#2b86c6"
        )
        confirm_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖ Cancel",
            command=on_cancel,
            width=120,
            height=40
        )
        cancel_btn.pack(side="left", padx=10)
        
        self.wait_window(dialog)

    
    def show_uninstall_confirmation(self, uninstall_info: str):
        """Show a confirmation dialog for program uninstallation."""
        parts = uninstall_info.replace("CONFIRM_UNINSTALL:", "").split("|")
        program_name = parts[0] if parts else "Unknown"
        uninstall_cmd = ""
        
        for part in parts:
            if part.startswith("CMD:"):
                uninstall_cmd = part.replace("CMD:", "")
        
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚠️ Confirm Uninstallation")
        dialog.geometry("550x350")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus()
        
        # Warning icon and title
        title_label = ctk.CTkLabel(
            dialog,
            text="⚠️ UNINSTALLATION CONFIRMATION REQUIRED",
            font=("Arial", 16, "bold"),
            text_color="#e74c3c"
        )
        title_label.pack(pady=(20, 10))
        
        # Safety warning
        safety_label = ctk.CTkLabel(
            dialog,
            text="✅ SAFETY CHECK: Program verified as safe to uninstall",
            font=("Arial", 11, "bold"),
            text_color="#27ae60"
        )
        safety_label.pack(pady=5)
        
        # Info frame
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        name_label = ctk.CTkLabel(info_frame, text=f"Program: {program_name}", font=("Arial", 13, "bold"))
        name_label.pack(anchor="w", pady=2)
        
        # Warning message
        warning = ctk.CTkLabel(
            dialog,
            text="⚠️ WARNING:\n" +
                 "• This will remove the program completely\n" +
                 "• User data may be deleted\n" +
                 "• You may need to restart your computer\n" +
                 "• This action cannot be undone!",
            font=("Arial", 11),
            text_color="orange",
            justify="left"
        )
        warning.pack(pady=10)
        
        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_confirm():
            dialog.destroy()
            self.set_status("Uninstalling...", "orange")
            self.append_chat("System", f"🗑️ Uninstalling {program_name}...", tag="warning")
            uninstall_result = AgentTools.execute_uninstall(program_name, uninstall_cmd)
            self.append_chat("System", uninstall_result, tag="success" if "✅" in uninstall_result else "error")
            self.set_status("Ready", "gray")
        
        def on_cancel():
            dialog.destroy()
            self.append_chat("System", "❌ Uninstallation cancelled by user.", tag="error")
        
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️ UNINSTALL",
            command=on_confirm,
            width=130,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        confirm_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖ Cancel",
            command=on_cancel,
            width=120,
            height=40
        )
        cancel_btn.pack(side="left", padx=10)
        
        self.wait_window(dialog)
    
    def show_update_confirmation(self, update_info: str):
        """Show a confirmation dialog for program updates."""
        parts = update_info.replace("CONFIRM_UPDATE:", "").split("|")
        program_name = ""
        download_url = ""
        status = "VERIFY_NEEDED"
        
        for part in parts:
            if part.startswith("URL:"):
                download_url = part.replace("URL:", "")
            elif part.startswith("STATUS:"):
                status = part.replace("STATUS:", "")
        
        # Extract program name from URL or use default
        if not program_name:
            program_name = parts[0] if parts else "Unknown Program"
        
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("🔄 Confirm Update")
        dialog.geometry("550x380")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus()
        
        # Warning icon and title
        title_label = ctk.CTkLabel(
            dialog,
            text="🔄 UPDATE CONFIRMATION REQUIRED",
            font=("Arial", 16, "bold"),
            text_color="#3498db"
        )
        title_label.pack(pady=(20, 10))
        
        # Safety status
        if "SAFE" in status:
            safety_color = "#27ae60"
            safety_text = "✅ SAFETY CHECK: PASSED"
        elif "WARNING" in status:
            safety_color = "#f39c12"
            safety_text = f"⚠️ WARNING: {status}"
        else:
            safety_color = "#e74c3c"
            safety_text = "❌ VERIFICATION NEEDED"
        
        safety_label = ctk.CTkLabel(
            dialog,
            text=safety_text,
            font=("Arial", 12, "bold"),
            text_color=safety_color
        )
        safety_label.pack(pady=5)
        
        # Info frame
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        name_label = ctk.CTkLabel(info_frame, text=f"Program: {program_name}", font=("Arial", 13, "bold"))
        name_label.pack(anchor="w", pady=2)
        
        url_label = ctk.CTkLabel(info_frame, text=f"URL:\n{download_url}", font=("Arial", 10), wraplength=500)
        url_label.pack(anchor="w", pady=2)
        
        # Warning message
        warning_msg = ctk.CTkLabel(
            dialog,
            text="📋 Update Info:\n" +
                 "• This will update the program to the latest version\n" +
                 "• User data should be preserved\n" +
                 "• Close other programs before updating\n" +
                 "• Restart computer if prompted\n\n" +
                 "⚠️ This action cannot be undone!",
            font=("Arial", 11),
            text_color="orange",
            justify="left"
        )
        warning_msg.pack(pady=10)
        
        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_confirm():
            dialog.destroy()
            self.set_status("Updating...", "orange")
            self.append_chat("System", f"🔄 Updating {program_name}...", tag="warning")
            update_result = AgentTools.execute_update(program_name, download_url)
            self.append_chat("System", update_result, tag="success" if "✅" in update_result else "error")
            self.set_status("Ready", "gray")
        
        def on_cancel():
            dialog.destroy()
            self.append_chat("System", "❌ Update cancelled by user.", tag="error")
        
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 UPDATE",
            command=on_confirm,
            width=120,
            height=40,
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        confirm_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖ Cancel",
            command=on_cancel,
            width=120,
            height=40
        )
        cancel_btn.pack(side="left", padx=10)
        
        self.wait_window(dialog)
    
    def show_shutdown_confirmation(self, shutdown_info: str):
        """Show a confirmation dialog for system shutdown."""
        parts = shutdown_info.replace("CONFIRM_SHUTDOWN:", "").split("|")
        is_force = "FORCE" in parts[0] if parts else False
        
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚠️ Confirm Shutdown")
        dialog.geometry("500x380")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus()
        
        # Warning icon and title
        title_label = ctk.CTkLabel(
            dialog,
            text="⚠️ SYSTEM SHUTDOWN",
            font=("Arial", 18, "bold"),
            text_color="#e74c3c"
        )
        title_label.pack(pady=(20, 10))
        
        # Warning icon
        warning_icon = ctk.CTkLabel(
            dialog,
            text="🖥️",
            font=("Arial", 60)
        )
        warning_icon.pack(pady=10)
        
        # Info frame
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        warning_text = ctk.CTkLabel(
            info_frame,
            text="⚠️ WARNING:\n\n" +
                 "• ALL programs will be closed\n" +
                 "• Unsaved work will be LOST\n" +
                 "• Your computer will shutdown\n\n" +
                 "• Please save any important work before proceeding\n\n" +
                 "This action cannot be undone!",
            font=("Arial", 12),
            text_color="orange",
            justify="left"
        )
        warning_text.pack(pady=10)
        
        if is_force:
            force_warning = ctk.CTkLabel(
                dialog,
                text="🔴 FORCE SHUTDOWN: Programs will be force closed",
                font=("Arial", 11, "bold"),
                text_color="#e74c3c"
            )
            force_warning.pack(pady=5)
        
        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_confirm():
            dialog.destroy()
            self.append_chat("System", "🖥️ Shutting down computer... Goodbye!", tag="warning")
            self.set_status("Shutting down...", "red")
            # Execute shutdown after a short delay
            self.after(2000, lambda: AgentTools.execute_shutdown(is_force))
        
        def on_cancel():
            dialog.destroy()
            self.append_chat("System", "❌ Shutdown cancelled by user.", tag="error")
        
        shutdown_btn = ctk.CTkButton(
            btn_frame,
            text="🖥️ SHUTDOWN",
            command=on_confirm,
            width=130,
            height=45,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        shutdown_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖ Cancel",
            command=on_cancel,
            width=120,
            height=45
        )
        cancel_btn.pack(side="left", padx=10)
        
        self.wait_window(dialog)
    
    def show_restart_confirmation(self):
        """Show a confirmation dialog for system restart."""
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚠️ Confirm Restart")
        dialog.geometry("500x350")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus()
        
        # Warning icon and title
        title_label = ctk.CTkLabel(
            dialog,
            text="🔄 SYSTEM RESTART",
            font=("Arial", 18, "bold"),
            text_color="#3498db"
        )
        title_label.pack(pady=(20, 10))
        
        # Warning icon
        warning_icon = ctk.CTkLabel(
            dialog,
            text="🔄",
            font=("Arial", 60)
        )
        warning_icon.pack(pady=10)
        
        # Info frame
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        warning_text = ctk.CTkLabel(
            info_frame,
            text="⚠️ WARNING:\n\n" +
                 "• ALL programs will be closed\n" +
                 "• Unsaved work will be LOST\n" +
                 "• Your computer will restart\n\n" +
                 "• Please save any important work before proceeding\n\n" +
                 "This action cannot be undone!",
            font=("Arial", 12),
            text_color="orange",
            justify="left"
        )
        warning_text.pack(pady=10)
        
        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_confirm():
            dialog.destroy()
            self.append_chat("System", "🔄 Restarting computer... See you soon!", tag="warning")
            self.set_status("Restarting...", "blue")
            # Execute restart after a short delay
            self.after(2000, lambda: AgentTools.execute_restart())
        
        def on_cancel():
            dialog.destroy()
            self.append_chat("System", "❌ Restart cancelled by user.", tag="error")
        
        restart_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 RESTART",
            command=on_confirm,
            width=130,
            height=45,
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        restart_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖ Cancel",
            command=on_cancel,
            width=120,
            height=45
        )
        cancel_btn.pack(side="left", padx=10)
        
        self.wait_window(dialog)
    
    def set_status(self, text: str, color: str = "white"):
        """Update the status label."""
        self.after(0, lambda: self.status_label.configure(text=f"Status: {text}", text_color=color))
    
    def set_button_state(self, enabled: bool):
        """Enable or disable the send button and toggle stop button."""
        state = "normal" if enabled else "disabled"
        self.is_processing = not enabled
        
        def _update():
            self.send_btn.configure(state=state)
            if not enabled:
                self.stop_btn.grid()
                self.send_btn.grid_remove()
            else:
                self.stop_btn.grid_remove()
                self.send_btn.grid()
        
        self.after(0, _update)
    
    def stop_processing(self):
        """Stop the current agent processing."""
        self.should_stop = True
        self.set_status("Stopping...", "orange")
        self.append_chat("System", "⏹️ Processing stopped by user.", tag="error")
    # ==================== SESSION MANAGEMENT ====================

    def handle_save(self):
        """Invoke Mr. Perfect's brain to save the session."""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"session_{datetime.datetime.now().strftime('%H%M%S')}.json"
        )
        if path:
            result = AGENT_TOOLS.save_session(path)
            self.append_chat("System", result, tag="success")
    def handle_load(self):
        """Restore history into the chat display without looping errors."""
        from tkinter import filedialog
        try:
            path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                title="Load Session"
            )
            if not path:
                return

            # 1. Clear current UI and internal history list to prevent loops
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", "end")
            self.chat_history = [] 
            
            # 2. Use the tool to load the file data into self.chat_history
            result = AGENT_TOOLS.load_session(path)
            
            # 3. Re-populate the UI using the SAFE render method
            for msg in self.chat_history:
                # We extract timestamp if it exists, otherwise use current
                ts = msg.get('timestamp', datetime.datetime.now().strftime("%H:%M"))
                self._render_single_message(
                    msg.get('sender', 'System'), 
                    msg.get('text', ''), 
                    msg.get('tag'),
                    ts
                )
                
            self.append_chat("System", f"✅ {result}", tag="success")
            self.set_status("Session Restored", "cyan")

        except Exception as e:
            self.append_chat("Error", f"Load failed: {str(e)}", tag="error")
    def refresh_chat_display(self):
        """Redraws the entire chat window. INSTANT and NO FREEZE."""
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end") # Clear the screen
        
        for msg in self.chat_history:
            # Get values safely (handling different JSON key names)
            sender = msg.get('sender') or msg.get('role', 'System')
            text = msg.get('text') or msg.get('content', '')
            tag = msg.get('tag')
            ts = msg.get('timestamp') or datetime.datetime.now().strftime("%H:%M")
            
            # Use the helper that ONLY draws text and does NOT append to history
            self._render_loaded_message(sender, text, tag, ts)
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _render_loaded_message(self, sender, text, tag, timestamp):
        """Helper to draw text on screen without re-logging it to the list."""
        # Use your existing color logic
        if sender == "You":
            msg_tag = "you"
        elif sender == "Agent":
            msg_tag = "agent"
        elif sender == "Tool":
            msg_tag = "tool_call"
        else:
            msg_tag = tag or "normal"
            
        # Insert to display
        self.chat_display.insert("end", f"[{timestamp}] ", "timestamp")
        self.chat_display.insert("end", f"{sender.upper()}: ", msg_tag)
        self.chat_display.insert("end", f"{text}\n\n")

    def _render_single_message(self, sender, text, tag, timestamp):
        """Lightweight renderer: Puts text on screen but DOES NOT save to list."""
        self.chat_display.configure(state="normal")
        
        # Match your existing logic for colors
        if sender == "You":
            msg_tag = "you"
        elif sender == "Agent":
            msg_tag = "agent"
        elif sender == "Tool":
            msg_tag = "tool_call"
        else:
            msg_tag = tag or "normal"
            
        # Insert the message
        self.chat_display.insert("end", f"[{timestamp}] ", "timestamp")
        self.chat_display.insert("end", f"{sender.upper()}: ", msg_tag)
        self.chat_display.insert("end", f"{text}\n\n")

    def handle_send(self):
        """Handle user input and start agent thread."""
        query = self.user_input.get("1.0", "end").strip()
        if not query:
            return
        
        self.append_chat("You", query)
        self.user_input.delete("1.0", "end")
        self.should_stop = False  # Reset stop flag
        self.set_button_state(False)
        threading.Thread(target=self.run_agent_thread, args=(query,), daemon=True).start()
    
    def run_agent_thread(self, user_prompt: str):
        import json
        import re
        import inspect
        import os
        import datetime # Added to ensure timestamps work in the loop

        # --- 1. Speed Bypass for greetings ---
        greetings = ["hello", "hi", "salam", "hey", "hi there", "hi"]
        if user_prompt.lower().strip() in greetings:
            self.append_chat("Agent", "Hello! I'm ready. I have 79 tools to help you create files, run code, and monitor your system. What shall we build?")
            self.set_status("Ready", "gray")
            self.set_button_state(True)
            return

        self.set_status("Thinking...", "yellow")

        # --- 2. System Keyword Priority ---
        system_keywords = ["pc", "system", "disk", "cpu", "ram", "files", "folder", "directory", "save", "create", "run"]
        if any(k in user_prompt.lower() for k in system_keywords):
            user_prompt = f"[SYSTEM ACTION REQUIRED] User wants to interact with the local machine. You MUST use a TOOL (ACTION:). Do not just describe what you would do.\nUser Request: {user_prompt}"

        # --- 3. History Management ---
        if not hasattr(self, "session_history"):
            self.session_history = []
        
        if sum(len(m['content']) for m in self.session_history) > 3000:
            self.session_history = self.session_history[-4:] 

        # --- 4. Enforced Prompting ---
        tool_list = ", ".join(TOOL_MAP.keys())
        instructions = (
            f"You are a System Agent. Available Tools: {tool_list}\n"
            "To save code: use 'ACTION: create_code_file' with 'ARGS: {\"filepath\": \"path\", \"content\": \"code\"}'\n"
            "To run code: use 'ACTION: execute_code' or 'ACTION: run_file'.\n"
            "You MUST output the code in a markdown block (```python) AND call the tool in the SAME message."
        )

        messages = [{"role": "system", "content": instructions}]
        messages.extend(self.session_history)
        messages.append({"role": "user", "content": user_prompt})

        final_answer = ""
        max_iterations = 4 
        
        try:
            for iteration in range(max_iterations):
                if self.should_stop: break
                self.set_status(f"Step {iteration + 1}/{max_iterations}...", "yellow")

                # Note: This assumes 'client', 'LOCAL_MODEL' are defined globally
                response = client.chat.completions.create(
                    model=LOCAL_MODEL,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2048
                )
                
                content = response.choices[0].message.content

                # --- VISIBILITY: Always show code blocks immediately ---
                if "```" in content:
                    code_blocks = re.findall(r"```(?:python|javascript|bash|powershell)?\n([\s\S]*?)```", content)
                    for block in code_blocks:
                        self.append_chat("Agent", f"📄 Code Generated:\n```python\n{block.strip()}\n```")

                # --- PARSING ACTION & ARGS ---
                action_match = re.search(r"ACTION:\s*(\w+)", content, re.IGNORECASE)
                args_match = re.search(r"ARGS:\s*(\{.*\}|.*)", content, re.IGNORECASE | re.DOTALL)

                if action_match:
                    tool_name = action_match.group(1).strip().lower()
                    raw_args = args_match.group(1).strip() if args_match else ""

                    # --- IMPROVED ARGUMENT PARSING (FIX FOR WinError 123) ---
                    processed_args = {}
                    is_json_dict = False
                    
                    try:
                        # Attempt to handle potential JSON strings from LLM
                        if raw_args.startswith("{"):
                            # Clean up potential trailing text outside the JSON block
                            json_fix = re.search(r"(\{.*\})", raw_args, re.DOTALL)
                            if json_fix:
                                processed_args = json.loads(json_fix.group(1))
                                is_json_dict = True
                    except Exception:
                        is_json_dict = False

                    if tool_name in TOOL_MAP:
                        self.set_status(f"Tool: {tool_name}", "cyan")
                        target_func = TOOL_MAP[tool_name]
                        sig = inspect.signature(target_func)
                        params = list(sig.parameters.keys())

                        # --- CONTENT RESCUE ---
                        # If tool needs 'content' but it's missing from ARGS, pull from code blocks
                        if "content" in params and not processed_args.get("content"):
                            blocks = re.findall(r"```(?:python)?\n([\s\S]*?)```", content)
                            if blocks:
                                processed_args["content"] = blocks[0].strip()

                        # --- SMART SIGNATURE MAPPING ---
                        final_kwargs = {}
                        
                        if is_json_dict:
                            # Map keys directly from JSON dictionary to tool parameters
                            for p in params:
                                if p in processed_args:
                                    final_kwargs[p] = processed_args[p]
                        else:
                            # If not JSON, treat raw_args as a single positional value
                            clean_raw = raw_args.strip("'\" ")
                            for p in params:
                                if p == "filepath" or p == "path":
                                    final_kwargs[p] = clean_raw
                                elif p == "code" or p == "query" or p == "content":
                                    final_kwargs[p] = clean_raw
                                    break 

                        try:
                            # Execute tool via Brain (Mr. Perfect)
                            if final_kwargs:
                                result = target_func(**final_kwargs)
                            else:
                                result = target_func(raw_args) if raw_args else target_func()
                        except Exception as e:
                            result = f"Error calling {tool_name}: {str(e)}"

                        self.append_chat("Tool", f"🛠️ {tool_name} result: {str(result)[:300]}...", tag="tool_call")
                        
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": f"TOOL RESULT: {result}\nContinue to next step or provide FINAL ANSWER."})
                        continue 

                # --- HALLUCINATION ENFORCEMENT ---
                if ("create" in user_prompt.lower() or "save" in user_prompt.lower()) and not action_match:
                    if iteration == 0:
                        messages.append({"role": "user", "content": "SYSTEM: You failed to use a tool. Use 'ACTION: create_code_file' to save the code now."})
                        continue

            # --- FINAL ANSWER CHECK ---
                # 1. If the model explicitly provides the keyword
                if "FINAL ANSWER:" in content.upper():
                    final_answer = re.split(r"FINAL ANSWER:", content, flags=re.IGNORECASE)[-1].strip()
                    break
                
                # 2. If we reach the last iteration and the model is still talking/acting
                if iteration == max_iterations - 1:
                    # If it executed a tool, we synthesize a success message
                    if action_match:
                        final_answer = f"I have executed the final action ({tool_name}) and completed your request."
                    else:
                        # Otherwise, just use the raw response as the answer
                        final_answer = content.strip()
                    break

            # --- DISPLAY & SESSION LOGGING ---
            if final_answer:
                # Clean any accidental "ACTION:" or "ARGS:" text from the final summary
                clean_display = re.sub(r"ACTION:\s*\w+", "", final_answer, flags=re.IGNORECASE)
                clean_display = re.sub(r"ARGS:\s*\{.*\}|ARGS:.*", "", clean_display, flags=re.IGNORECASE | re.DOTALL)
                
                final_text = clean_display.strip()
                if final_text:
                    self.append_chat("Agent", final_text)
                    self.session_history.append({"role": "user", "content": user_prompt})
                    self.session_history.append({"role": "assistant", "content": final_text})
            else:
                # Fallback: If everything else fails, show the last known content
                fallback = content.strip() if 'content' in locals() else "Task completed."
                self.append_chat("Agent", fallback)

        except Exception as e:
            self.append_chat("Error", f"System Error: {str(e)}", tag="error")

        self.should_stop = False
        self.set_status("Ready", "gray")
        self.set_button_state(True)
        
if __name__ == "__main__":
    app = AgentGUI()
    app.mainloop()
