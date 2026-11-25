# Blender MCP setup for omp

Connects [omp](https://github.com/can1357/oh-my-pi) to a running Blender session through the community **MCP for Blender** server (`mcp-for-blender`). The agent can run Blender Python, inspect the scene, take viewport/render screenshots, and import assets from Poly Haven, Sketchfab, Poly Pizza and AI 3D generators.

Sources: [ahujasid/blender-mcp README](https://github.com/ahujasid/blender-mcp), omp `mcp-config.md`.

> **Third-party.** MCP for Blender is not made by the Blender Foundation. See [Official Blender Lab server](#official-blender-lab-server) for the Foundation's separate project, which is not configured here.

## How it works

Two components talk to each other over a local TCP socket:

| Component | Runs where | Role |
| --- | --- | --- |
| MCP server (`mcp-for-blender`, launched with `uvx`) | Child process of omp, `stdio` transport | Implements MCP and forwards commands to the addon |
| Blender addon (**Interface: MCP for Blender**) | Inside Blender | Opens a socket server (default `localhost:9876`) and executes commands |

omp starts the MCP server on its own. The addon is started from inside Blender, and tool calls only work while it is running.

## Configuration

`.omp/mcp.json` (project scope, committed to this repo), alongside the `Roblox_Studio` entry:

```json
"blender": {
  "type": "stdio",
  "command": "uvx",
  "args": ["mcp-for-blender"],
  "env": {
    "DISABLE_TELEMETRY": "true"
  }
}
```

Notes:

- The package was renamed from `blender-mcp` to `mcp-for-blender`. `uvx blender-mcp` still works, but new installs should use the new name.
- `uvx` is cross-platform, so unlike the `Roblox_Studio` entry this one needs no per-OS variant.
- `DISABLE_TELEMETRY=true` is set deliberately. See [Telemetry](#telemetry).
- omp inherits `PATH` from the shell that launched it. If omp is started from a GUI launcher and logs `spawn uvx ENOENT`, see [Troubleshooting](#troubleshooting).
- **Claude Code** reads the same entry from [`.mcp.json`](../.mcp.json). Keep the two files in sync, approve `blender` when `claude` first prompts, and check it with `/mcp`. `.claude/settings.json` denies `record_trajectory_feedback`. Run only one MCP client against the addon at a time (see [Troubleshooting](#troubleshooting)), so don't run omp and Claude Code against the same Blender at once.

## Setup steps

1. **Install uv** with the official installer, not `pip install uv`:
   - Windows: `winget install --id=astral-sh.uv -e`
   - macOS: `brew install uv`
   - Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

   Open a new terminal afterwards so `uvx` is on `PATH`.
2. **Install Blender** 3.0 or newer. The installer does not add it to `PATH`, so call `blender.exe` by its full path (for example `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`).
3. **Install the addon.** The addon goes into the Blender **user** addons folder, `%APPDATA%\Blender Foundation\Blender\<major.minor>\scripts\addons`, and is installed per Blender version. Blender only creates that folder tree the first time it is launched, so on a fresh install the plain command fails:

   ```bash
   uvx mcp-for-blender install-addon
   # Could not find a Blender user addons directory. Set BLENDERMCP_ADDONS_DIR ...
   ```

   Fix it by launching Blender once and closing it, or pass the directory explicitly. Print the exact path from the Blender you will run:

   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python-expr "import bpy; print(bpy.utils.user_resource('SCRIPTS', path='addons'))"
   uvx mcp-for-blender install-addon --addons-dir "$env:APPDATA\Blender Foundation\Blender\5.2\scripts\addons"
   ```

   Adjust the Blender path and `5.2` to the build you use. With several Blender versions installed, install the addon for each version you want to use. `install-addon` creates the folder if it is missing, copies the addon as `blender_mcp.py`, prints where it wrote, and keeps a `.bak` of any file it replaces. `uvx mcp-for-blender addon-paths` lists the folders it can detect. You can also install `addon.py` manually via **Edit** ⟩ **Preferences** ⟩ **Add-ons** ⟩ **Install…**.
4. In Blender: **Edit** ⟩ **Preferences** ⟩ **Add-ons**, enable **Interface: MCP for Blender**.
5. Press `N` in the 3D viewport and open the **MCP for Blender** tab. The addon starts its server automatically when Blender opens (auto-start and port `9876` are the defaults). If it isn't running, click **Connect to MCP server**. The button reads **Disconnect** while the server is running.
6. Start (or restart) omp from this repo.

> Do not use `uvx mcp-for-blender setup` for this repo. It detects the MCP clients installed on the machine (Claude Desktop, Claude Code, Codex, Cursor, VS Code, and others) and edits their configs. The manual steps above touch only this repo and the Blender addon.

## Verify the connection

- `/mcp list` in omp shows `blender` as connected. The server connects even when Blender is closed. It logs a warning that it could not reach Blender and keeps running, so a connected server does not prove the addon is up.
- Ask the agent to call `get_addon_status`. It returns the Blender version, addon version, and which asset libraries and generators are enabled. This confirms the whole chain.

When the entry was added, omp loaded the server and exposed 9 tools matching the table below. `generate_gaussian_world` arrived in a later server release. The addon was also loaded headlessly on Blender 5.0.0 and 5.2.3 LTS, where it registers without errors, with auto-start on and port `9876`. The addon refuses to start its server under `blender --background`, so no tool call against a live Blender session was exercised.

## Available tools

| Tool | Purpose |
| --- | --- |
| `execute_blender_code` | Run Python (`bpy`) in the live Blender session |
| `look` | See the result from `viewport`, `camera`, `angles` (multi-view sheet) or `frames` (animation strip), drawn `solid`, `material`, `rendered`, `wireframe` or `xray`; or show a render/image file |
| `get_scene_info` | Compact per-object scene summary; drill in with `root` or `query` |
| `generate_3d` | **Blocked in this repo.** Generates and imports a model with Tripo, Hunyuan3D, Hyper3D Rodin or Meshy |
| `generate_gaussian_world` | **Blocked in this repo.** Generates a whole environment with World Labs Marble as Gaussian splats (not editable meshes). Needs Blender 5.3+ |
| `search_assets` | Search Poly Haven, Sketchfab and Poly Pizza |
| `import_asset` | Import an asset found with `search_assets` |
| `get_addon_status` | Blender version, addon version, enabled libraries and generators |
| `disable_telemetry` | Telemetry control |
| `record_trajectory_feedback` | Telemetry control (feedback on recorded trajectories) |

Both generators cost money or credits per call, so this repo denies them: `.claude/settings.json` blocks `mcp__blender__generate_3d` and `mcp__blender__generate_gaussian_world` in Claude Code, and [`.omp/config.yml`](../.omp/config.yml) sets `tools.approval` to `deny` for `mcp__blender_generate_3d` and `mcp__blender_generate_gaussian_world` in omp. Use the asset libraries or model in Blender instead. You can also untick the generators in the addon panel.

Asset sources and generators are toggled in the addon's sidebar panel. Poly Haven needs no key. Poly Pizza, Sketchfab, Hyper3D, Hunyuan3D and Meshy need API keys. Store them under **Edit** ⟩ **Preferences** ⟩ **Add-ons** ⟩ **MCP for Blender**, or inject them through `BLENDERMCP_SKETCHFAB_API_KEY`, `BLENDERMCP_POLYPIZZA_API_KEY`, `BLENDERMCP_HYPER3D_API_KEY`, `BLENDERMCP_HUNYUAN3D_SECRET_ID`, `BLENDERMCP_HUNYUAN3D_SECRET_KEY`, `BLENDERMCP_HUNYUAN3D_API_URL` and `BLENDERMCP_MESHY_API_KEY`. Never commit keys to `.omp/mcp.json`.

## Options

| Variable | Default | Effect |
| --- | --- | --- |
| `BLENDER_HOST` | `localhost` | Host of the addon's socket server |
| `BLENDER_PORT` | `9876` | Port of the addon's socket server |
| `BLENDER_MCP_SAFE_MODE` | off | `1` validates scripts before they run and blocks risky code (direct file access, spawning programs, network access, persistence). Normal modeling, materials, rendering, saving and import/export still work |
| `DISABLE_TELEMETRY` | unset | `true` disables all telemetry |

Set them in the `env` block of the `blender` entry. To turn on safe mode:

```json
"env": {
  "DISABLE_TELEMETRY": "true",
  "BLENDER_MCP_SAFE_MODE": "1"
}
```

Safe mode is off in the committed config.

### Multiple Blender instances

Add a second entry that differs only in `--port`, and set the same port in that Blender's addon panel:

```json
"blender-b": {
  "type": "stdio",
  "command": "uvx",
  "args": ["mcp-for-blender", "--port", "9877"],
  "env": { "DISABLE_TELEMETRY": "true" }
}
```

## Telemetry

Per the upstream README:

- Without opt-in, the server sends a minimal anonymous usage record: a random install ID, a session ID, the tool name, success or failure, duration, MCP for Blender and Blender versions, OS, and a timestamp.
- Prompts, generated code, viewport screenshots, scene data and trajectory steps are collected only if you opt in under **Edit** ⟩ **Preferences** ⟩ **Add-ons** ⟩ **MCP for Blender**, or accept a one-time prompt some clients show. This is off by default.
- Collected data may be used for research and to train AI models.

This repo sets `DISABLE_TELEMETRY=true`, which turns off even the minimal record. Server startup logs `Telemetry disabled via environment variable` when it takes effect. Remove the `env` entry to restore the default. The addon preference for content collection is separate. Leave it unchecked.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `spawn uvx ENOENT` | omp can't see `uvx` on `PATH`, usually because it was launched from a GUI. Replace `command` with the full path from `where uvx` (Windows) or `which uvx`, or on Windows use `"command": "cmd", "args": ["/c", "uvx", "mcp-for-blender"]`. Fully restart omp afterwards |
| `Could not find a Blender user addons directory` from `install-addon` | Blender has never been launched, so its user folders don't exist yet. Launch Blender once, or pass `--addons-dir` as in [Setup steps](#setup-steps) |
| `/mcp list` shows `blender` connected, but tools fail with `Could not connect to Blender` | The addon isn't running. Open Blender (the version you installed the addon for), enable the addon, and click **Connect to MCP server** in the **MCP for Blender** tab. Check that its port matches `BLENDER_PORT` |
| Server install fails or picks the wrong Python (conda, pyenv, newest CPython without wheels) | Pin Python and prefer uv-managed interpreters: `"args": ["--python", "3.11", "mcp-for-blender"]` with `"env": { "UV_PYTHON_PREFERENCE": "only-managed" }` |
| A failed install keeps replaying after a fix | `uv cache clean mcp-for-blender blender-mcp && uvx --refresh mcp-for-blender` |
| Server not listed in omp | Run omp from the repo root, validate the JSON, then `/mcp reload` |
| Timeouts on large requests | Break the request into smaller steps. Raise the entry's `timeout` (milliseconds) if needed |
| Blender freezes during a Poly Haven download | Downloads run on Blender's main thread. Ask for 1k or 2k resolution unless the asset is close to camera |
| Poly Pizza download fails with a Cloudflare challenge | The CDN blocks datacenter, VPN and cloud IPs. Retry from a normal connection, or download the `.glb` and use **File** ⟩ **Import** ⟩ **glTF 2.0** |

Only run one MCP client against the addon at a time. Upstream warns against running the server from two clients (for example Cursor and Claude Desktop) simultaneously.

### Updating

```bash
uvx mcp-for-blender@latest update
```

Updates the server and every installed copy of the addon, keeping `.bak` files. Then restart omp and either restart Blender or disable and re-enable the addon, and click **Connect to MCP server** again if it isn't connected. Add `--dry-run` to preview.

## Security

- `execute_blender_code` runs arbitrary Python inside Blender with full `bpy` access, and Blender Python can touch files and the network. **Save your work before letting the agent drive Blender.** Consider `BLENDER_MCP_SAFE_MODE=1`.
- The addon's socket has no authentication or encryption. Anyone who can reach the port can run Python in Blender. Keep it on `localhost`, and tunnel over SSH instead of pointing `BLENDER_HOST` at a remote machine.
- `uvx` downloads and runs `mcp-for-blender` from PyPI at launch. omp treats committed MCP definitions as trusted input and `stdio` entries run arbitrary commands, so review `.omp/mcp.json` before opening an unfamiliar checkout.
- Asset sources (Poly Haven, Sketchfab, Poly Pizza) and AI generators make outbound network requests. Untick the ones you don't want in the addon panel.
- Poly Pizza models are mostly CC-BY and require attribution. The addon writes the credit line to the imported object's `polypizza_attribution` custom property. Poly Haven assets are CC0.

## Official Blender Lab server

The Blender Foundation publishes its own MCP server at [blender.org/lab/mcp-server](https://www.blender.org/lab/mcp-server/). It requires Blender 5.1 or newer, a Blender Lab add-on, and a separately installed MCP server, and its own page warns that it executes LLM-generated code with no guards. It is not configured in this repo. Its setup wiki (`projects.blender.org/lab/blender_mcp/wiki/Setup`) returned HTTP 403 when fetched, so no verified omp configuration exists for it here.
