# Asset manifest

One row per asset. Credit lines here are the ones approved under AGENTS.md rule 6 and needed for the game's credits.

| Asset | Source file | Export file(s) | Roblox asset ID | Licence | Attribution |
| --- | --- | --- | --- | --- | --- |
| ScrapSedan: rusted four-door wreck on bare rims, left doors missing, roof caved in | `assets/models/scrapyard_cars.blend` (built by `assets/models/scripts/build_scrapyard_cars.py`) | `assets/models/export/ScrapSedan.fbx` (albedo embedded), `assets/models/export/ScrapSedan_albedo.png` | Pending: not yet imported into Studio | Original work, made for this project | None needed |
| ScrapPickup: burnt-out pickup on cinder blocks, no wheels, bonnet open, glass smashed | `assets/models/scrapyard_cars.blend` (built by `assets/models/scripts/build_scrapyard_cars.py`) | `assets/models/export/ScrapPickup.fbx` (albedo embedded), `assets/models/export/ScrapPickup_albedo.png` | Pending: not yet imported into Studio | Original work, made for this project | None needed |

## Notes

- **Scrapyard cars.** Modelled by hand with bpy (lofted body sections, exact booleans, dents from displacement). No library assets, textures or generators were used. Rust, soot and paint chips come from a procedural Cycles shader baked to a 1024x1024 albedo (`bake_export_scrapyard_cars.py`). 1 Blender unit = 1 stud, front faces +X in Blender, origin at the base centre.
