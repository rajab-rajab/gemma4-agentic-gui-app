# 🤖 Agentic AI - Local LLM Assistant

A powerful desktop AI agent with a modern GUI that interfaces with your local LLM. Features include system monitoring, file operations, web search, network tools, and more.

![Agentic AI Screenshot](screenshot.png)

## Features

- **🧠 Local LLM Integration** - Connects to your local Ollama, LM Studio, or any compatible LLM server
- **🛠️ 65+ Built-in Tools** - System monitoring, file operations, network tools, web search, PowerShell admin tools
- **📁 File Operations** - Create, copy, move, rename, delete, hash files/folders
- **🖥️ Windows Admin** - Services, registry, firewall, event logs, hotfixes, installed programs
- **📦 Program Manager** - Install/uninstall/update programs with safety checks and user confirmation
- **🔄 Update Checker** - Check for updates only when USER requests (no auto-updates)
- **🛡️ Self-Protection** - Cannot delete/modify agent itself or running LLM processes
- **🔗 Clickable URLs** - All web search results have clickable URLs that open in browser
- **🌐 Tavily API** - All web searches use Tavily API for better results
- **💻 Coding Assistant** - Execute code, generate templates, create files
- **🔍 Auto Web Search** - Automatically searches web when unable to answer or code fails
- **🖥️ System Control** - Shutdown/restart/sleep with confirmation dialogs
- **🎨 Modern Dark UI** - Clean, scrollable interface with color-coded messages
- **⚡ Quick Prompts** - One-click buttons for common tasks
- **📋 Copy Functions** - Copy full output or last response to clipboard
- **⏹️ Stop Button** - Interrupt unstable or long-running responses
- **🗑️ Safe Delete** - File deletion with confirmation dialogs and safety restrictions
- **🔒 Safe Operations** - Secure calculator, input validation

---

## 📥 Installation

### 1. Clone or Download
```bash
# If using git
git clone <repository-url>
cd agentic-ai

# Or just download agent.py
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Local LLM Server
<div align="center" markdown="1">
   <sup>Special thanks to:</sup>
   <br>
   <br>
   <a href="https://go.warp.dev/text-generation-webui">
      <img alt="Warp sponsorship" width="400" src="https://raw.githubusercontent.com/warpdotdev/brand-assets/refs/heads/main/Github/Sponsor/Warp-Github-LG-02.png">
   </a>

### [Warp, built for coding with multiple AI agents](https://go.warp.dev/text-generation-webui)
[Available for macOS, Linux, & Windows](https://go.warp.dev/text-generation-webui)<br>
</div>
<hr>

# TextGen

**A desktop app for local LLMs. Open source, no telemetry.** Text, vision, tool-calling, web search. UI + API.

[![GitHub stars](https://img.shields.io/github/stars/oobabooga/textgen?style=for-the-badge&logo=github&logoColor=white&labelColor=black)](https://github.com/oobabooga/textgen)

[![Chat mode](https://raw.githubusercontent.com/oobabooga/screenshots/refs/heads/main/CHAT-4.8.png)](https://raw.githubusercontent.com/oobabooga/screenshots/refs/heads/main/CHAT-4.8.png)

## Get started in 1 minute

Download, unzip, double-click `textgen`. A window opens.

**https://github.com/oobabooga/textgen/releases**

Portable builds for Linux, Windows, and macOS with CUDA, Vulkan, ROCm, and CPU-only options. All dependencies included. Compatible with GGUF (llama.cpp) models.

** OR USE  :**
```bash
# Install Ollama from https://ollama.ai
ollama serve
ollama pull gemma:2b  # or any model you prefer
```

**Using LM Studio:**
- Download from https://lmstudio.ai
- Start the local server
- Default URL: `http://127.0.0.1:1234/v1`

### 4. Run the Application
```bash
python agent.py
```

---

## 🎮 How to Use

### Interface Overview

```
┌─────────────────────────────────────────────────────────┐
│  [Chat Display - Scrollable]                            │
│                                                         │
│  [09:37] YOU: what day is today?                        │
│  [09:37] TOOL: get_datetime(full) → Sunday, May 10, 2026│
│  [09:38] AGENT: Today is Sunday, May 10, 2026.          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  [Input Text Area - Multi-line]                    [📤] │
│  Type your question or task here...                      │
└─────────────────────────────────────────────────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          │         ACTION BUTTONS              │
          │                                    │
          │  [Send ➤]  or  [■ Stop]            │  ← Toggle based on state
          │  [Clear Chat]                       │
          │  [Copy Output]                      │
          │  [Copy Last]                        │
          │  [Clear Input]                      │
          │                                    │
          │  ── Quick Prompts ──                │
          │  [📅 Today]  [🌤️ Weather]          │
          │  [💻 System] [📁 Files]             │
          └────────────────────────────────────┘
```

### ⏹️ Stop Button

When processing starts, the **Send** button is replaced by a **Stop** button. This allows you to:

- **Interrupt unstable responses** - If the agent goes into an infinite loop or produces unwanted output
- **Cancel long operations** - Stop web searches or complex calculations
- **Reset stuck processing** - Force stop and try a new query

Click **Stop** to immediately halt the agent. You can then send a new query.

### Quick Start Examples

**Ask about date/time:**
```
You: what day and date is today?
Agent: Today is Sunday, May 10, 2026.
```

**System information:**
```
You: give me my system info
Agent: CPU: 25% (8 cores) | RAM: 45% used (8GB / 16GB)
```

**Weather check:**
```
You: what's the weather in Lahore Pakistan?
Agent: The weather in Lahore, Pakistan is hot...
     Temperature: 38°C - 40°C
     Conditions: Sunny
```

**File operations:**
```
You: list files in current directory
Agent: [D] Documents/
      [F] notes.txt (1,234 bytes)
      [F] image.png (45,678 bytes)
```

---

## 🛠️ All Available Tools

### 📅 Date & Time

| Tool | Description | Example Args |
|------|-------------|--------------|
| `get_datetime` | Get current date/time | `full`, `date`, `time`, `day`, `iso`, `unix` |

**Format Options:**
- `default` - "2026-05-10 09:37:00"
- `date` - "2026-05-10"
- `time` - "09:37:00"
- `day` - "Sunday"
- `full` - "Sunday, May 10, 2026"
- `full_with_time` - "Sunday, May 10, 2026 at 09:37:00"
- `iso` - ISO 8601 format
- `unix` - Unix timestamp

### 💻 System Information

| Tool | Description |
|------|-------------|
| `get_system_info` | CPU & RAM usage |
| `get_uptime` | System uptime since boot |
| `get_cpu_info` | CPU cores, frequency details |
| `get_memory_info` | Detailed RAM & swap info |
| `get_battery_status` | Battery percentage & charging status |
| `get_processes` | Top processes by memory usage |

### 💾 Disk & Files

| Tool | Description | Args |
|------|-------------|------|
| `list_files` | List directory contents | `path`, `pattern` (optional), `include_hidden` (optional) |
| `read_file` | Read file contents | `filepath`, `max_lines` (optional) |
| `read_file_lines` | Read specific lines | `filepath`, `start_line`, `count` |
| `write_file` | Write to a file | `filepath`, `content`, `append` (optional) |
| `get_file_info` | Detailed file info | `filepath` |
| `get_disk_usage` | Disk space usage | `path` (optional, default: /) |
| `search_files` | Search for files | `pattern`, `path`, `max_results` |

### 🌐 Network Tools

| Tool | Description | Args |
|------|-------------|------|
| `ping_host` | Ping a host | `hostname`, `count` (optional) |
| `check_port` | Check if port is open | `host`, `port` |
| `dns_lookup` | DNS resolution | `hostname` |
| `get_network_info` | List network interfaces | (none) |
| `get_ip_info` | Public IP info | (none) |

### 🔧 Command Execution

| Tool | Description | Args |
|------|-------------|------|
| `run_powershell` | Execute PowerShell command | `command` |
| `run_command` | Execute system command | `command` |

### 🖥️ PowerShell Windows Admin Tools

| Tool | Description | Args |
|------|-------------|------|
| `ps_get_services` | Get Windows services | `status` (all/running/stopped) |
| `ps_service_action` | Start/stop/restart service | `service_name`, `action` |
| `ps_get_eventlog` | Get Event Log entries | `logname`, `count` |
| `ps_get_processes_detailed` | Detailed process list | (none) |
| `ps_get_registry` | Read registry keys | `key_path` |
| `ps_get_scheduled_tasks` | Get scheduled tasks | (none) |
| `ps_get_installed_programs` | List installed programs | (none) |
| `ps_get_environment_vars` | Get environment variables | (none) |
| `ps_get_network_adapters` | Get network adapters | (none) |
| `ps_get_firewall_rules` | Get firewall rules | `enabled_only` |
| `ps_get_disk_partitions` | Get disk/partition info | (none) |
| `ps_get_wifi_networks` | Get available WiFi networks | (none) |
| `ps_get_hotfixes` | Get installed Windows updates | (none) |
| `ps_get_running_tasks` | Get running tasks | (none) |
| `ps_get_systeminfo` | Comprehensive system info | (none) |

### 📦 Program Installation/Uninstall

| Tool | Description | Args |
|------|-------------|------|
| `search_program` | Search online for program | `program_name` |
| `validate_program_safety` | Check program safety | `program_name`, `url` (optional) |
| `get_installed_programs_list` | List installed programs | (none) |
| `check_program_removable` | Check if program can be uninstalled | `program_display_name` |
| `prepare_install_command` | Prepare install with confirmation | `program_name`, `download_url` |
| `prepare_uninstall_command` | Prepare uninstall with confirmation | `program_name` |
| `execute_install` | Execute installation | `program_name`, `download_url` |
| `execute_uninstall` | Execute uninstallation | `program_name`, `uninstall_string` |

### 🔄 Program Updates (User MUST Request)

| Tool | Description | Args |
|------|-------------|------|
| `check_program_updates` | Check for updates online | `program_name` |
| `validate_update_safety` | Validate update source | `program_name`, `download_url` |
| `prepare_update_command` | Prepare update with confirmation | `program_name`, `download_url` |
| `execute_update` | Execute update after confirmation | `program_name`, `download_url` |

### 🛡️ Agent Self-Protection

| Tool | Description | Args |
|------|-------------|------|
| `validate_self_protection` | Check if path is protected | `path` |
| `get_agent_info` | Get agent information | (none) |

### 💻 Coding Assistant

| Tool | Description | Args |
|------|-------------|------|
| `execute_code` | Execute code snippets | `code`, `language` |
| `create_code_file` | Create code file | `filepath`, `content`, `language` |
| `generate_code_template` | Generate code templates | `task`, `language` |
| `check_code_syntax` | Check syntax validation | `code`, `language` |
| `get_code_snippet_info` | Get language info | `language` |

#### 💡 Coding Features

**Supported Languages:**
- 🐍 Python - Full execution support
- 🟨 JavaScript - Node.js execution
- 🔧 Bash/Shell - Command execution
- ⚡ PowerShell - Windows commands
- 🌐 HTML - Template generation
- 🎨 CSS - Style templates
- 🗄️ SQL - Query templates

**Capabilities:**
- Execute code and see output
- Generate code templates
- Check syntax without running
- Create code files
- Get language information
- **Web search for solutions** when code fails

#### 🔍 Auto Web Search Fallback

**IMPORTANT FEATURE:** If the agent cannot answer a question or perform a task, it automatically searches the web.

**When it triggers:**
- User asks about current events or recent information
- User asks about topics outside training data
- User asks for tutorials, guides, or how-to instructions
- Agent reaches maximum iterations without clear answer
- Agent doesn't know the answer to a question

**How it works:**
1. Agent tries to answer using its available tools
2. If unsuccessful after max iterations, it shows a message
3. Agent automatically uses web search to find the answer
4. Results are displayed with clickable URLs

**Example Flow:**
```
You: what is the latest version of React.js?
Agent: (thinking...) [Max iterations reached]
Agent: 🤔 I couldn't find a clear answer. Let me search the web...
Agent: 📢 Based on my web search:

     🔍 Search Results for: latest version of React.js
     ============================================================
     
     1. React.js Official Website
        📎 https://react.dev/
        💬 Current stable version is React 19...
     
     🔗 QUICK LINKS:
        → https://react.dev/
```

#### ⚠️ INSTALL/UNINSTALL SAFETY RULES

1. **ALWAYS Search Online First**
   - Find official download source
   - Verify URL authenticity

2. **Safety Validation**
   - Check for HTTPS (secure connection)
   - Verify official sources
   - Reject pirated software (torrent, crack, keygen)

3. **User Permission ALWAYS Required**
   - Confirmation dialog appears before any install/uninstall
   - User must explicitly approve

4. **Protected System Programs (NEVER Uninstall)**
   - Windows, Microsoft, Kernel, System files
   - Device drivers (Intel, NVIDIA, AMD, Realtek)
   - Runtime libraries (.NET Framework, Visual C++)
   - Boot and recovery programs

5. **Malware Prevention**
   - Reject URLs containing: torrent, crack, keygen, serial, patch
   - Reject programs with suspicious names
   - Warn about third-party download sites

#### System Programs List:
```
windows, kernel, runtime, visual c++, vcruntime, msvc, 
.net framework, dotnet, intel, nvidia, amd, radeon, geforce, 
realtek, audio, graphics, wireless, bluetooth, drivers, boot, recovery
```

```

### 🌐 Web & Search

| Tool | Description | Args |
|------|-------------|------|
| `web_search` | Search the web with clickable URLs | `query` |
| `web_search_simple` | Simple web search with URLs | `query` |
| `search_with_urls` | Search with prominent clickable URLs | `query` |
| `get_weather` | Get weather for location (Tavily API) | `location` |

#### 🌟 URLs Feature

All web search results include **URLs** 

*
### 🔢 Calculator

| Tool | Description | Args |
|------|-------------|------|
| `calculate` | Safe math evaluation | `expression` |

**Supported Operations:**
- Addition: `2 + 3`
- Subtraction: `10 - 4`
- Multiplication: `5 * 6`
- Division: `20 / 4`
- Floor division: `17 // 5`
- Modulo: `17 % 5`
- Power: `2 ** 10`
- Functions: `abs(-5)`, `round(3.7)`, `min(1,2,3)`, `max(1,2,3)`

### 🔐 Security

| Tool | Description | Args |
|------|-------------|------|
| `generate_password` | Generate secure password | `length` (optional), `include_special` (optional) |

### 📁 File System

| Tool | Description | Args |
|------|-------------|------|
| `get_current_directory` | Get current working directory | (none) |
| `change_directory` | Change working directory | `path` |

### 🗑️ Delete Operations (WITH RESTRICTIONS)

| Tool | Description | Args |
|------|-------------|------|
| `delete_file` | Delete file/folder (with restrictions) | `filepath` |
| `confirm_delete` | Confirm deletion after user approval | `filepath` |
| `create_folder` | Create new folder | `folderpath` |
| `create_file` | Create new file | `filepath`, `content` (optional) |
| `copy_file` | Copy file/folder to destination | `source`, `destination` |
| `move_file` | Move file/folder to destination | `source`, `destination` |
| `rename_file` | Rename file/folder | `oldpath`, `newname` |
| `get_file_hash` | Calculate file hash | `filepath`, `algorithm` (md5/sha1/sha256) |

#### ⚠️ DELETE RESTRICTIONS & SAFETY RULES

1. **User Permission Required**
   - A confirmation dialog ALWAYS appears before any deletion
   - User must manually confirm or cancel

2. **Protected Paths (CANNOT BE DELETED)**
   - System partitions: `C:`, `D:`, `E:`, etc.
   - Linux root: `/`
   - System directories: `Windows`, `System32`, `SysWOW64`
   - Linux system dirs: `/bin`, `/etc`, `/boot`, `/dev`, `/lib`, `/proc`, `/sys`, `/var`

3. **Protected Files (CANNOT BE DELETED)**
   - System files: `.sys`, `.dll`
   - Boot files: `bootmgr`, `boot.ini`, `config.sys`, `autoexec.bat`

4. **Agent Self-Protection (CANNOT BE DELETED)**
   - Agent files: `agent.py`, `agent.exe`, `requirements.txt`, `README.md`
   - Virtual environments: `venv`, `.venv`, `env`
   - LLM files: `ollama.exe`, `gemma`, `mistral`, `llama.cpp`
   - Python executables: `python.exe`, `pythonw.exe`, `py.exe`

5. **Folder Restrictions**
   - Cannot delete non-empty folders
   - Only empty folders can be deleted
   - Files inside protected directories cannot be deleted

6. **One at a Time**
   - Only one file or folder can be deleted per operation
   - Bulk deletions are not allowed

#### Example Delete Flow:
```
You: delete test.txt
Agent: ⚠️ DELETE CONFIRMATION REQUIRED
       Type: File
       Name: test.txt
       Path: C:\Users\John\Documents\test.txt
       Size: 1,234 bytes
       
       [CONFIRM DIALOG APPEARS]
       - Click "🗑️ DELETE" to confirm
       - Click "✖ Cancel" to abort
```

**Error Messages:**
- "Error: CANNOT DELETE protected partition" - Attempted to delete system drive
- "Error: CANNOT DELETE system directory" - Attempted to delete Windows/System folder
- "Error: Cannot delete non-empty folder" - Folder contains files
- "Error: CANNOT DELETE system file" - Attempted to delete system file

### ⚙️ Process Management

| Tool | Description | Args |
|------|-------------|------|
| `get_processes` | List running processes | `limit` (optional) |
| `kill_process` | Terminate a process | `PID` |

### 📋 Clipboard

| Tool | Description | Args |
|------|-------------|------|
| `get_clipboard` | Get clipboard content | (none) |
| `set_clipboard` | Set clipboard text | `text` |


3. **Never Auto-Shutdown**
   - Never shutdown without user request
   - Never shutdown automatically

#### Example Shutdown Flow:
```
You: shutdown the computer
Agent: ⚠️ SYSTEM SHUTDOWN CONFIRMATION REQUIRED

       ⚠️ WARNING:
       • ALL programs will be closed
       • Unsaved work will be LOST
       • Your computer will shutdown

       [CONFIRM DIALOG APPEARS]
       - Click "🖥️ SHUTDOWN" to confirm
       - Click "✖ Cancel" to abort
```

---

## 📝 Usage Examples

### 💻 Coding Examples
```
You: write a python function to check prime numbers
Agent: 📝 Here is a Python function to check prime numbers:

```python
def is_prime(n):
    """Check if a number is prime."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

# Test
print(is_prime(17))  # True
print(is_prime(15))  # False
```

You: execute this code
Agent: 📤 Output:
       True
       False

You: create a web server in python
Agent: 📝 Python Web Server Template:

```python
import http.server
import socketserver

PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()
```

You: write a javascript function to reverse a string
Agent: 📝 JavaScript function:

```javascript
function reverseString(str) {
    return str.split('').reverse().join('');
}

console.log(reverseString("Hello World"));
```

You: execute this js code
Agent: 📤 Output:
       dlroW olleH
```

### Date & Time Queries
```
You: what day is it today?
Agent: Today is Sunday.

You: what's today's date?
Agent: The date is May 10, 2026.

You: what time is it?
Agent: The current time is 09:37:00.
```

### System Monitoring
```
You: show me my system stats
Agent: CPU: 25% | RAM: 45% (8GB / 16GB)
      Uptime: 3d 5h 12m

You: how much disk space do I have?
Agent: Path: C:\
      Total: 476 GB
      Used: 234 GB (49%)
      Free: 242 GB
```

### File Operations
```
You: show files in Documents folder
Agent: [D] Projects/
      [F] report.pdf (2.3 MB)
      [F] budget.xlsx (156 KB)

You: read the first 20 lines of notes.txt
Agent: Line 1: Hello World
      Line 2: This is a test file
      ...

You: create a new folder called "Projects"
Agent: ✅ Created folder: Projects
      Path: C:\Users\John\Documents\Projects

You: create a file called notes.txt
Agent: ✅ Created file: notes.txt
      Path: C:\Users\John\Documents\notes.txt
      Size: 0 bytes

You: copy report.pdf to Projects folder
Agent: ✅ Copied file: report.pdf
      To: C:\Users\John\Documents\Projects\report.pdf

You: rename old.txt to new.txt
Agent: ✅ Renamed: old.txt → new.txt
      New path: C:\Users\John\Documents\new.txt

You: get md5 hash of report.pdf
Agent: MD5=a1b2c3d4e5f6...
```

### 🖥️ PowerShell Windows Admin
```
You: show me all running services
Agent: Name        DisplayName              Status
      ----        -----------              ------
      wuauserv    Windows Update          Running
      WinDefend   Windows Defender        Running
      ...

You: get installed programs
Agent: DisplayName        Version    Publisher
      ----------        -------    --------
      Python 3.11       3.11.5     Python Software
      VS Code          1.85.0     Microsoft
      ...

You: show my wifi networks
Agent: SSID: MyHomeNetwork
      BSSID: AA:BB:CC:DD:EE:FF
      Signal: 85%
      Security: WPA2

You: get event log errors
Agent: TimeGenerated  EntryType  Source      Message
      --------------  ---------  ------      -------
      5/10 09:00      Error      Service     Failed to start...

You: show firewall rules
Agent: Name              Direction  Action  Enabled
      ----              ---------  ------  -------
      CoreNet-Debug     Inbound    Allow   True
      File and Print    Inbound    Allow   True
      ...
```
      Line 20: End of preview
```

### Network Diagnostics
```
You: check if google.com is reachable
Agent: PING google.com
      Reply from 142.250.x.x: bytes=32 time=15ms

You: what's my public IP?
Agent: Public IP: 203.0.113.42
      City: Lahore
      Country: Pakistan
      ISP: Pakistan Telecom
```

### Web Search
```
You: latest news about AI
Agent: 🔍 Search Results for: latest news about AI
      ============================================================
      
      1. AI News - OpenAI Blog
         📎 https://openai.com/blog
         💬 Latest developments in AI research...
      
      2. AI News - TechCrunch
         📎 https://techcrunch.com/category/ai
         💬 Startup funding and AI technology news...
      
      ============================================================
      🔗 QUICK LINKS - Click or copy these URLs:
      ------------------------------------------------------------
        1. OpenAI Blog: https://openai.com/blog
        2. TechCrunch AI: https://techcrunch.com/category/ai
      
      [💡 Click any URL above to open in your browser]

You: what's the weather in Tokyo?
Agent: Weather in Tokyo, Japan:
      Temperature: 22°C
      Conditions: Partly Cloudy
      Humidity: 65%
```

### Calculator
```
You: what is 125 * 17 + 300 / 25?
Agent: Result: 2,137

You: calculate square root of 2025
Agent: Result: 45
```

### Password Generation
```
You: generate a 24 character password
Agent: Generated password: aB3$kL9@mN2@pQ5#rT8!
```

### Program Update (User Must Request)
```
You: check for updates for Python
Agent: 🔍 Checking for updates: Python...
      ✅ OFFICIAL: Python 3.12.4 Download
      URL: https://www.python.org/downloads/
      ...

You: update Python
Agent: [CONFIRM DIALOG]
      Program: Python
      URL: https://www.python.org/downloads/python-3.12.4.exe
      [Click "🔄 UPDATE" to confirm]
```

### Agent Self-Protection
```
You: delete agent.py
Agent: ❌ SELF-PROTECTION: Cannot delete 'agent.py' - this is a critical agent file

You: delete ollama folder
Agent: ❌ SELF-PROTECTION: Cannot delete LLM related files - this is critical for LLM operation
```

### Process Management
```
You: show my top processes
Agent: Top Processes by Memory:
      PID: 1234 | chrome.exe | CPU: 5.2% | RAM: 12.3%
      PID: 5678 | code.exe | CPU: 8.1% | RAM: 6.7%
      ...

You: kill process with PID 9999
Agent: Terminated process: app.exe (PID: 9999)
```

---

## ⚙️ Configuration

Edit these variables at the top of `agent.py`:

```python
# LLM Configuration
LOCAL_LLM_URL = "http://127.0.0.1:5000/v1"  # Your LLM server URL
LOCAL_MODEL = "gemma"  # Your model name

# Tavily API (for enhanced web search)
# export TAVILY_API_KEY=your_api_key
```

---

## 🔧 Troubleshooting

### LLM Connection Error
**Problem:** "LLM Connection Error"
**Solution:**
1. Make sure your LLM server is running
2. Check the URL in `LOCAL_LLM_URL`
3. Verify the model name in `LOCAL_MODEL`

### Web Search Not Working
**Problem:** "Tavily API not configured"
**Solution:**
1. Get free API key from [tavily.com](https://tavily.com)
2. Set environment variable: `export TAVILY_API_KEY=your_key`

### Command Not Found
**Problem:** Tool execution fails
**Solution:**
1. Check if the command exists on your system
2. Some tools require admin privileges
3. Verify paths are correct

---

### Agent Self-Protection Examples
```
You: delete agent.py
Agent: ❌ SELF-PROTECTION: Cannot delete 'agent.py' - this is a critical agent file
      This is a protected file for the agent's operation.

You: modify my requirements.txt
Agent: ❌ SELF-PROTECTION: Cannot modify 'requirements.txt' - this is a critical agent file

You: delete ollama folder
Agent: ❌ SELF-PROTECTION: Cannot modify LLM related files
      This is critical for the LLM server operation.
```

### System Shutdown Example
```
You: shutdown
Agent: ⚠️ SYSTEM SHUTDOWN CONFIRMATION REQUIRED

       🖥️ WARNING:
       • ALL programs will be closed
       • Unsaved work will be LOST
       • Your computer will shutdown

       [CONFIRM DIALOG]
       - Click "🖥️ SHUTDOWN" to confirm
       - Click "✖ Cancel" to abort

You: [clicks SHUTDOWN]
Agent: 🖥️ Shutting down computer... Goodbye!

You: restart my computer
Agent: ⚠️ SYSTEM RESTART CONFIRMATION REQUIRED

       [CONFIRM DIALOG]
       - Click "🔄 RESTART" to confirm
       - Click "✖ Cancel" to abort
```

---

## 📄 License

MIT License - Feel free to modify and use for any purpose.

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Add new tools following the existing patterns
3. Update this README with new tool documentation
4. Test thoroughly before submitting
AGENT Mr. PERFECT AND GEMMA 4 E4B PLUS POINTS
Here is a comprehensive list of the "Plus Points" for my project.

The "Heart & Brain" Architecture (Conceptual Innovation)

Dual-Layer Intelligence: Instead of a generic chatbot, I have created a synergy between the Heart (Gemma 4 E4B) for high-level reasoning and the Brain (Mr. Perfect) for precise and exact and error free system execution. Intent Recognition: The system doesn't just "chat"; it also understands and uses engineering intent. If a user asks to "Fix the PC or want to run system commands," the agent knows to trigger diagnostic tools and commands rather than just giving advice.
Powered by Gemma 4 E4B (Model Optimization)

Engineering-for-Business (E4B) Precision: I chose the E4B variant specifically for its superior performance in generating high level technical programming code (Python, PowerShell, C++) and following complex and difficult business logic.
Local Performance: By using the it-Q4_K_M GGUF quantization, I have achieved a perfect balance: high intelligence (reasoning) and accuracy with low latency (speed) on consumer-grade hardware. As it uses minimal resources in RAM and disk space.
Private & Offline: The model runs 100% locally. A protected environment where no data ever leaves the user's machine, making it suitable and important for corporate and sensitive engineering environments.
Professional Grade Toolset (65+ Built-in Tools)

OS-Level Integration: While most AI agents are "sandboxed," Mr. Perfect has deep integration with Windows via PowerShell Admin Tools, allowing for real-time system monitoring, registry edits, and service management.
The Developer's Swiss Army Knife: Built-in capabilities for Code Creation, Creating files and folders, Syntax Checking, and Immediate Execution across multiple languages (Python, HTML, JS).
Web-Augmented Reasoning: When local knowledge isn't enough, the agent autonomously and efficiently uses the Tavily API to fetch real-time data, presenting it with Verified URLs.
Advanced Session Management (The "Black Box")

Persistence (Save/Load): Its ability to save sessions to JSON transforms the agent from a temporary chat into a persistent workspace for developers and software engineers.
Auditability: The JSON logs provide a transparent and neat record of each and every step of "Action" and "Argument," which is critical for business stability, accountability and debugging.
Ease of Any time Context Restoration: Users can stop and close mid-project, save their current session, and reload it later to pick up and start exactly where Gemma 4 left off.
"Responsible AI" & Safety (The Self-Protection Layer)

Self-Preservation Logic: The agent is hard-coded to never delete its own source code (agent.py) or the LLM binaries. This prevents "Agentic Suicide" or accidental system damage.
System Guardrails: It recognizes protected Windows directories and system files, refusing to perform "Delete" operations on critical OS components.
Human-in-the-Loop: Critical actions (like system shutdown or bulk file deletion) require explicit user confirmation through the modern GUI.
Modern & Intuitive UX (CustomTkinter GUI)

Clean Dark Theme: A professional, tech-focused interface that reduces eye strain for long engineering and coding sessions.
Dynamic Status Feedback: The UI provides real-time updates (e.g., "Step 1/4: Tool Execution: "), so the user is never left wondering what the agent is "thinking."
Rich Text Features: Support for URLs, color-coded message tags. Quick Prompt buttons for common tasks.
Resilient Execution (The 4-Iteration Loop)

Autonomous Problem Solving: The agent uses a multi-step thinking process while working with Gemma4. If a code execution fails, it reads the error, searches for a fix, modifies the code, and tries again—all in one session.
Synthetic Final Answers: if the agent exhausts its loop during a tool call, it provides a logical summary of its actions, ensuring the user is always well informed and aware.
Clean and neat Code & High Portability

Single-File Power: Most of the core logic is contained in agent.py, making it incredibly easy for other developers to download, inspect, and run.
Standardized Data: By using standard JSON for sessions and Markdown for code, your project integrates perfectly into existing developer workflows (like GitHub and VS Code). I am still working on Install, Uninstall, Update, Shutdown and Restart functionalities. However, most of powershell tools are working fine.
---

**Made with ❤️ for local AI enthusiasts**
