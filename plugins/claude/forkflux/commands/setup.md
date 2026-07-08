---
description: Configure ForkFlux as your statusline
allowed-tools: Bash, Read, Edit, AskUserQuestion, Write
---

**Note**: Placeholders like `{PYTHON_PATH}`, `{SCRIPT_PATH}`, and `{API_KEY}` should be substituted with actual detected or user-provided values.

## Step 1: Detect Python Runtime

Check if Python 3 is installed and available in the system.

**macOS/Linux / Windows (Git Bash)**:
```bash
command -v python3 2>/dev/null
```

**Windows (PowerShell)**:

```powershell
if (Get-Command python3 -ErrorAction SilentlyContinue) { (Get-Command python3).Source } elseif (Get-Command python -ErrorAction SilentlyContinue) { (Get-Command python).Source } else { Write-Output "" }
```

If the output is empty, stop the setup and tell the user they need to install Python 3 (from python.org) to use the ForkFlux statusline.

## Step 2: Ensure API Credentials are Set

The ForkFlux script requires the `FORKFLUX_API_KEY` environment variable to authenticate requests (and optionally `FORKFLUX_API_URL` if using a custom endpoint).

Instruct the user to add these variables to their system or shell configuration and **explicitly remind them to apply the changes**.

Tell the user:
> "To use the ForkFlux statusline, your API key must be set in your environment variables."
>
> **macOS/Linux (Zsh/Bash)**:
> ```bash
> # 1. Add this line to your ~/.zshrc or ~/.bashrc:
> export FORKFLUX_API_KEY="your_api_key_here"
>
> # 2. Apply the changes to your current terminal:
> source ~/.zshrc  # or source ~/.bashrc
> ```
>
> **Windows (PowerShell)**:
> ```powershell
> # 1. Add to your PowerShell profile (open with `notepad $PROFILE`):
> $env:FORKFLUX_API_KEY="your_api_key_here"
>
> # 2. Apply the changes:
> . $PROFILE
> ```

Use `AskUserQuestion` to confirm:
- header: "Environment Variables"
- question: "Have you set the FORKFLUX_API_KEY and applied the changes (e.g., by running `source ~/.zshrc` or opening a fresh terminal)?"
- options:
  - "Yes, continue setup"
  - "No, cancel setup"

If they choose to cancel, stop the setup.

## Step 3: Write the ForkFlux Script

We need to save the ForkFlux Python script locally so the statusline can execute it.

Define the path:

* macOS/Linux: `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/forkflux`
* Windows (PowerShell): `Join-Path (if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME ".claude" }) "plugins\forkflux"`

Create this directory if it doesn't exist.
Inside this directory, write the following Python code to a file named `statusline.py`:

```python
import json
import urllib.error
import urllib.request
import os

BASE_URL = os.getenv("FORKFLUX_API_URL") or "http://localhost:8000/api/v1"
URL = f"{BASE_URL}/jobs?limit=5&status=published&status=in_progress"
TOKEN = os.getenv("FORKFLUX_API_KEY")

def fetch_and_display_data():
    req = urllib.request.Request(URL)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            raw_data = response.read().decode("utf-8")

            if status_code == 200:
                try:
                    data = json.loads(raw_data)
                    if not isinstance(data, list):
                        print("Error: Expected a JSON array but received a different format.")
                        return
                    if not data:
                        print("ForkFLux: there are no any jobs.")
                        return

                    display_table(data)

                except json.JSONDecodeError:
                    print("Error: Failed to parse response as JSON.")
            else:
                print(f"Unexpected response status: {status_code}")

    except urllib.error.HTTPError as e:
        print(f"\n[HTTP Error]: {e.code} — {e.reason}")
        try:
            error_body = e.read().decode("utf-8")
            print(f"Server response details: {error_body}")
        except Exception:
            pass
    except urllib.error.URLError as e:
        print(f"\n[Connection error]: {e.reason}")
    except Exception as e:
        print(f"\n[An unexpected error occurred]: {e}")

def display_table(data):
    headers = [
        "id", "summary", "status", "priority",
        "source_agent", "assignee_agent", "target_role", "created_at"
    ]
    key_mapping = {
        "id": "id", "summary": "summary", "status": "status",
        "priority": "priority", "source_agent": "source_agent_label",
        "assignee_agent": "assignee_agent_label", "target_role": "target_role_key",
        "created_at": "created_at"
    }

    col_widths = {h: len(h) for h in headers}

    for row in data:
        for h in headers:
            val = str(row.get(key_mapping[h], ""))
            if len(val) > col_widths[h]:
                col_widths[h] = len(val)

    def get_sep_line():
        parts = ["-" * (col_widths[h] + 2) for h in headers]
        return "+" + "+".join(parts) + "+"

    def format_row(row_data_dict_or_list, is_header=False):
        row_parts = []
        for h in headers:
            if is_header:
                val = h
            else:
                val = str(row_data_dict_or_list.get(key_mapping[h], ""))
            row_parts.append(f" {val.ljust(col_widths[h])} ")
        return "|" + "|".join(row_parts) + "|"

    print("\nForkFlux jobs. Just say `claim job <ID>`:")
    print(get_sep_line())
    print(format_row({}, is_header=True))
    print(get_sep_line())

    for row in data:
        print(format_row(row))

    print(get_sep_line())

if __name__ == "__main__":
    fetch_and_display_data()
```

## Step 4: Backup Existing Config

Protect the user's current settings before modifying `settings.json`.

**macOS/Linux**:

```bash
SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
if [ -f "$SETTINGS" ]; then
  BACKUP_PATH="${SETTINGS}.bak.$(date +%Y%m%d-%H%M%S)"
  cp "$SETTINGS" "$BACKUP_PATH"
  echo "Backup created at: $BACKUP_PATH"
fi
```

**Windows (PowerShell)**:

```powershell
$settingsPath = if ($env:CLAUDE_CONFIG_DIR) { Join-Path $env:CLAUDE_CONFIG_DIR "settings.json" } else { Join-Path $HOME ".claude\settings.json" }
if (Test-Path $settingsPath) {
  $backupPath = "${settingsPath}.bak.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
  Copy-Item $settingsPath $backupPath -ErrorAction Stop
  Write-Host "Backup created at: $backupPath"
}
```

If `settings.json` already contains a `statusLine.command` that doesn't say "forkflux", use `AskUserQuestion` to ask the user if they want to overwrite their existing statusline. If they say no, cancel the setup.

## Step 5: Apply Configuration

Generate the command to run the Python script. Since the environment variables are handled by the user's shell, we simply need to invoke the script.

**Command Format (All Platforms):**
```bash
"{PYTHON_PATH}" "{SCRIPT_PATH}"

```

Read `settings.json`, merge the new configuration, and write it back:

```json
{
  "statusLine": {
    "type": "command",
    "command": "\"{PYTHON_PATH}\" \"{SCRIPT_PATH}\""
  }
}

```

*Make sure to preserve any other existing keys in `settings.json`.*

## Step 6: Finish and Restart

After successfully writing the config, display a success message to the user:

> ✅ **ForkFlux statusline installed successfully!**
>
> **Important:** Claude Code needs to inherit your new `FORKFLUX_API_KEY`.
> Please type `/quit` to exit completely. Make sure you have run `source ~/.zshrc` or `source ~/.bashrc` (or opened a new terminal window), and then launch `claude` again.
> Your ForkFlux jobs will appear below the input bar!
