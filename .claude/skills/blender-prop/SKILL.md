---
name: blender-prop
description: Use when a 3D prop, model, rig or animation for the Roblox game needs to be made, imported from Poly Haven, Sketchfab or Poly Pizza, cleaned up or exported as FBX from Blender.
---

# 3D prop: Blender to Roblox Studio

The prop pipeline from AGENTS.md ("Pipelines" and "Blender"), as a checklist. In Claude Code, prefer delegating steps 2 to 4 to the `blender-artist` subagent so that `look` images stay out of the main conversation. If the subagent returns candidate assets that need attribution, put them to the user. Once they approve, re-dispatch with the approved asset and its credit line.

## Checklist

1. **Agree on the spec** with the user: size in studs and metres, style, triangle budget (at most 20,000 per mesh) and texture size. Grey-box it in Studio first if the gameplay isn't proven yet.
2. **Build in Blender.** Start with `get_addon_status` and `get_scene_info`, then make small `execute_blender_code` steps, each followed by `look`.
   - Library import: run `search_assets` with `previews` first, and read each candidate's licence before importing. Then act on the licence:

     | Licence | Action |
     | --- | --- |
     | CC0 (all of Poly Haven, CC0 Poly Pizza) | Import with `import_asset`, passing `target_size` in metres |
     | Requires credit (CC-BY Poly Pizza, a Sketchfab model that requires credit), or unknown | **Stop. Don't import.** Report the asset's name, its source link or ID, its licence and the exact credit line, then wait for a go-ahead (AGENTS.md rule 6) |
     | Doesn't allow use in a published game | Skip it |

   - After an approved import, copy the approved credit line (for Poly Pizza, `polypizza_attribution`) for the manifest.
   - Source models from the libraries (Poly Haven, Poly Pizza, Sketchfab) or model them with `execute_blender_code`. The Blender generators `generate_3d` and `generate_gaussian_world` are blocked in this repo.
   - Experiment on a duplicate object or collection. Ask the user to save the `.blend` before destructive steps.
3. **Check the budgets** with `get_scene_info` (fields `topology`, `details`, `materials`, `ground`) and `look` (`angles`, then `wireframe`):
   - tris ≤ 20,000, no n-gons, no non-manifold edges
   - one material per mesh, one UV set inside 0 to 1
   - deliberate object names and a bottom-center pivot, sitting on the ground
   - rigs: frozen bones and the root at the origin
4. **Export the FBX** to `assets/models/export/<name>.fbx` (use a new filename, don't overwrite). Read the exporter's enum identifiers from the live API first. Settings: path mode Copy with Embed Textures, Apply Scalings = FBX Unit Scale, Add Leaf Bones off, Bake Animation off unless the export is an animation. Save the `.blend` source under `assets/models/`.
5. **HANDOFF.** Stop and ask the user to import the FBX in Studio (3D Importer or Asset Manager) and send back the instance path or asset ID.
6. **Place it** with `execute_luau`: anchoring, collision, tags and attributes. Compare the size with `inspect_instance` and fix the scale if needed (see AGENTS.md "FBX export"). Verify with `screen_capture`, then playtest.
7. **Manifest.** Add or update the row in `assets/MANIFEST.md`: `.blend` source, FBX export, Roblox asset ID, licence and attribution.

## Report

Give the triangle count, material count, the export path, the licence and credit line, any assets waiting on attribution approval, and which steps are still waiting on the user.
