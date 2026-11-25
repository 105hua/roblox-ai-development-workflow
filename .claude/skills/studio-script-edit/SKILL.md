---
name: studio-script-edit
description: Use when creating, changing or fixing a Script, LocalScript or ModuleScript in the open Roblox Studio place through the Roblox Studio MCP server (multi_edit, script_read, script_search, script_grep).
---

# Editing scripts in Roblox Studio

`multi_edit` creates a new script when the target path doesn't exist, so a typo silently creates a stray script. The user may also have changed the script since you last read it. These steps prevent both problems.

## Steps

1. **Find it.** Use `script_search` (fuzzy name, max 10 results) or `script_grep` (max 50 matches). If you hit a cap, narrow the query.
2. **Read it now.** Run `script_read` on the exact path right before the edit, even if you read it earlier.
3. **New script?** Confirm that the parent path exists with `search_game_tree` or `inspect_instance`. Follow the code defaults in AGENTS.md under "Luau and game engineering": `--!strict`, `GetService` at the top, the `task.*` library, and thin entry points with logic in ModuleScripts.
4. **Edit** with one focused `multi_edit` call. Overwriting a script the user wrote counts as a protected change, so ask first (AGENTS.md rule 3).
5. **Re-read** the edited range with `script_read` to confirm the change landed in the right script.
6. **Run it.** Exercise the code, either with `execute_luau` (`datamodel_type: Edit` for edit-time code) or through a playtest (the `studio-playtest` skill), then check `get_console_output` for new errors and warnings.
7. **Remotes.** If you added or changed a `RemoteEvent` or `RemoteFunction` handler, confirm that the server validates the sender, argument types, ranges and call rate.

## Report

Give the script path, what changed, and the console output you observed. Name anything you didn't run.
