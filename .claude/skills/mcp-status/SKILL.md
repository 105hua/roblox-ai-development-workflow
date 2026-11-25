---
name: mcp-status
description: Use when starting a Roblox, Blender or PhotoCraft session in this repo, before planning work that depends on Roblox Studio, Blender or PhotoCraft, or when an MCP tool fails with errors like "MCP subprocess closed stdout", "Could not connect to Blender", "spawn uvx ENOENT" or "cannot open automation read root".
---

# MCP status check

Confirm which of the three servers actually work before you plan around them. A server that is listed as connected can still be unusable. For example, the Blender server connects even when Blender is closed.

## Checks

Run each check and record the result. Don't guess.

| Server | Call | Healthy result |
| --- | --- | --- |
| `Roblox_Studio` | `list_roblox_studios`, then `get_studio_state` with the chosen `studio_id` | At least one Studio listed. State returns edit or play mode |
| `blender` | `get_addon_status` | Blender and addon versions, plus the enabled libraries and generators |
| `photocraft` | `session_list` | A session list. It may be empty |

If several Studios are listed, ask which place to edit before you change anything.

## Report

Give one line per server: **up**, **down** (with the exact error), or **not checked** (with the reason). Then:

- For a down server, point to the matching Troubleshooting section and stop planning work that needs it: `docs/roblox-studio-mcp.md`, `docs/blender-mcp.md` or `docs/photocraft-mcp.md`.
- If a server is missing from the tool list entirely, it was probably never approved. Tell the user to run `/mcp` in Claude Code (or `/mcp list` in omp) and approve or reconnect it.
- Don't edit `.mcp.json` or `.omp/mcp.json` to work around a failure without telling the user.
