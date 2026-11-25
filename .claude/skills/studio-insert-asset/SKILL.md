---
name: studio-insert-asset
description: Use when adding a model, mesh, material or image to the Roblox place from the Creator Store, the user's Creator Inventory or Studio generation tools (search_asset, insert_asset, generate_procedural_model, generate_mesh, generate_material, upload_image).
---

# Inserting or generating assets in Roblox Studio

Creator Store models can carry scripts and may require credit, and generation can cost money or credits. Handle all three before the asset ends up in the game.

## Steps

1. **Prefer the user's own assets.** `search_asset` covers the Creator Inventory as well as the Creator Store.
2. **Attribution.** For a Creator Store asset, read its description and creator notes for a credit requirement before inserting it. If it requires credit, **stop and don't insert it**. Tell the user the asset's name, asset ID, creator, licence or terms, and the exact credit line, then wait for a go-ahead (AGENTS.md rule 6). The user's own assets need no approval.
3. **Generation costs.** Before calling `generate_mesh`, `generate_material` or `generate_procedural_model`, tell the user that it may cost money or credits and get a yes. Wait on jobs with `wait_job_finished`.
4. **Insert** with `insert_asset`.
5. **Audit scripts.** Search the inserted tree with `search_game_tree` for the classes `Script`, `LocalScript` and `ModuleScript`. Read each one with `script_read`. Report what each script does and ask before removing anything. Never `require` or `loadstring` code you haven't read.
6. **Configure** with `execute_luau` (`datamodel_type: Edit`): anchor static parts, and turn off `CanCollide`, `CanQuery` and `CanTouch` on decorative parts. Use tags and attributes rather than hard-coded paths.
7. **Look** at it with `screen_capture`.
8. **Record** the asset in `assets/MANIFEST.md` (create it if missing): source, Roblox asset ID, licence, and the approved credit line if there is one.

## Report

Give the asset ID and source, its licence and credit line (or that it's waiting on attribution approval), the scripts found and what was done with each, the cost incurred (if any), and the screen-capture result.
