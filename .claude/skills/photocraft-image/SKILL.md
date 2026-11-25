---
name: photocraft-image
description: Use when a texture, PBR map, decal, UI image, icon or thumbnail for the Roblox game needs to be made or edited in PhotoCraft and exported as PNG.
---

# 2D image: PhotoCraft to Roblox Studio

The 2D pipeline from AGENTS.md ("Pipelines" and "PhotoCraft"), as a checklist. In Claude Code, prefer delegating steps 2 to 4 to the `photocraft-artist` subagent so that `render_preview` images stay out of the main conversation. If the subagent returns source images that need attribution, put them to the user before re-dispatching.

## Checklist

1. **Agree on the spec:** use and size (power of two, PBR maps ≤ 1024x1024, about one 256x256 map per 2x2x2 studs), colour mode, and transparency. For game icons and thumbnails, check the current sizes with the Studio `http_get` tool.
2. **Build it.** Start with `session_list`, then `doc_new` (`width`, `height`, `mode`, `depth: 8`, `background`) or `doc_open`. Find command ids with `command_list` and its `filter`. Never guess ids or parameters. Duplicate the document (`image.duplicate`) before experimenting. After each meaningful step, run `doc_inspect` and `render_preview`.
   - Source images you didn't make, such as textures, photos and references: you can use CC0 images (such as Poly Haven) freely. If an image needs attribution or its licence is unknown, stop before `doc_open` or `doc_place`. Report its name, source, licence and the exact credit line, then wait for a go-ahead (AGENTS.md rule 6).
   - Roughness, metalness and emissive-mask maps: `mode: gray`, `depth: 8`.
   - Normal maps: bake them in Blender (OpenGL tangent-space), not in PhotoCraft.
   - Tiling textures: offset or tile the image and check the seams in `render_preview`.
   - UI panels and buttons: transparent background, consistent padding, designed for 9-slice (`ScaleType = Slice`).
   - `command_batch` is not atomic. After a failure, inspect and then undo with `{"id":"edit.undo","params":{}}`.
3. **Save the source** as `.pcraft` or `.psd` under `assets/art/`.
4. **Export the PNG** to `assets/art/export/<name>.png` with a new filename. Never overwrite an existing or tracked file without telling the user. Reopen gray maps to confirm their mode.
5. **HANDOFF.** Stop and ask the user to upload the PNG through Studio's Asset Manager and send back the asset ID. If the image is reachable at an HTTP URL, `upload_image` can do this instead.
6. **Apply it** with `execute_luau` (`SurfaceAppearance`, `Decal` or `ImageLabel`). Verify with `screen_capture` in play mode, and check UI on phone, tablet and desktop.
7. **Manifest.** Add or update the row in `assets/MANIFEST.md`: source, export, Roblox asset ID, licence, and the approved credit line for any credited source image.

## Report

Give the size and mode as confirmed by reopening the file, the source and export paths, and which steps are still waiting on the user.
