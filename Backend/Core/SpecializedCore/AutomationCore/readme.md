# AutomationCore

The AI-OS hardware-native executive. AutomationCore implements the bare-metal OS interaction layer — intercepting file system events, managing processes, collecting hardware telemetry, and executing sandboxed system commands.

## Responsibility

Act as Vibhu-Oska's hands in the operating system. Triggered by OrchestratorCore when a prompt matches OS-class keywords.

## Supported Actions (9 total)

| Action | Description |
|---|---|
| `get_system_info` | CPU, memory, disk, GPU telemetry snapshot |
| `list_directory` | List files and directories at a given path |
| `read_file` | Read file content (text, with size limit) |
| `write_file` | Write content to a file path |
| `run_command` | Execute a shell command in a sandboxed subprocess |
| `list_processes` | Enumerate running processes (pid, name, cpu%, mem%) |
| `kill_process` | Terminate a process by PID |
| `watch_filesystem` | Monitor a directory for file system change events |
| `open_application` | Launch an application by name or executable path |

## Safety Architecture

AutomationCore maintains a **command blacklist** that prevents execution of destructive OS operations even if CognitionCore generates a prompt requesting them:

```python
_BLACKLISTED_COMMANDS = {
    "format", "rm -rf", "del /f /s /q", "shutdown", "reboot",
    "mkfs", "dd if=", ":(){ :|:& };:", ...
}
```

Any `run_command` call is sanitized against the blacklist before subprocess execution. The subprocess runs with a timeout (default 30 seconds) and captured stdout/stderr.

## Key File

`AutomationCore.py` — 25.2KB

## Module Boundary Rules

- **No inference logic** — never calls CognitionCore
- **No DB writes** — hardware telemetry is returned as structured dicts, not persisted here
- All subprocess execution is sandboxed with timeout enforcement

## OrchestratorCore Trigger Keywords

```
list files, list directory, run command, execute, open app,
cpu usage, memory usage, system info, disk space,
what processes, kill process, read file, write file,
system status, hardware, gpu info
```
