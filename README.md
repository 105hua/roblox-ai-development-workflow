# Roblox AI Development Workflow

Tooling and configuration for developing Roblox experiences with an AI coding agent ([omp](https://github.com/can1357/oh-my-pi)) connected to Roblox Studio, Blender and PhotoCraft.

## Contents

| Path | Purpose |
| --- | --- |
| [`.omp/mcp.json`](.omp/mcp.json) | omp project config that registers the `Roblox_Studio`, `blender` and `photocraft` MCP servers |
| [`docs/roblox-studio-mcp.md`](docs/roblox-studio-mcp.md) | Setup, tool reference, verification, and troubleshooting for the Roblox Studio connection |
| [`docs/blender-mcp.md`](docs/blender-mcp.md) | Setup, tool reference, verification, and troubleshooting for the Blender connection |
| [`docs/photocraft-mcp.md`](docs/photocraft-mcp.md) | Setup, tool reference, safety notes, and troubleshooting for the PhotoCraft image editor connection |
| [`AGENTS.md`](AGENTS.md) | Instructions for AI agents: how to use all three servers together, Roblox asset budgets, cross-tool pipelines, and repo conventions |

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
2. Confirm it exists at `C:\Program Files\PhotoCraft\photocraft-cli.exe`, or edit `command` in `.omp/mcp.json` to your install path.
3. Confirm `photocraft` is connected. It runs headlessly, so the desktop app doesn't need to be open.

The committed `photocraft` entry is Windows-specific and grants the server read and write access to the repo root, so start omp from the repo root. Other platforms, narrower roots and the optional live-app bridge are in [`docs/photocraft-mcp.md`](docs/photocraft-mcp.md).

## Security

All three MCP servers give the connected agent control of a local application. The Studio server can read and modify your open places. The Blender server can run arbitrary Python in Blender, so save your work first. The PhotoCraft server can read and overwrite files under its configured roots. Review `.omp/mcp.json` before running omp in any checkout, since `stdio` entries execute commands.
