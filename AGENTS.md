# AGENTS.md

Instructions for AI agents working in this repo. Goal: ship a high-quality Roblox game by using three MCP servers well and verifying everything they do.

The repo currently holds tooling config and docs only (see [README.md](README.md) and [docs/](docs/)). The game itself lives in a **Roblox Studio place** and is edited live through MCP. Source art and models are saved here as they are created (see [Repo conventions](#repo-conventions)).

Order of authority: the user's instructions, then conventions already present in the place or repo, then the defaults in this file.

## Tools at a glance

| Server | Use it for | Needs running | Status check |
| --- | --- | --- | --- |
| `Roblox_Studio` | The game: data model, scripts, Luau, playtesting, in-Studio asset generation and insertion | Roblox Studio open, **Enable Studio as MCP server** on | `list_roblox_studios`, then `get_studio_state` |
| `blender` | 3D models, rigs, animation, materials, FBX export, asset-library imports | Blender open with the MCP for Blender addon connected | `get_addon_status` |
| `photocraft` | 2D art: textures, UI art, icons, thumbnails | Nothing (headless) | `session_list` |

- In omp, MCP tools are mounted as `xd://mcp__<server>_<tool>`. Read the device for the exact schema before first use.
- Check availability before planning around a server. If one is down, say so, point to its troubleshooting section in `docs/`, and do not substitute guesses. Never report a visual or runtime check as passed unless you ran it.
- Other MCP servers in the user's global config (UI-component catalogs, reverse-engineering tools) are not part of this workflow. Don't use them for the game unless asked.
- Setup, tool lists and troubleshooting: [Roblox Studio](docs/roblox-studio-mcp.md), [Blender](docs/blender-mcp.md), [PhotoCraft](docs/photocraft-mcp.md).

## Rules for every tool

1. **Look, change, look again.** Evidence beats assumption: `get_console_output`, `screen_capture`, `inspect_instance`, `look`, `get_scene_info`, `render_preview`, `doc_inspect`. A task is done when you observed the result, not when the call returned.
2. **Small steps.** One focused change per call, print or return what you need to check it, then verify. Batch only when the steps are independent and cheap to redo.
3. **Protect the user's work.** Ask before deleting instances or objects, overwriting scripts or files, mass renames or reparenting, or anything that costs money or credits. Experiment on copies: duplicate instances, Blender objects or collections, PhotoCraft documents.
4. **Be explicit about gaps.** Say what you did not verify and why. Mark inferences as inferences.
5. **Check costs and licences before using an asset.** Generation tools may cost money or credits. Library assets carry licences (see [Blender](#blender)). Record sources in the asset manifest.
6. **Keep secrets and telemetry out of the repo.** Never put API keys in `.omp/mcp.json` or committed files. Blender MCP telemetry is disabled by config. Do not re-enable it, do not call `record_trajectory_feedback`, and omit the optional `user_prompt` parameter on Blender tools.
7. **Don't commit or push unless asked.**

## Roblox Studio

### Session
- Every tool takes `studio_id`. Run `list_roblox_studios` first and use the ID of the right instance. If several Studios are open, confirm with the user which place to edit.
- `execute_luau` requires `datamodel_type`: **Edit** to change the place, **Client** or **Server** to inspect a running playtest. `multi_edit` requires **Edit**.
- No documented tool saves or publishes the place. Tell the user to save, and never claim it was saved.

### Explore before editing
- Map the place with `search_game_tree` (filter by path, class, keyword; limit depth) and `inspect_instance`. Use `subagent` with type `explore` for broad questions about the game state.
- Find code with `script_search` (fuzzy name, max 10 results) and `script_grep` (max 50 matches). Hitting a cap means the query is too broad, so narrow it.
- Read the script with `script_read` (line ranges supported) immediately before editing it. The user may have changed it.

### Editing scripts
- `multi_edit` applies several edits in one call and **creates a new script when the target path does not exist**. A typo therefore creates a stray script. Confirm the path with `script_read` or `script_search` first, and re-read after editing.
- After every script change, run the affected code and check `get_console_output` for errors and warnings.

### Running Luau
- Use `execute_luau` for bulk instance creation, property changes, measurements and assertions. Return a value from the code so you can check the outcome.
- Keep calls small. No unbounded loops. Don't depend on state surviving between calls.

### Playtesting loop
1. `get_studio_state`, then `start_stop_play`.
2. Drive the game with `character_navigation`, `user_keyboard_input` and `user_mouse_input`. Test UI through real input targeting UI instances, not by calling handlers directly.
3. Verify with `get_console_output`, `screen_capture` (optionally with a custom camera position and look-at target) and `execute_luau` on **Server** and **Client**.
4. Stop play with `start_stop_play` before editing.

Use `subagent` with type `playtest` for scripted gameplay scenarios. Check networked features on both the Client and Server data models. Multi-client testing is not covered by a documented tool, so ask the user to run it.

### Docs over memory
Roblox's API changes. Use `http_get` (Engine API, Creator docs, Cloud API, performance guides; supports keyword search) and `skill` (debugging, device simulation, documentation search) instead of recalling API details.

### Generating and inserting assets
- `generate_procedural_model` (primitive-part models, with `wait_job_finished`), `generate_mesh`, `generate_material`, `search_asset`, `insert_asset`, `upload_image`, `store_image`. Check each result with `screen_capture`.
- Grey-box first: block out levels with parts or procedural models, prove the gameplay, and swap in final art afterwards.
- `search_asset` covers the Creator Store and the user's Creator Inventory. Prefer the user's own assets. Creator Store models can contain scripts, so after `insert_asset` search the inserted tree for `Script`, `LocalScript` and `ModuleScript` and review or remove them. Never run `require` or `loadstring` on code you haven't read.
- `upload_image` takes HTTP URLs only. `store_image` turns a local file into an image URI for use as a reference input to other tools. No documented tool imports a local mesh or image file into Roblox. The user does that in Studio (Asset Manager or the 3D Importer) and gives you the asset ID. See [Pipelines](#pipelines).

## Luau and game engineering

Follow the place's existing conventions first. Otherwise default to the following.

**Code**
- New scripts start with `--!strict`. Annotate function signatures. Put logic in ModuleScripts and keep Script and LocalScript entry points thin.
- Use `game:GetService("...")` at the top of the file. Use `task.wait`, `task.spawn`, `task.delay` and `task.defer`, never `wait`, `spawn` or `delay`.
- Prefer events to polling. Per-frame work goes on `RunService` signals and stays cheap. Set properties before setting `Parent`.
- Disconnect connections and `Destroy` instances you create. Use `WaitForChild` (with a timeout) for anything that replicates.
- Drive designer-tunable behavior with CollectionService tags and attributes instead of hard-coded instance paths.

**Networking and security**
- The server is authoritative for currency, inventory, damage, cooldowns, spawning and progression. The client sends input and renders.
- Every `RemoteEvent` and `RemoteFunction` handler validates the sender, argument types, ranges and call rate on the server. Never trust client-supplied positions, prices, damage or IDs. Never call `InvokeClient` from the server.
- DataStore calls go in `pcall` with retry and backoff, within request budgets, with saves on player leave and in `BindToClose`. Only the server writes player data.

**Performance**
- Meshes must stay within Roblox's 20,000-triangle limit. Reuse meshes and textures. Anchor static parts, and turn off `CanCollide`, `CanQuery` and `CanTouch` on purely decorative ones.
- For large worlds, write code that tolerates instances not being streamed in yet.
- Check Roblox's current performance guides through `http_get` before optimizing, and measure rather than guess.

**UI**
- Size with scale plus constraints (`UIAspectRatioConstraint`, `UISizeConstraint`, layout objects). Respect safe areas (`ScreenGui.ScreenInsets`). Make touch targets large. Support keyboard, gamepad and touch.
- Verify on phone, tablet and desktop form factors using the device-simulation skill.

**Definition of done for a feature**
- Works in a playtest on the Client and Server data models with no new console errors or warnings.
- Gives clear feedback to the player (animation, sound, VFX, UI) and handles edge cases such as respawn, leaving mid-action and rejoining.
- UI holds up on small screens. Server-side validation exists for every remote it adds.
- Art is consistent with the rest of the game and within the budgets below.

## Blender

**Workflow.** `get_addon_status` once, then `get_scene_info`, then work in small `execute_blender_code` steps, then `look`. Use `look` generously: modes `viewport`, `camera`, `angles` (auto-framed multi-view) and `frames`, with shading `solid`, `material`, `rendered`, `wireframe` or `xray`. Images stay in the conversation, so use a small `max_size` for quick checks.

**Scripting rules (from the server's own instructions)**
- Find shader nodes by type, never by name: `next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")`.
- Never hard-code enum identifiers. Read them from the live API, for example `[i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["file_format"].enum_items]`. This applies to the FBX exporter's options as well.
- Set material colors on shader node inputs. `material.diffuse_color` only affects the viewport.
- `execute_blender_code` runs arbitrary Python. Stay within the task: no deleting files, no network access, no installing packages. Ask the user to save the `.blend` before destructive operations.

**Roblox asset budgets** (from Roblox's [specifications](https://create.roblox.com/docs/art/modeling/specifications), [texture specifications](https://create.roblox.com/docs/art/modeling/texture-specifications) and [export settings](https://create.roblox.com/docs/art/modeling/export-requirements); re-check them through `http_get` because they change):

| Area | Requirement |
| --- | --- |
| Geometry | At most 20,000 triangles per mesh. Watertight, with no exposed holes or backfaces. Quads where possible, no n-gons. Non-zero thickness |
| Materials | One material per mesh object. Split multi-material models into separate meshes or bake to one texture |
| UVs | One UV set, all coordinates inside 0 to 1. Overlaps allowed |
| PBR maps | Albedo RGB 24-bit. Normal map in OpenGL tangent-space format. Roughness, metalness and emissive mask are single-channel 8-bit grayscale |
| Texture size | One 256x256 map per roughly 2x2x2 studs of asset, stepping up for larger assets. Keep PBR maps at 1024x1024 or below |
| Rigs | Freeze all bones (scale 1,1,1; rotation 0,0,0). Root bone at 0,0,0 with no vertex influence. At most 4 bone influences per vertex |
| Animation | One animation track per FBX export |
| Cages | Named `<Mesh>_InnerCage` and `<Mesh>_OuterCage`. Don't delete vertices or edit UVs on them |
| Avatar items | Characters, rigid accessories and layered accessories have their own specifications. Read them before starting |

Check budgets with `get_scene_info` using the `topology` (quads, tris, n-gons, non-manifold edges), `details` and `materials` fields before exporting. Name objects deliberately, because Roblox instance names come from them. Put pivots where placement is easy (bottom-center for props). Use the `ground` field to confirm objects sit on the ground.

**FBX export.** Use `bpy.ops.export_scene.fbx` (look up its enum identifiers first) with these settings: path mode **Copy** with **Embed Textures** on, **Apply Scalings** set to **FBX Unit Scale**, **Add Leaf Bones** off, and **Bake Animation** off unless exporting keyframed animation. After the user imports the model, compare its size in Studio using `inspect_instance`. If it is off, follow Roblox's [Blender FBX scaling guidance](https://create.roblox.com/docs/art/blender#adjust-scale-fbx).

**Library assets**
- `search_assets` (use `previews` before importing), then `import_asset`. Always pass `target_size` in metres for models. Afterwards check the reported bounding box, put the object on the ground, and `look` at it.
- Poly Haven is CC0. Poly Pizza is CC0 or CC-BY, and CC-BY needs credit: the addon writes the credit line to the object's `polypizza_attribution` custom property, so copy it into the manifest. Sketchfab licences vary per model, so confirm the licence allows use in a published game before importing.
- Prefer low-poly sources for Roblox. Sketchfab face counts vary widely.
- Poly Haven textures need `apply_to` or the material is created but unused and lost on save.

**Generation.** `generate_3d` makes one textured object per call, takes 1 to 3 minutes, and can cost the user money or credits. Ask first and don't repeat a request to retry it (resuming with `job` is free). Expect to clean up topology, scale and UVs to meet the budgets.

## PhotoCraft

**Workflow.** `session_list`, then `doc_new` (`width`, `height`, `mode` rgb or gray, `depth` 8, `background` such as `transparent` or `#rrggbb`) or `doc_open`. Find engine commands with `command_list` and its `filter` parameter. Never guess command ids or parameters. Run them with `command_run`, or `command_batch` for ordered steps. Inspect with `doc_inspect` and look at `render_preview` (max side 2048) after each meaningful change.

**Safety**
- Experiment on a copy: `command_run` with `image.duplicate` or `history.newDocument`.
- `command_batch` is not atomic. After a failure, check `doc_inspect` and undo with `command_run` `{"id":"edit.undo","params":{}}`. Undo does not undo files already written.
- The read and write roots are the repo root. `doc_save` and `doc_export` can overwrite existing files. Never write over an existing source or tracked file without telling the user. Use a new filename for each export.

**Making Roblox-ready art**
- Keep layered sources as `.pcraft` (lossless) or `.psd`. Export flattened copies with `doc_save` and a `path` ending in `.png` (Roblox accepts `.png`, `.jpg`, `.tga`, `.bmp` for uploaded textures). Prefer PNG for lossless color and alpha.
- Use the Roblox size budgets above. Make roughness, metalness and emissive-mask maps `mode: gray`, `depth: 8`, then reopen the exported file to confirm its mode. PhotoCraft is not a normal-map baker, so bake normals in Blender and keep them OpenGL tangent-space.
- For tiling textures, check seams before exporting. Look in `command_list` for an offset or tile command and view the result with `render_preview`.
- UI art: use transparent backgrounds, power-of-two canvases and consistent padding. Design panels and buttons so they can use 9-slice scaling (`ImageLabel.ScaleType = Slice` with `SliceCenter`). Check current game icon and thumbnail sizes through `http_get`.

## Pipelines

These are the handoffs where an agent cannot finish alone. Stop at each **HANDOFF**, tell the user exactly what to do, and resume with the asset ID.

**3D prop**
1. Agree on size, style and polygon budget. Grey-box it in Studio first.
2. Model in Blender, then check budgets with `get_scene_info` and review with `look` (`angles`, `wireframe`).
3. Export FBX with the settings above into `assets/models/export/`.
4. **HANDOFF:** the user imports the FBX in Studio (3D Importer or Asset Manager) and reports the instance or asset ID.
5. Place and configure it with `execute_luau` (anchoring, collision, tags and attributes). Verify with `screen_capture`, then playtest.

**2D texture, decal or UI image**
1. Build it in PhotoCraft at the budgeted size. Check with `render_preview`.
2. Export a PNG to `assets/art/export/`.
3. **HANDOFF:** the user uploads it through Studio's Asset Manager and reports the asset ID. If the image is reachable at an HTTP URL, `upload_image` can do this instead.
4. Apply it with `execute_luau` (`SurfaceAppearance`, `Decal` or `ImageLabel`). Verify with `screen_capture` in play mode.

**Reference to generation.** `store_image` a local PhotoCraft export, then pass the returned URI as the reference image to `generate_procedural_model`.

## Repo conventions

Create these when first needed:

```
assets/models/          Blender sources (.blend)
assets/models/export/   FBX exports for Studio import
assets/art/             PhotoCraft sources (.pcraft, .psd)
assets/art/export/      PNG exports for upload
assets/MANIFEST.md      one row per asset: source file, export file, Roblox asset ID, licence and attribution
```

- Update `assets/MANIFEST.md` whenever you add or replace an asset. It carries the CC-BY credits you need for the game's credits.
- Ask before committing large binaries.
- `.omp/mcp.json` is Windows-specific for `Roblox_Studio` and `photocraft`. Don't commit machine-specific paths, tokens or keys. When MCP setup changes, update the matching file in `docs/` and the README.
- When a server won't connect, use the troubleshooting section of its doc in `docs/`. Don't work around a missing server by editing its config without telling the user.
