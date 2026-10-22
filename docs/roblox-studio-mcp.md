# Roblox Studio MCP setup for omp

Connects [omp](https://github.com/can1357/oh-my-pi) to a running Roblox Studio session through Studio's built-in MCP server. Once connected, the agent can read the data model, edit scripts, run Luau, insert assets, and drive play mode.

Sources: [Roblox: Connect to the Roblox Studio MCP server](https://create.roblox.com/docs/studio/mcp), omp `mcp-config.md`.

## How it works

- The MCP server is built into Roblox Studio. It is not a separate package to install.
- The server runs as a local process and talks to omp over `stdio`.
- omp launches the process via `.omp/mcp.json`. The server then relays requests to your open Studio session.
- Studio must be running with the MCP server enabled, or the launched process exits and omp reports the server as failed.

## Configuration

`.omp/mcp.json` (project scope, committed to this repo) contains this entry. The file also holds the entries for the other servers, see the [README](../README.md):

```json
{
  "$schema": "https://raw.githubusercontent.com/can1357/oh-my-pi/main/packages/coding-agent/src/config/mcp-schema.json",
  "mcpServers": {
    "Roblox_Studio": {
      "type": "stdio",
      "command": "cmd.exe",
      "args": ["/c", "%LOCALAPPDATA%\\Roblox\\mcp.bat"]
    }
  }
}
```

Notes:

- `.omp/mcp.json` is omp's native project-level MCP file. It applies only when omp runs in this repo.
- omp only expands `${VAR}` placeholders. `%LOCALAPPDATA%` is passed through untouched and expanded by `cmd.exe`.
- The server name `Roblox_Studio` matches the name in Roblox's own examples.

### macOS

Roblox documents a different launch command on macOS. Because `.omp/mcp.json` is committed and the entry above is Windows-specific, macOS users should put this entry in their user-level config (`~/.omp/agent/mcp.json`) instead:

```json
{
  "mcpServers": {
    "Roblox_Studio": {
      "type": "stdio",
      "command": "/Applications/RobloxStudio.app/Contents/MacOS/StudioMCP"
    }
  }
}
```

This entry comes from the Roblox docs and has not been tested in this repo.

## Setup steps

1. Install the latest Roblox Studio.
2. In Studio, open **Assistant**, click **…** ⟩ **Manage MCP Servers**, and turn on **Enable Studio as MCP server**.
3. Start (or restart) omp from this repo. omp discovers `.omp/mcp.json` automatically.
4. Confirm the connection (see below).

Alternative: Studio's **Quick connect** dropdown can configure some clients automatically. omp is not in Roblox's quick connect list (Antigravity, Codex CLI, Claude Code, Claude Desktop, Cursor, Gemini CLI, Visual Studio Code), so use the JSON config above.

## Verify the connection

- In Studio: **Assistant** ⟩ **…** ⟩ **Manage MCP Servers**. A green indicator under **Enable Studio as MCP server** shows the number of connected clients.
- In omp: run `/mcp list` and check that `Roblox_Studio` is connected.

## Available tools

Every tool call takes a `studio_id` parameter that selects the target Studio instance. Use `list_roblox_studios` to look up IDs.

| Area | Tools |
| --- | --- |
| Scripts | `script_read`, `multi_edit`, `script_search`, `script_grep` |
| Asset and content generation | `generate_mesh`, `generate_material`, `generate_procedural_model`, `wait_job_finished`, `search_asset`, `insert_asset`, `upload_image`, `store_image` |
| Data model exploration | `subagent` (`explore`, `playtest`), `search_game_tree`, `inspect_instance` |
| Luau execution | `execute_luau` (requires `datamodel_type`: Edit, Client, or Server) |
| Playtesting | `get_studio_state`, `start_stop_play`, `get_console_output`, `screen_capture` |
| Player input simulation | `character_navigation`, `user_keyboard_input`, `user_mouse_input` |
| Documentation and skills | `http_get`, `skill` |
| Session management | `list_roblox_studios` |

See the Roblox docs for per-tool behavior and limits.

### Multiple Studio instances

One client can connect to several running Studio instances. Call `list_roblox_studios` to get each instance's name, Studio instance ID, and place ID, then pass the chosen ID as `studio_id`. Local places without a place ID are listed by name only.

## Troubleshooting

### `MCP subprocess closed stdout before responding`

omp launched the command and it exited immediately. When this config was first added on the author's machine, `%LOCALAPPDATA%\Roblox\mcp.bat` did not exist, which produced exactly this error. Check:

1. The file exists: `dir %LOCALAPPDATA%\Roblox\mcp.bat`.
2. **Enable Studio as MCP server** is turned on in Studio (see Setup steps).
3. Studio is on the latest version. The built-in MCP server is a recent addition, so an old Studio build won't have it. Studio's active install is registered under `HKCU\Software\Classes\roblox-studio\shell\open\command` and lives in `%LOCALAPPDATA%\Roblox\Versions\version-*\`. If that folder's `RobloxStudioBeta.exe` is many months old, launch Studio and let it update, then enable the MCP server again.
4. Both Studio and omp were restarted after enabling.

If the file is still missing after all of that, see the Roblox docs or DevForum for the current install location. This repo does not document a path other than the one Roblox publishes.

### Server not listed in omp

- Run omp from the repo root so `.omp/mcp.json` is found.
- Validate the JSON. A missing comma or bracket stops the file from loading.
- After editing the config, run `/mcp reload` or restart omp.

### Config changes not taking effect

omp's `disabledServers` list in `~/.omp/agent/mcp.json` hides a server by name regardless of the project entry. Check there if `Roblox_Studio` is configured but never appears.

## Security

- MCP clients can read and modify content in your open Roblox places. Connect only clients you trust.
- omp treats committed MCP definitions as trusted input, and `stdio` entries run arbitrary commands. Review `.omp/mcp.json` in any checkout before opening it with omp.
