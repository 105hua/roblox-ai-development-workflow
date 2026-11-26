# Roblox AI Development Workflow

Tooling and configuration for developing Roblox experiences with an AI coding agent ([omp](https://github.com/can1357/oh-my-pi) or [Claude Code](https://code.claude.com/docs)) connected to Roblox Studio, Blender and PhotoCraft.

## Contents

| Path | Purpose |
| --- | --- |
| [`.omp/mcp.json`](.omp/mcp.json) | omp project config that registers the `Roblox_Studio`, `blender` and `photocraft` MCP servers |
| [`docs/roblox-studio-mcp.md`](docs/roblox-studio-mcp.md) | Setup, tool reference, verification, and troubleshooting for the Roblox Studio connection |
| [`docs/blender-mcp.md`](docs/blender-mcp.md) | Setup, tool reference, verification, and troubleshooting for the Blender connection |
| [`docs/photocraft-mcp.md`](docs/photocraft-mcp.md) | Setup, tool reference, safety notes, and troubleshooting for the PhotoCraft image editor connection |
| [`AGENTS.md`](AGENTS.md) | Instructions for AI agents: how to use all three servers together, Roblox asset budgets, cross-tool pipelines, and repo conventions |
| [`CLAUDE.md`](CLAUDE.md) | Claude Code entry point. Imports `AGENTS.md` and adds Claude Code specifics |
| [`.mcp.json`](.mcp.json) | Claude Code project config for the same three MCP servers. Keep it in sync with `.omp/mcp.json` |
| [`.claude/settings.json`](.claude/settings.json) | Shared Claude Code permissions: read-only MCP tools allowed, Studio generation and config edits ask, trajectory feedback and the paid Blender generators denied |
| [`.omp/config.yml`](.omp/config.yml) | omp project settings that deny the paid Blender generators |
| [`.claude/skills/`](.claude/skills/) | Step-by-step procedures (also loaded by omp): `mcp-status`, `studio-script-edit`, `studio-playtest`, `studio-insert-asset`, `blender-prop`, `photocraft-image` |
| [`.claude/agents/`](.claude/agents/) | Claude Code subagents: `blender-artist`, `photocraft-artist`, `luau-reviewer` |

## Quick start

Run omp from this directory after setting up each server, then run `/mcp list` to confirm the connections.

### Roblox Studio

1. Install the latest Roblox Studio.
2. In Studio: **Assistant** ⟩ **…** ⟩ **Manage MCP Servers** ⟩ turn on **Enable Studio as MCP server**.
3. Confirm `Roblox_Studio` is connected. Studio also shows a green indicator.

The committed `Roblox_Studio` entry is Windows-specific. macOS setup and troubleshooting are in [`docs/roblox-studio-mcp.md`](docs/roblox-studio-mcp.md).

### Blender

1. Install [uv](https://docs.astral.sh/uv/) (official installer, not `pip install uv`) and Blender 3.0 or newer.
2. Install the addon. A freshly installed Blender has no user folders until it has been launched once, so launch and close it first, or pass the folder explicitly: `uvx mcp-for-blender install-addon --addons-dir "$env:APPDATA\Blender Foundation\Blender\<major.minor>\scripts\addons"`.
3. In Blender: **Edit** ⟩ **Preferences** ⟩ **Add-ons** ⟩ enable **Interface: MCP for Blender**. The server starts automatically. If not, click **Connect to MCP server** in the **MCP for Blender** tab of the 3D viewport sidebar (`N`).
4. Confirm `blender` is connected, then call `get_addon_status` to confirm the addon is reachable.

The `blender` entry works on any OS and has telemetry disabled. Details are in [`docs/blender-mcp.md`](docs/blender-mcp.md).

### PhotoCraft

1. Install [PhotoCraft](https://github.com/storytold/photocraft/releases). The installer includes `photocraft-cli`.
2. Confirm it exists at `C:\Program Files\ArtCraft\PhotoCraft\photocraft-cli.exe`, or point `command` at your install path (see [`docs/photocraft-mcp.md`](docs/photocraft-mcp.md) for per-machine overrides).
3. Confirm `photocraft` is connected. `photocraft-cli mcp` runs its own headless engine by default, so the desktop app doesn't need to be open.

The committed `photocraft` entry is Windows-specific and grants the server read and write access to the repo root, so start omp from the repo root. Other platforms, narrower roots and the optional live-app bridge are in [`docs/photocraft-mcp.md`](docs/photocraft-mcp.md).

## Using with Claude Code

1. Set up each application as in [Quick start](#quick-start). The Studio, Blender and PhotoCraft steps are the same for every agent.
2. Run `claude` from the repo root. Claude Code loads `CLAUDE.md` (which imports `AGENTS.md`), the skills and the subagents automatically.
3. Approve `Roblox_Studio`, `blender` and `photocraft` when Claude Code asks about the project MCP servers in `.mcp.json`. Run `/mcp` to confirm they're connected, then ask Claude to run the `mcp-status` skill to check that each application is actually reachable.
4. On macOS, or with PhotoCraft installed elsewhere, override an entry for your checkout only with `claude mcp add --scope local <name> -- <command>`. The docs in `docs/` have the exact commands.
5. Put personal permissions in `.claude/settings.local.json`, which is gitignored. The shared settings only pre-allow read-only tools, so Blender and PhotoCraft write tools still prompt. That matters when the artist subagents run in the background. If you want them to work unattended, allow the write tools yourself, for example:

   ```json
   { "permissions": { "allow": ["mcp__blender__execute_blender_code", "mcp__photocraft__command_run", "mcp__photocraft__doc_save"] } }
   ```

The skills hold the AGENTS.md procedures, and Claude picks them up when a task matches. You can also call one directly, for example `/studio-playtest`. Delegate Blender and PhotoCraft work to the `blender-artist` and `photocraft-artist` subagents so their preview images don't fill the main context. Use `luau-reviewer` for a read-only review before calling a feature done.

## Security

All three MCP servers give the connected agent control of a local application. The Studio server can read and modify your open places. The Blender server can run arbitrary Python in Blender, so save your work first. The PhotoCraft server can read and overwrite files under its configured roots. Review `.omp/mcp.json` and `.mcp.json` before running omp or Claude Code in any checkout, since `stdio` entries execute commands. Claude Code asks you to approve project MCP servers before it starts them. This repo deliberately does not pre-approve them in `.claude/settings.json`.
