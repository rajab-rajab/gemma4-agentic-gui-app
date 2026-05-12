"""
Agentic AI - A Desktop AI Agent with Local LLM Integration
Enhanced with additional tools, better security, and improved error handling.
"""

import os
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
    def web_search(query: str, depth: str = "basic") -> str:
        """Search the web using Tavily API."""
        if not tavily:
            return "Error: Tavily API not configured. Set TAVILY_API_KEY environment variable."
        try:
            search_depth = "basic" if depth == "basic" else "advanced"
            results = tavily.search(query=query, search_depth=search_depth, max_results=5)
            
            if isinstance(results, dict) and 'results' in results:
                formatted = []
                formatted.append(f"🔍 Search Results for: {query}")
                formatted.append("=" * 60)
                
                for i, r in enumerate(results['results'][:5], 1):
                    title = r.get('title', 'No title')
                    url = r.get('url', '')
                    content = r.get('content', '')[:250]
                    
                    # Format with numbered results and clickable URL
                    formatted.append(f"\n{i}. {title}")
                    formatted.append(f"   📎 {url}")
                    formatted.append(f"   💬 {content}...")
                
                formatted.append("\n" + "=" * 60)
                formatted.append("\n📋 QUICK LINKS:")
                for i, r in enumerate(results['results'][:5], 1):
                    url = r.get('url', '')
                    title = r.get('title', 'No title')[:50]
                    if len(title) < len(r.get('title', 'No title')):
                        title += "..."
                    formatted.append(f"   [{i}] {title}: {url}")
                
                return "\n".join(formatted)
            return str(results)[:1000]
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def web_search_simple(query: str) -> str:
        """Simple web search without API (uses DuckDuckGo basic HTML)."""
        try:
            import urllib.request
            from urllib.parse import quote
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            # Simple parsing for search results
            results = re.findall(r'<a class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
            snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]*)</a>', html)
            
            output = [f"🔍 Search: {query}"]
            output.append("=" * 60)
            
            for i, (url, title) in enumerate(results[:5], 1):
                snippet = snippets[i] if i < len(snippets) else ""
                output.append(f"\n{i}. {title}")
                output.append(f"   📎 {url}")
                output.append(f"   💬 {snippet[:150]}...")
            
            output.append("\n" + "=" * 60)
            output.append("\n📋 QUICK LINKS:")
            for i, (url, title) in enumerate(results[:5], 1):
                title_short = title[:50] + "..." if len(title) > 50 else title
                output.append(f"   [{i}] {title_short}: {url}")
            
            return "\n".join(output)
        except Exception as e:
            return f"Search Error: {str(e)}\n\nTip: Set TAVILY_API_KEY for better results."
    
    @staticmethod
    def search_with_urls(query: str) -> str:
        """
        Search the web and return results with prominent clickable URLs.
        This is the primary search function that always shows URLs clearly.
        
        Args:
            query: Search query
            
        Returns:
            Formatted search results with clickable URLs
        """
        if tavily:
            try:
                results = tavily.search(query=query, search_depth="advanced", max_results=8)
                
                if isinstance(results, dict) and 'results' in results:
                    formatted = []
                    formatted.append(f"🔍 Search: {query}")
                    formatted.append("=" * 70)
                    formatted.append("")
                    
                    for i, r in enumerate(results['results'][:8], 1):
                        title = r.get('title', 'No title')
                        url = r.get('url', '')
                        content = r.get('content', '')[:300]
                        
                        # Main result with title and URL
                        formatted.append(f"【{i}】 {title}")
                        formatted.append(f"🔗 {url}")
                        formatted.append(f"📝 {content}...")
                        formatted.append("")
                    
                    # Prominent quick links section
                    formatted.append("━" * 70)
                    formatted.append("🔗 QUICK LINKS - Click or copy these URLs:")
                    formatted.append("━" * 70)
                    for i, r in enumerate(results['results'][:8], 1):
                        url = r.get('url', '')
                        title = r.get('title', 'No title')[:60]
                        formatted.append(f"  {i}. {title}")
                        formatted.append(f"     → {url}")
                    
                    return "\n".join(formatted)
            except Exception as e:
                return f"Search Error: {str(e)}"
        
        # Fallback to simple search
        return AgentTools.web_search_simple(query)
    
    @staticmethod
    def get_system_info() -> str:
        """Get current system resource usage."""
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
    def create_file(filepath: str, content: str = "") -> str:
        """
        Create a new file.
        
        Args:
            filepath: Path for the new file
            content: Optional initial content
            
        Returns:
            Success or error message
        """
        try:
            p = Path(filepath)
            
            if p.exists():
                return f"Error: File already exists: {filepath}"
            
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return f"✅ Created file: {p.name}\nPath: {p.resolve()}\nSize: {p.stat().st_size} bytes"
        except FileExistsError:
            return f"Error: File already exists: {filepath}"
        except PermissionError:
            return f"Error: Permission denied: {filepath}"
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
    def execute_code(code: str, language: str = "python") -> str:
        """
        Execute code snippets and return output.
        Supports Python, JavaScript, Bash, and PowerShell.
        
        Args:
            code: Code to execute
            language: Language (python, javascript, bash, powershell)
            
        Returns:
            Execution output or error
        """
        try:
            import tempfile
            import uuid
            
            if language.lower() == "python":
                # Execute Python code
                try:
                    import sys
                    from io import StringIO
                    
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = StringIO()
                    sys.stderr = StringIO()
                    
                    try:
                        exec(code, {"__builtins__": __builtins__})
                        output = sys.stdout.getvalue()
                        errors = sys.stderr.getvalue()
                    finally:
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr
                    
                    result = ""
                    if output:
                        result += f"📤 Output:\n{output}"
                    if errors:
                        result += f"\n⚠️ Errors:\n{errors}"
                    return result if result else "✅ Code executed successfully (no output)"
                except SyntaxError as se:
                    return f"❌ Syntax Error: {str(se)}"
                except Exception as e:
                    return f"❌ Runtime Error: {str(e)}"
            
            elif language.lower() == "javascript":
                # Execute JavaScript using Node.js
                temp_file = tempfile.NamedTemporaryFile(suffix='.js', delete=False)
                temp_file.write(code.encode())
                temp_file.close()
                
                result = subprocess.run(['node', temp_file.name], capture_output=True, text=True, timeout=30)
                os.unlink(temp_file.name)
                
                if result.stdout:
                    return f"📤 Output:\n{result.stdout}"
                return f"⚠️ Errors:\n{result.stderr}" if result.stderr else "✅ Code executed"
            
            elif language.lower() in ["bash", "shell"]:
                # Execute bash/shell commands
                result = subprocess.run(code, shell=True, capture_output=True, text=True, timeout=30)
                output = f"📤 Output:\n{result.stdout}" if result.stdout else ""
                output += f"\n⚠️ Errors:\n{result.stderr}" if result.stderr else ""
                return output if output else "✅ Code executed successfully"
            
            elif language.lower() == "powershell":
                # Execute PowerShell
                result = subprocess.run(
                    ["powershell", "-Command", code],
                    capture_output=True, text=True, timeout=30
                )
                output = f"📤 Output:\n{result.stdout}" if result.stdout else ""
                output += f"\n⚠️ Errors:\n{result.stderr}" if result.stderr else ""
                return output if output else "✅ Code executed successfully"
            
            else:
                return f"❌ Unsupported language: {language}\nSupported: python, javascript, bash, powershell"
        
        except subprocess.TimeoutExpired:
            return "❌ Code execution timed out (30 seconds limit)"
        except Exception as e:
            return f"❌ Execution Error: {str(e)}"
    
    @staticmethod
    def create_code_file(filepath: str, content: str, language: str = "") -> str:
        """
        Create a code file with proper syntax.
        
        Args:
            filepath: Path for the code file
            content: Code content
            language: Language for file extension (optional)
            
        Returns:
            Success or error message
        """
        try:
            p = Path(filepath)
            
            # Detect language from extension if not specified
            if not language:
                ext_map = {
                    '.py': 'Python',
                    '.js': 'JavaScript',
                    '.ts': 'TypeScript',
                    '.java': 'Java',
                    '.cpp': 'C++',
                    '.c': 'C',
                    '.cs': 'C#',
                    '.html': 'HTML',
                    '.css': 'CSS',
                    '.json': 'JSON',
                    '.xml': 'XML',
                    '.yaml': 'YAML',
                    '.yml': 'YAML',
                    '.sh': 'Bash',
                    '.bat': 'Batch',
                    '.ps1': 'PowerShell',
                    '.sql': 'SQL',
                    '.md': 'Markdown',
                }
                language = ext_map.get(p.suffix.lower(), 'Unknown')
            
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            
            return f"✅ Created {language} file: {p.name}\nPath: {p.resolve()}"
        except Exception as e:
            return f"❌ File Creation Error: {str(e)}"
    
    @staticmethod
    def generate_code_template(task: str, language: str = "python") -> str:
        """
        Generate code templates based on task description.
        Uses web search if needed for best practices.
        
        Args:
            task: Description of the code task
            language: Programming language (default: python)
            
        Returns:
            Code template and explanation
        """
        # Search for best practices if needed
        try:
            # Common code templates
            templates = {
                "python": {
                    "web_server": '''import http.server
import socketserver

PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()''',
                    "api": '''from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api', methods=['GET', 'POST'])
def api_handler():
    data = request.get_json() if request.method == 'POST' else {}
    return jsonify({'status': 'success', 'data': data})

if __name__ == '__main__':
    app.run(debug=True, port=5000)''',
                    "class": '''class ClassName:
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2
    
    def method_name(self):
        """Description of the method."""
        return f"Parameters: {self.param1}, {self.param2}"
    
    def __str__(self):
        return f"ClassName({self.param1}, {self.param2})"

# Usage
obj = ClassName("value1", "value2")
print(obj.method_name())''',
                    "function": '''def function_name(param1, param2=None):
    """
    Description of what the function does.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: None)
    
    Returns:
        Description of return value
    """
    # Main logic here
    result = param1  # Placeholder
    
    return result

# Example usage
result = function_name("test", param2="optional")
print(result)''',
                },
                "javascript": {
                    "web_server": '''const http = require('http');

const PORT = 3000;

const server = http.createServer((req, res) => {
    res.writeHead(200, {'Content-Type': 'text/plain'});
    res.end('Hello World!\\n');
});

server.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}/`);
});''',
                    "class": '''class ClassName {
    constructor(param1, param2) {
        this.param1 = param1;
        this.param2 = param2;
    }
    
    methodName() {
        return `Parameters: ${this.param1}, ${this.param2}`;
    }
}

// Usage
const obj = new ClassName("value1", "value2");
console.log(obj.methodName());''',
                    "function": '''function functionName(param1, param2 = null) {
    /**
     * Description of what the function does.
     * @param {*} param1 - Description of param1
     * @param {*} param2 - Description of param2 (optional)
     * @returns {*} Description of return value
     */
    
    // Main logic here
    const result = param1; // Placeholder
    
    return result;
}

// Example usage
const result = functionName("test", "optional");
console.log(result);''',
                }
            }
            
            # Look for matching template
            task_lower = task.lower()
            selected_template = None
            
            if any(word in task_lower for word in ['server', 'http', 'web', 'website']):
                selected_template = templates.get(language.lower(), {}).get('web_server')
            elif any(word in task_lower for word in ['api', 'rest', 'endpoint']):
                selected_template = templates.get(language.lower(), {}).get('api')
            elif any(word in task_lower for word in ['class', 'object']):
                selected_template = templates.get(language.lower(), {}).get('class')
            elif any(word in task_lower for word in ['function', 'method', 'def']):
                selected_template = templates.get(language.lower(), {}).get('function')
            
            if selected_template:
                return f"📝 **{language.upper()} Code Template:**\n\n```\n{selected_template}\n```\n\n💡 This is a basic template. You can customize it further!"
            
            return "❌ No template found for this task. Please describe your task more specifically.\n\n" \
                   "Available templates: web server, API, class, function"
        
        except Exception as e:
            return f"❌ Error generating template: {str(e)}"
    
    @staticmethod
    def check_code_syntax(code: str, language: str = "python") -> str:
        """
        Check code syntax without executing.
        import tempfile

        Args:
            code: Code to check
            language: Programming language
            
        Returns:
            Syntax validation result
        """
        try:
            import ast
            import tempfile
            
            if language.lower() == "python":
                try:
                    ast.parse(code)
                    return "✅ Python syntax is valid"
                except SyntaxError as e:
                    return f"❌ Syntax Error at line {e.lineno}: {e.msg}\n{e.text}"
            
            elif language.lower() == "javascript":
                import subprocess
                temp_file = tempfile.NamedTemporaryFile(suffix='.js', delete=False)
                temp_file.write(b"const a = 1; " + code.encode())
                temp_file.close()
                
                result = subprocess.run(
                    ['node', '--check', temp_file.name],
                    capture_output=True, text=True
                )
                os.unlink(temp_file.name)
                
                if result.returncode == 0:
                    return "✅ JavaScript syntax is valid"
                return f"❌ JavaScript Syntax Error:\n{result.stderr}"
            
            else:
                return f"❌ Syntax check not supported for: {language}"
        
        except Exception as e:
            return f"❌ Syntax Check Error: {str(e)}"
    
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
    "get_datetime": lambda *args, **kwargs: AGENT_TOOLS.get_datetime(),
    
    # System Commands
    "run_powershell": lambda cmd, *args, **kwargs: AGENT_TOOLS.run_powershell(cmd),
    "run_command": lambda cmd, *args, **kwargs: AGENT_TOOLS.run_command(cmd),
    
    # Web & Search
    "web_search": lambda query, *args, **kwargs: AGENT_TOOLS.web_search(query),
    "web_search_simple": lambda query, *args, **kwargs: AGENT_TOOLS.web_search_simple(query),
    "search_with_urls": lambda query, *args, **kwargs: AGENT_TOOLS.search_with_urls(query),
    "get_weather": lambda location, *args, **kwargs: AGENT_TOOLS.get_weather(location),
    "get_ip_info": lambda *args, **kwargs: AGENT_TOOLS.get_ip_info(),
    
    # System Info - FIXED: Accept any arguments
    "get_system_info": lambda *args, **kwargs: AGENT_TOOLS.get_system_info(),
    "get_uptime": lambda *args, **kwargs: AGENT_TOOLS.get_uptime(),
    "get_battery_status": lambda *args, **kwargs: AGENT_TOOLS.get_battery_status(),
    "get_cpu_info": lambda *args, **kwargs: AGENT_TOOLS.get_cpu_info(),
    "get_memory_info": lambda *args, **kwargs: AGENT_TOOLS.get_memory_info(),
    
    # Disk & Files
    "list_files": lambda path=".", *args, **kwargs: AGENT_TOOLS.list_files(path),
    "read_file": lambda path, *args, **kwargs: AGENT_TOOLS.read_file(path),
    "read_file_lines": lambda path, start=None, count=None, *args, **kwargs: AGENT_TOOLS.read_file_lines(path, start, count),
    "write_file": lambda path, content, *args, **kwargs: AGENT_TOOLS.write_file(path, content),
    "get_file_info": lambda path, *args, **kwargs: AGENT_TOOLS.get_file_info(path),
    "get_disk_usage": lambda path=".", *args, **kwargs: AGENT_TOOLS.get_disk_usage(path),
    "search_files": lambda pattern, path=".", *args, **kwargs: AGENT_TOOLS.search_files(pattern, path),
    "delete_file": lambda path, *args, **kwargs: AGENT_TOOLS.delete_file(path),
    "confirm_delete": lambda path, *args, **kwargs: AGENT_TOOLS.confirm_delete(path),
    "create_folder": lambda path, *args, **kwargs: AGENT_TOOLS.create_folder(path),
    "create_file": lambda path, content="", *args, **kwargs: AGENT_TOOLS.create_file(path, content),
    "copy_file": lambda src, dest, *args, **kwargs: AGENT_TOOLS.copy_file(src, dest),
    "move_file": lambda src, dest, *args, **kwargs: AGENT_TOOLS.move_file(src, dest),
    "rename_file": lambda old, new, *args, **kwargs: AGENT_TOOLS.rename_file(old, new),
    "get_file_hash": lambda path, *args, **kwargs: AGENT_TOOLS.get_file_hash(path),
    
    # PowerShell Windows Admin Tools - FIXED: Accept any arguments
    "ps_get_services": lambda *args, **kwargs: AGENT_TOOLS.ps_get_services(),
    "ps_service_action": lambda name, action, *args, **kwargs: AGENT_TOOLS.ps_service_action(name, action),
    "ps_get_eventlog": lambda log="System", count=10, *args, **kwargs: AGENT_TOOLS.ps_get_eventlog(log, count),
    "ps_get_processes_detailed": lambda *args, **kwargs: AGENT_TOOLS.ps_get_processes_detailed(),
    "ps_get_registry": lambda path, *args, **kwargs: AGENT_TOOLS.ps_get_registry(path),
    "ps_get_scheduled_tasks": lambda *args, **kwargs: AGENT_TOOLS.ps_get_scheduled_tasks(),
    "ps_get_installed_programs": lambda *args, **kwargs: AGENT_TOOLS.ps_get_installed_programs(),
    "ps_get_environment_vars": lambda *args, **kwargs: AGENT_TOOLS.ps_get_environment_vars(),
    "ps_get_network_adapters": lambda *args, **kwargs: AGENT_TOOLS.ps_get_network_adapters(),
    "ps_get_firewall_rules": lambda *args, **kwargs: AGENT_TOOLS.ps_get_firewall_rules(),
    "ps_get_disk_partitions": lambda *args, **kwargs: AGENT_TOOLS.ps_get_disk_partitions(),
    "ps_get_wifi_networks": lambda *args, **kwargs: AGENT_TOOLS.ps_get_wifi_networks(),
    "ps_get_hotfixes": lambda *args, **kwargs: AGENT_TOOLS.ps_get_hotfixes(),
    "ps_get_running_tasks": lambda *args, **kwargs: AGENT_TOOLS.ps_get_running_tasks(),
    "ps_get_systeminfo": lambda *args, **kwargs: AGENT_TOOLS.ps_get_systeminfo(),
    
    # Program Installation/Uninstallation
    "search_program": lambda name, *args, **kwargs: AGENT_TOOLS.search_program(name),
    "validate_program_safety": lambda name, url, *args, **kwargs: AGENT_TOOLS.validate_program_safety(name, url),
    "get_installed_programs_list": lambda *args, **kwargs: AGENT_TOOLS.get_installed_programs_list(),
    "check_program_removable": lambda name, *args, **kwargs: AGENT_TOOLS.check_program_removable(name),
    "prepare_install_command": lambda name, *args, **kwargs: AGENT_TOOLS.prepare_install_command(name),
    "prepare_uninstall_command": lambda name, *args, **kwargs: AGENT_TOOLS.prepare_uninstall_command(name),
    "execute_install": lambda cmd, *args, **kwargs: AGENT_TOOLS.execute_install(cmd),
    "execute_uninstall": lambda cmd, *args, **kwargs: AGENT_TOOLS.execute_uninstall(cmd),
    
    # Program Updates
    "check_program_updates": lambda name, *args, **kwargs: AGENT_TOOLS.check_program_updates(name),
    "validate_update_safety": lambda name, url, *args, **kwargs: AGENT_TOOLS.validate_update_safety(name, url),
    "prepare_update_command": lambda name, *args, **kwargs: AGENT_TOOLS.prepare_update_command(name),
    "execute_update": lambda cmd, *args, **kwargs: AGENT_TOOLS.execute_update(cmd),
    
    # Agent Self-Protection
    "validate_self_protection": lambda path, *args, **kwargs: AGENT_TOOLS.validate_self_protection(path),
    "get_agent_info": lambda *args, **kwargs: AGENT_TOOLS.get_agent_info(),
    
    # System Control (Shutdown/Restart)
    "shutdown_computer": lambda *args, **kwargs: AGENT_TOOLS.shutdown_computer(),
    "prepare_shutdown": lambda *args, **kwargs: AGENT_TOOLS.prepare_shutdown(),
    "execute_shutdown": lambda delay=30, *args, **kwargs: AGENT_TOOLS.execute_shutdown(delay),
    "restart_computer": lambda *args, **kwargs: AGENT_TOOLS.restart_computer(),
    "execute_restart": lambda delay=30, *args, **kwargs: AGENT_TOOLS.execute_restart(delay),
    "sleep_computer": lambda *args, **kwargs: AGENT_TOOLS.sleep_computer(),
    
    # Coding Tools
    "execute_code": lambda code, language="python", *args, **kwargs: AGENT_TOOLS.execute_code(code, language),
    "create_code_file": lambda path, content, *args, **kwargs: AGENT_TOOLS.create_code_file(path, content),
    "generate_code_template": lambda language, task, *args, **kwargs: AGENT_TOOLS.generate_code_template(language, task),
    "check_code_syntax": lambda code, language="python", *args, **kwargs: AGENT_TOOLS.check_code_syntax(code, language),
    "get_code_snippet_info": lambda *args, **kwargs: AGENT_TOOLS.get_code_snippet_info(),
    
    # Calculator
    "calculate": lambda expression, *args, **kwargs: AGENT_TOOLS.calculate(expression),
    
    # Network
    "ping_host": lambda host, count=4, *args, **kwargs: AGENT_TOOLS.ping_host(host, count),
    "check_port": lambda host, port, *args, **kwargs: AGENT_TOOLS.check_port(host, port),
    "dns_lookup": lambda domain, *args, **kwargs: AGENT_TOOLS.dns_lookup(domain),
    "get_network_info": lambda *args, **kwargs: AGENT_TOOLS.get_network_info(),
    
    # File System
    "get_current_directory": lambda *args, **kwargs: AGENT_TOOLS.get_current_directory(),
    "change_directory": lambda path, *args, **kwargs: AGENT_TOOLS.change_directory(path),
    
    # Security
    "generate_password": lambda length=16, *args, **kwargs: AGENT_TOOLS.generate_password(length),
    
    # Process Management
    "get_processes": lambda *args, **kwargs: AGENT_TOOLS.get_processes(),
    "kill_process": lambda name, *args, **kwargs: AGENT_TOOLS.kill_process(name),
    
    # Clipboard
    "get_clipboard": lambda *args, **kwargs: AGENT_TOOLS.get_clipboard(),
    "set_clipboard": lambda text, *args, **kwargs: AGENT_TOOLS.set_clipboard(text),
}

# --- SYSTEM PROMPT ---

SYSTEM_PROMPT = """You are a helpful AI Agent with access to various tools.

When you need to use a tool, follow this format EXACTLY:
THOUGHT: <your reasoning>
ACTION: <tool_name>
ARGS: <argument>

Example:
THOUGHT: The user wants to know what time it is.
ACTION: get_datetime
ARGS: default

IMPORTANT - WEB SEARCH FALLBACK RULE:
If you do NOT know the answer to a question, or if you CANNOT perform a task:
1. You MUST use the web_search tool to find the answer
2. Search the web for relevant information
3. Provide the user with accurate information from your search results
4. Always include clickable URLs in your response

Examples when to use web search:
- User asks about current events, news, or recent information
- User asks about something you don't have knowledge of
- User asks for product reviews, comparisons, or recommendations
- User asks for tutorial/guide on something specific
- User asks about a topic outside your training data
- User asks for instructions on how to do something
- User's coding task produces errors or unexpected results
- User asks for specific library/API usage you are unsure about
- User requests code that is beyond your training data

IMPORTANT - CODING WEB SEARCH RULE:
When helping with coding tasks:
1. If user reports code is not working as expected, search web for solutions
2. If you are unsure how to solve a coding problem, search online for examples
3. If error occurs, search for the error message to find fixes
4. Always provide working code examples from web search results

Available Tools:
- get_datetime: Get current date/time. Args: format_type ("default", "date", "time", "iso", "unix", "day", "day_short", "full", "full_with_time")
  IMPORTANT: When user asks about "what day is today" or "what day of the week", use format_type="day" or "full"
  For date questions like "what date is today", use format_type="date"
- run_powershell: Execute PowerShell commands. Args: command string
- run_command: Execute system commands. Args: command string
- web_search: Search the web with clickable URLs. Args: query string
- web_search_simple: Simple web search with URLs. Args: query string
- search_with_urls: Search with prominent clickable URLs. Args: query string
- get_weather: Get weather info. Args: location string

IMPORTANT: When using web search, ALWAYS include the full URL in results so user can click/visit them. Format results with numbered links.

SYSTEM CONTROL TOOLS (Shutdown/Restart):
- shutdown_computer: Shutdown computer. Args: force (optional)
- prepare_shutdown: Prepare shutdown with confirmation. Args: force (optional)
- execute_shutdown: Execute shutdown after confirmation. Args: force (optional)
- restart_computer: Restart computer. No args required
- execute_restart: Execute restart after confirmation
- sleep_computer: Put computer to sleep

IMPORTANT: When user says "shutdown", "turn off", "power off", "shut down":
1. ALWAYS ask for confirmation first
2. Explain that all programs will be closed
3. Use shutdown_computer tool to get confirmation
4. NEVER auto-shutdown without user permission

IMPORTANT: For ALL web search operations (web_search, get_weather, check_program_updates, search_with_urls), you MUST use Tavily API if available. The Tavily API provides more accurate and comprehensive results.
- get_system_info: Get CPU/RAM usage
- get_uptime: Get system uptime
- get_battery_status: Get battery info (laptops)
- get_cpu_info: Get CPU details
- get_memory_info: Get memory details
- list_files: List directory contents. Args: path, pattern (optional), include_hidden (optional)
- read_file: Read file contents. Args: filepath, max_lines (optional), encoding (optional)
- read_file_lines: Read specific lines. Args: filepath, start_line, count
- write_file: Write to file. Args: filepath, content, append (optional)
- get_file_info: Get file details. Args: filepath
- get_disk_usage: Get disk space. Args: path (optional)
- search_files: Find files. Args: pattern, path (optional), max_results (optional)
- delete_file: DELETE file/folder with restrictions. Returns confirmation request.
- confirm_delete: Confirm deletion after user approval. Args: filepath (from delete_file)
  DELETE RESTRICTIONS:
  - CANNOT delete system partitions (C:, D:, etc.) or root (/)
  - CANNOT delete system directories (Windows, System32, SysWOW64, /etc, /bin, etc.)
  - CANNOT delete non-empty folders
  - CANNOT delete system files (.sys, .dll, bootmgr, etc.)
  - MUST ask user for confirmation before any deletion
  - ALWAYS report what will be deleted (name, size) before deleting
  - If any restriction is triggered, report error and do NOT proceed
- create_folder: Create new folder. Args: folderpath
- create_file: Create new file. Args: filepath, content (optional)
- copy_file: Copy file/folder. Args: source, destination
- move_file: Move file/folder. Args: source, destination
- rename_file: Rename file/folder. Args: oldpath, newname
- get_file_hash: Calculate file hash. Args: filepath, algorithm (md5/sha1/sha256)
- ps_get_services: Get Windows services. Args: status (all/running/stopped)
- ps_service_action: Start/stop/restart service. Args: service_name, action
- ps_get_eventlog: Get Event Log. Args: logname (System/Application/Security), count
- ps_get_processes_detailed: Get detailed process list
- ps_get_registry: Read registry. Args: key_path (e.g., HKLM:\\SOFTWARE\\Microsoft)
- ps_get_scheduled_tasks: Get scheduled tasks
- ps_get_installed_programs: Get installed programs list
- ps_get_environment_vars: Get environment variables
- ps_get_network_adapters: Get network adapters info
- ps_get_firewall_rules: Get firewall rules. Args: enabled_only (True/False)
- ps_get_disk_partitions: Get disk and partition info
- ps_get_wifi_networks: Get available WiFi networks
- ps_get_hotfixes: Get installed Windows updates/hotfixes
- ps_get_running_tasks: Get running tasks with details
- ps_get_systeminfo: Get comprehensive system information

# PROGRAM MANAGEMENT (Install/Uninstall)
- search_program: Search online for program. Args: program_name
- validate_program_safety: Check if program is safe. Args: program_name, url (optional)
- get_installed_programs_list: List all installed programs
- check_program_removable: Check if program can be uninstalled. Args: program_display_name
- prepare_install_command: Prepare install with confirmation. Args: program_name, download_url
- prepare_uninstall_command: Prepare uninstall with confirmation. Args: program_name, uninstall_string (optional)
- execute_install: Execute installation after confirmation. Args: program_name, download_url
- execute_uninstall: Execute uninstallation after confirmation. Args: program_name, uninstall_string

# PROGRAM UPDATES (User must REQUEST this)
- check_program_updates: Check for updates online (requires user request). Args: program_name
- validate_update_safety: Validate update source. Args: program_name, download_url
- prepare_update_command: Prepare update with confirmation. Args: program_name, download_url
- execute_update: Execute update after confirmation. Args: program_name, download_url

UPDATE SAFETY RULES:
- NEVER auto-check for updates - user must REQUEST this feature
- NEVER auto-update programs - user must REQUEST update
- ALWAYS search online first to find official download source
- ALWAYS ask user for confirmation BEFORE updating
- Updates are treated like new installations (require permission)

# CODING TOOLS
- execute_code: Execute code in various languages. Args: code, language (python/javascript/bash/powershell)
- create_code_file: Create a code file. Args: filepath, content, language (optional)
- generate_code_template: Generate code templates. Args: task, language (python/javascript)
- check_code_syntax: Check syntax without execution. Args: code, language
- get_code_snippet_info: Get language info and patterns. Args: language

CODING RULES:
- ALWAYS try to help with coding tasks using execute_code tool
- If code execution fails or output is incorrect, use web_search to find solutions
- If you don't know how to solve a coding problem, search online for solutions
- Use web_search to find best practices, code examples, and documentation
- Support languages: Python, JavaScript, Bash, PowerShell, HTML, CSS, SQL
- If user asks for code that you cannot generate correctly, search the web for examples
- ALWAYS use web_search when coding task is beyond your training data
- If user says code is not working as expected, search web for solutions

IMPORTANT: If a coding task fails or produces unexpected results:
1. First try to fix the code based on error messages
2. If you cannot fix it, use web_search to find solutions
3. Present the web search results with explanations

# AGENT SELF-PROTECTION
- validate_self_protection: Check if path is protected. Args: path
- get_agent_info: Get agent information and statistics

SELF-PROTECTION RULES:
- CANNOT delete, modify, or harm the agent itself (agent.py)
- CANNOT delete or modify running LLM processes or files
- CANNOT delete critical files: requirements.txt, README.md, venv, python.exe
- Protected files: agent.py, agent.exe, requirements.txt, README.md, LICENSE, venv, .venv, ollama, ollama.exe

INSTALL/UNINSTALL SAFETY RULES:
- ALWAYS search online first to find official download source
- ALWAYS validate URL safety (HTTPS, official sites preferred)
- ALWAYS ask user for confirmation BEFORE installing or uninstalling
- NEVER suggest uninstalling system programs (Windows, drivers, .NET, Visual C++, etc.)
- NEVER install from suspicious URLs (torrent, crack, keygen sites)
- If program name contains: windows, microsoft, intel, nvidia, amd, realtek, kernel, system, driver, boot -> DO NOT UNINSTALL
- System programs list: windows, kernel, runtime, visual c++, vcruntime, msvc, .net framework, dotnet, intel, nvidia, amd, radeon, geforce, realtek, audio, graphics, wireless, bluetooth
- ALWAYS inform user about what will be installed/uninstalled
- ping_host: Ping a host. Args: hostname, count (optional)
- check_port: Check if port is open. Args: host, port
- dns_lookup: DNS lookup. Args: hostname
- get_network_info: List network interfaces
- get_current_directory: Get CWD
- change_directory: Change directory. Args: path
- generate_password: Generate password. Args: length (optional), include_special (optional)
- get_processes: List processes. Args: limit (optional)
- kill_process: Kill process. Args: PID
- get_clipboard: Get clipboard content
- set_clipboard: Set clipboard. Args: text
- get_ip_info: Get public IP info

If you have the answer, say:
FINAL ANSWER: <your answer>

If you are writing a poem, story, or simple response, just write it directly without any tool calls.
"""

# --- GUI APPLICATION ---

class AgentGUI(ctk.CTk):
    """Main GUI application for the AI Agent."""
    
    # ==================== Helper Methods ====================
    
    def append_chat(self, sender, message, tag=None):
        """Append a message to the chat display."""
        from datetime import datetime
        self.chat_display.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M")
        
        if sender != "System":
            self.chat_display.insert("end", f"[{timestamp}] ", "timestamp")
        
        self.chat_display.insert("end", f"{message}\n\n", tag or "normal")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
    
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
    
    def handle_send(self):
        """Handle send button click."""
        user_message = self.user_input.get("1.0", "end").strip()
        if not user_message:
            return
        self.user_input.delete("1.0", "end")
        self.append_chat("You", user_message, tag="you")
        self.should_stop = False
        self.is_processing = True
        self.send_btn.grid_remove()
        self.stop_btn.grid()
        # Start processing in background
        self.after(100, lambda: self.process_with_agent(user_message))
    
    def stop_processing(self):
        """Stop the current processing."""
        self.should_stop = True
        self.append_chat("System", "Stopping...", tag="error")
    
    def process_with_agent(self, user_message):
        """Process user message with the AI agent."""
        # This will be connected to your agent logic
        try:
            self.append_chat("Agent", "Processing your request...", tag="agent")
            # Add your agent processing logic here
            response = f"You said: {user_message}"
            self.append_chat("Agent", response, tag="agent")
        except Exception as e:
            self.append_chat("System", f"Error: {str(e)}", tag="error")
        finally:
            self.is_processing = False
            self.should_stop = False
            self.send_btn.grid()
            self.stop_btn.grid_remove()
    
    def update_status(self, status):
        """Update the status label."""
        self.status_label.configure(text=f"Status: {status}")
    
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
        
        # Configure text tags for styling
        self.chat_display.tag_config("timestamp", foreground="gray")
        self.chat_display.tag_config("tool_call", foreground="cyan")
        self.chat_display.tag_config("error", foreground="#ff6b6b")
        self.chat_display.tag_config("success", foreground="#51cf66")
        self.chat_display.tag_config("you", foreground="#74c0fc")
        self.chat_display.tag_config("agent", foreground="#ffd43b")
        
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
        
        # Spacer at top
        spacer_top = ctk.CTkLabel(self.buttons_frame, text="")
        spacer_top.grid(row=0, pady=(0, 20))
        
        # Send button
        self.send_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Send ➤",
            command=self.handle_send,
            width=100,
            height=45,
            font=("Arial", 13, "bold")
        )
        self.send_btn.grid(row=1, padx=10, pady=5)
        
        # Stop button (initially hidden)
        self.stop_btn = ctk.CTkButton(
            self.buttons_frame,
            text="■ Stop",
            command=self.stop_processing,
            width=100,
            height=45,
            font=("Arial", 13, "bold"),
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        self.stop_btn.grid(row=2, padx=10, pady=5)
        self.stop_btn.grid_remove()  # Hide initially
        
        # Clear Chat button
        self.clear_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Clear Chat",
            command=self.clear_chat,
            width=100,
            height=40
        )
        self.clear_btn.grid(row=3, padx=10, pady=5)
        
        # Copy Output button
        self.copy_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Copy Output",
            command=self.copy_output,
            width=100,
            height=40
        )
        self.copy_btn.grid(row=4, padx=10, pady=5)
        
        # Copy Last Response button
        self.copy_last_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Copy Last",
            command=self.copy_last_response,
            width=100,
            height=40
        )
        self.copy_last_btn.grid(row=5, padx=10, pady=5)
        
        # Clear Input button
        self.clear_input_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Clear Input",
            command=self.clear_input,
            width=100,
            height=40
        )
        self.clear_input_btn.grid(row=6, padx=10, pady=5)
        
        # Spacer between buttons
        spacer_mid = ctk.CTkLabel(self.buttons_frame, text="")
        spacer_mid.grid(row=7, pady=(20, 0))
        
        # Prompts quick buttons
        prompts_label = ctk.CTkLabel(
            self.buttons_frame,
            text="Quick Prompts",
            font=("Arial", 11, "bold")
        )
        prompts_label.grid(row=8, pady=(0, 10))
        
        self.quick_prompts = [
            ("📅 Today", "what day and date is today?"),
            ("🌤️ Weather", "what's the weather in Lahore Pakistan?"),
            ("💻 System", "give me my system info"),
            ("📁 Files", "list files in current directory"),
        ]
        
        for i, (label, prompt) in enumerate(self.quick_prompts):
            btn = ctk.CTkButton(
                self.buttons_frame,
                text=label,
                command=lambda p=prompt: self.set_prompt(p),
                width=100,
                height=35
            )
            btn.grid(row=9 + i, padx=10, pady=3)
        
        # Welcome message
        self.append_chat("System", f"Welcome! I'm your AI Agent.\n\nI have {len(TOOL_MAP)} tools available:\n" +
                        "• System info & monitoring\n• File operations\n• Network tools\n" +
                        "• Web search\n• Calculator\n• And more...\n\n" +
                        "Type your question or task below!", tag="success")
    def append_chat(self, sender: str, text: str, tag: str = None):
        """Add a message to the chat display with clickable URLs."""
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
                msg_tag = None
            
            self.chat_display.insert("end", f"[{timestamp}] ", "timestamp")
            self.chat_display.insert("end", f"{sender.upper()}: ", msg_tag or "sender")
            
            # Parse text for URLs and make them clickable
            # URL regex pattern
            url_pattern = re.compile(r'https?://[^\s\)"\']+')
            
            last_end = 0
            for match in url_pattern.finditer(text):
                # Insert text before URL
                before_url = text[last_end:match.start()]
                self.chat_display.insert("end", before_url)
                
                # Insert clickable URL
                url = match.group()
                url_start = self.chat_display.index("end")
                self.chat_display.insert("end", url)
                url_end = self.chat_display.index("end")
                
                # Create hyperlink tag
                self.chat_display.tag_add(f"link_{last_end}", url_start, url_end)
                self.chat_display.tag_configure(f"link_{last_end}", foreground="#5dade2", underline=True)
                self.chat_display.tag_bind(f"link_{last_end}", "<Button-1>", 
                    lambda e, u=url: self.open_url(u))
                self.chat_display.tag_bind(f"link_{last_end}", "<Enter>",
                    lambda e: self.chat_display.configure(cursor="hand2"))
                self.chat_display.tag_bind(f"link_{last_end}", "<Leave>",
                    lambda e: self.chat_display.configure(cursor="arrow"))
                
                last_end = match.end()
            
            # Insert any remaining text
            if last_end != 0:
                remaining = text[last_end:]
                if remaining:
                    self.chat_display.insert("end", remaining)
            else:
                self.chat_display.insert("end", text)
            
            self.chat_display.insert("end", f"\n\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")
        self.after(0, _update)
    
    def open_url(self, url: str):
        """Open URL in default browser."""
        import webbrowser
        try:
            webbrowser.open(url)
            self.set_status(f"Opened: {url}", "green")
        except Exception as e:
            self.set_status(f"Could not open URL: {str(e)}", "red")
    
    def clear_input(self):
        """Clear the input field."""
        self.user_input.delete("1.0", "end")
    
    def set_prompt(self, prompt: str):
        """Set the input field with a quick prompt."""
        self.user_input.delete("1.0", "end")
        self.user_input.insert("1.0", prompt)
        self.user_input.focus()
    
    def get_chat_content(self) -> str:
        """Get all chat content."""
        return self.chat_display.get("1.0", "end").strip()
    
    def get_last_response(self) -> str:
        """Get the last agent response."""
        content = self.chat_display.get("1.0", "end").strip()
        lines = content.split("\n")
        last_response = []
        capturing = False
        for line in reversed(lines):
            if line.startswith("[") and ("AGENT:" in line.upper()):
                capturing = True
            elif capturing and line.startswith("["):
                break
            if capturing:
                last_response.insert(0, line)
        return "\n".join(last_response).replace("[AGENT]:", "").strip()
    
    def copy_output(self):
        """Copy all chat output to clipboard."""
        content = self.get_chat_content()
        self.copy_to_clipboard(content)
        self.set_status("Copied all output!", "green")
    
    def copy_last_response(self):
        """Copy the last agent response to clipboard."""
        content = self.get_last_response()
        if content:
            self.copy_to_clipboard(content)
            self.set_status("Copied last response!", "green")
        else:
            self.set_status("No response to copy", "red")
    
    def copy_to_clipboard(self, text: str):
        """Copy text to system clipboard."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
        except Exception as e:
            print(f"Clipboard error: {e}")
    
    def format_delete_info(self, delete_info: str) -> str:
        """Format delete confirmation info for display."""
        parts = delete_info.replace("CONFIRM_DELETE:", "").split("|")
        if len(parts) >= 2:
            if parts[1].startswith("FILE:"):
                size = ""
                if len(parts) >= 3 and parts[2].startswith("SIZE:"):
                    size = f" ({int(parts[2].replace('SIZE:', '')):,} bytes)"
                return f"Type: File\nName: {parts[1].replace('FILE:', '')}{size}\nPath: {parts[0]}"
            elif parts[1].startswith("FOLDER:"):
                return f"Type: Empty Folder\nName: {parts[1].replace('FOLDER:', '')}\nPath: {parts[0]}"
        return delete_info
    
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
            self.set_status("Installing...", "orange")
            self.append_chat("System", f"📥 Installing {program_name}...", tag="warning")
            install_result = AgentTools.execute_install(program_name, download_url)
            self.append_chat("System", install_result, tag="success" if "✅" in install_result else "error")
            self.set_status("Ready", "gray")
        
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
        """Main agent logic running in a separate thread."""
        self.set_status("Thinking...", "yellow")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        final_answer = ""
        max_iterations = 8
        
        try:
            for iteration in range(max_iterations):
                # Check for stop signal
                if self.should_stop:
                    self.append_chat("System", "⏹️ Agent processing was stopped.", tag="error")
                    break
                
                self.set_status(f"Thinking... (Step {iteration + 1}/{max_iterations})", "yellow")
                
                try:
                    response = client.chat.completions.create(
                        model=LOCAL_MODEL,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=500
                    )
                except Exception as e:
                    if self.should_stop:
                        break
                    self.append_chat("Error", f"LLM Connection Error: {str(e)}\n\n" +
                                     "Make sure your local LLM server is running at " + LOCAL_LLM_URL, tag="error")
                    break
                except Exception as e:
                    self.append_chat("Error", f"LLM Connection Error: {str(e)}\n\n" +
                                     "Make sure your local LLM server is running at " + LOCAL_LLM_URL, tag="error")
                    break
                
                content = response.choices[0].message.content
                
                # Parse response for tool calls
                action_match = re.search(r"ACTION:\s*(\w+)", content, re.IGNORECASE)
                args_match = re.search(r"ARGS:\s*(.*?)(?:\n|$)", content, re.IGNORECASE | re.DOTALL)
                thought_match = re.search(r"THOUGHT:\s*(.*?)(?:\n|$)", content, re.IGNORECASE | re.DOTALL)
                
                if action_match:
                    if thought_match:
                        thought_text = thought_match.group(1).strip()
                        self.set_status(f"Thinking: {thought_text[:50]}...", "yellow")
                    
                    tool_name = action_match.group(1).strip().lower()
                    raw_args = args_match.group(1).strip() if args_match else ""
                    
                    # Clean args
                    args = raw_args.strip('"').strip("'").strip()
                    
                    if tool_name in TOOL_MAP:
                        self.set_status(f"Executing {tool_name}...", "cyan")
                        try:
                            if args:
                                result = TOOL_MAP[tool_name](args)
                            else:
                                result = TOOL_MAP[tool_name]()
                        except TypeError as te:
                            result = f"Error: Invalid arguments for {tool_name}: {str(te)}"
                        
                        # Handle delete confirmation specially
                        if tool_name == "delete_file":
                            if str(result).startswith("CONFIRM_DELETE:"):
                                # Show confirmation dialog and wait for user response
                                delete_info = str(result)
                                self.pending_delete = delete_info
                                self.show_delete_confirmation(delete_info)
                                # For now, we'll append a message asking for confirmation
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"⚠️ DELETE CONFIRMATION REQUIRED\n{self.format_delete_info(delete_info)}", tag="error")
                                continue
                            else:
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"{tool_name}({args}) → {str(result)[:200]}", tag="tool_call")
                        
                        elif tool_name == "prepare_install_command":
                            if str(result).startswith("CONFIRM_INSTALL:"):
                                install_info = str(result)
                                self.show_install_confirmation(install_info)
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"⚠️ INSTALL CONFIRMATION REQUIRED\nProgram: {args}", tag="warning")
                                continue
                            elif str(result).startswith("ERROR:"):
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"❌ {result}", tag="error")
                                continue
                            else:
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"{tool_name}({args}) → {str(result)[:200]}", tag="tool_call")
                        
                        elif tool_name == "prepare_uninstall_command":
                            if str(result).startswith("CONFIRM_UNINSTALL:"):
                                uninstall_info = str(result)
                                self.show_uninstall_confirmation(uninstall_info)
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"⚠️ UNINSTALL CONFIRMATION REQUIRED\nProgram: {args}", tag="warning")
                                continue
                            elif str(result).startswith("ERROR:"):
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"❌ {result}", tag="error")
                                continue
                            else:
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"{tool_name}({args}) → {str(result)[:200]}", tag="tool_call")
                        
                        elif tool_name == "prepare_update_command":
                            if str(result).startswith("CONFIRM_UPDATE:"):
                                update_info = str(result)
                                self.show_update_confirmation(update_info)
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"⚠️ UPDATE CONFIRMATION REQUIRED\nProgram: {args}", tag="warning")
                                continue
                            elif str(result).startswith("ERROR:"):
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"❌ {result}", tag="error")
                                continue
                            else:
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"{tool_name}({args}) → {str(result)[:200]}", tag="tool_call")
                        
                        elif tool_name == "validate_self_protection":
                            protection_result = str(result)
                            if "PROTECTED" in protection_result:
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"🛡️ SELF-PROTECTION: {protection_result}", tag="error")
                                continue
                            else:
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"{tool_name}({args}) → OK", tag="tool_call")
                        
                        elif tool_name == "shutdown_computer":
                            if str(result).startswith("CONFIRM_SHUTDOWN:"):
                                self.show_shutdown_confirmation(result)
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                continue
                            else:
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"{tool_name}({args}) → {str(result)[:200]}", tag="tool_call")
                        
                        elif tool_name == "prepare_shutdown":
                            if str(result).startswith("CONFIRM_SHUTDOWN:"):
                                self.show_shutdown_confirmation(result)
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                continue
                            else:
                                messages.append({"role": "assistant", "content": content})
                                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                                self.append_chat("Tool", f"{tool_name}({args}) → {str(result)[:200]}", tag="tool_call")
                        
                        elif tool_name == "restart_computer":
                            self.show_restart_confirmation()
                            messages.append({"role": "assistant", "content": content})
                            messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                            continue
                        
                        else:
                            messages.append({"role": "assistant", "content": content})
                            messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                            self.append_chat("Tool", f"{tool_name}({args}) → {str(result)[:200]}", tag="tool_call")
                    else:
                        error_msg = f"Error: Tool '{tool_name}' not found. Available tools: {', '.join(TOOL_MAP.keys())}"
                        messages.append({"role": "user", "content": error_msg})
                        self.append_chat("Error", error_msg, tag="error")
                        self.set_status("Invalid tool, retrying...", "red")
                        continue
                
                # Check for final answer
                elif re.search(r"FINAL ANSWER:", content, re.IGNORECASE):
                    final_answer = re.split(r"FINAL ANSWER:", content, flags=re.IGNORECASE)[-1].strip()
                    break
                
                # Direct response (creative/simple task)
                else:
                    # Check if model is stuck in thought loop
                    if re.search(r"THOUGHT:", content, re.IGNORECASE) and not re.search(r"ACTION:", content, re.IGNORECASE):
                        self.set_status("Correcting agent response...", "orange")
                        messages.append({"role": "user", "content": 
                            "You provided a THOUGHT but no ACTION. Please output the ACTION and ARGS now, or give your FINAL ANSWER."})
                        continue
                    else:
                        final_answer = content.strip()
                        break
            
            if final_answer:
                self.append_chat("Agent", final_answer)
            else:
                # Agent couldn't provide a clear answer - try web search as fallback
                self.set_status("Searching the web...", "cyan")
                self.append_chat("System", "🤔 I couldn't find a clear answer. Let me search the web...", tag="warning")
                
                # Use web search with the original user prompt
                try:
                    web_result = AgentTools.web_search(user_prompt)
                    if not web_result.startswith("Error:") and not web_result.startswith("Search Error"):
                        self.append_chat("Agent", f"📢 Based on my web search:\n\n{web_result}", tag="tool_call")
                    else:
                        self.append_chat("Agent", "I reached the maximum iterations without a clear answer. " +
                                        "Please try a more specific question or task.", tag="error")
                except Exception as e:
                    self.append_chat("Agent", "I reached the maximum iterations without a clear answer. " +
                                    "Please try a more specific question or task.", tag="error")
        
        except Exception as e:
            self.append_chat("Error", f"Unexpected error: {str(e)}", tag="error")
        
        self.should_stop = False
        self.set_status("Ready", "gray")
        self.set_button_state(True)


# --- MAIN ENTRY POINT ---

if __name__ == "__main__":
    app = AgentGUI()
    app.mainloop()
