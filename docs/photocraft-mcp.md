# PhotoCraft MCP setup for omp

Connects [omp](https://github.com/can1357/oh-my-pi) to **PhotoCraft**, ArtCraft's open-source, Photoshop-style image editor written in Rust (layers, masks, adjustment layers, layer styles, type, vectors, real PSD files). The agent can create and edit documents, run any engine command, and render previews, either headlessly or against a running desktop app.

Sources: [storytold/photocraft](https://github.com/storytold/photocraft) (`book/src/automation/mcp.md`, `docs/mcp.md`, `docs/development.md`). PhotoCraft's README labels the project early alpha, so expect behavior to change between releases.

## How it works

The MCP server is a mode of the PhotoCraft CLI, `photocraft-cli mcp`, which ships with the desktop app. It talks to omp over `stdio` and has two backends:

| Backend | Started with | What it drives |
| --- | --- | --- |
| Headless (configured here) | `photocraft-cli mcp --automation-read-root <dir> --automation-write-root <dir>` | An in-process engine session. No desktop app needed |
| Bridge (optional) | `photocraft-cli mcp --bridge 127.0.0.1:<port> --control-token-file <file>` | A running desktop app started with `photocraft --control <port>`. Adds UI tools |

## Configuration

`.omp/mcp.json` (project scope, committed to this repo) contains:

```json
"photocraft": {
  "type": "stdio",
  "command": "C:\\Program Files\\PhotoCraft\\photocraft-cli.exe",
  "args": [
    "mcp",
    "--automation-read-root",
    ".",
    "--automation-write-root",
    "."
  ]
}
```

Notes:

- **Windows-specific path.** `C:\Program Files\PhotoCraft\photocraft-cli.exe` is the MSI's default install location. The CLI is not put on `PATH`, so the entry uses the absolute path. If you installed elsewhere, edit `command`. Linux `.deb`/`.rpm` packages install `/usr/bin/photocraft-cli`. On macOS the CLI is a separate release asset (`photocraft-cli-<version>-macos-<arch>.zip`), because the `.app` holds only the desktop app.
- **Roots are the filesystem permission.** The server can read only under `--automation-read-root` and write only under `--automation-write-root`. A root that is omitted means no access in that direction. Paths in tool calls are relative to the root, or absolute paths beneath it.
- **`.` means the repo root.** Relative roots resolve against omp's working directory, which for a project-scoped server is the directory omp was started in. Start omp from the repo root. The root directory must exist or the server exits with `cannot open automation read root`.
- **Narrowing the roots.** To limit the agent to one folder, create it and point both roots there, for example `assets/photocraft`. Upstream recommends "deliberately chosen trusted workspace directories".

### Other platforms

Put the entry in your user-level `~/.omp/agent/mcp.json` instead, with the platform's CLI path and absolute roots. Upstream's bare-name form works once `photocraft-cli` is on the `PATH` that omp inherits:

```json
"photocraft": {
  "type": "stdio",
  "command": "photocraft-cli",
  "args": ["mcp", "--automation-read-root", "/abs/path/to/repo", "--automation-write-root", "/abs/path/to/repo"]
}
```

This form is from the upstream docs and has not been tested in this repo.

## Setup steps

1. Install PhotoCraft from the [releases page](https://github.com/storytold/photocraft/releases) (or `getartcraft.com/apps/photocraft`). The installer includes `photocraft-cli`.
2. Confirm the CLI path: `"C:\Program Files\PhotoCraft\photocraft-cli.exe" --version`.
3. Start (or restart) omp from this repo. omp discovers `.omp/mcp.json` automatically. Nothing needs to be running first, because the headless backend is self-contained.

## Verify the connection

- `/mcp list` in omp shows `photocraft` as connected.
- Ask the agent to create a document and save it, for example `doc_new` then `doc_save` to `check.png`. A saved file appearing in the repo root confirms both the engine and the write root. Delete it afterwards.

When the entry was added, omp loaded the server with PhotoCraft 0.13.0, and `doc_new` (64x64) followed by `doc_save` to a relative path wrote the PNG into the repo root. The probe file was then removed. Bridge mode and UI tools were not exercised.

## Available tools

| Area | Tools |
| --- | --- |
| Session and documents | `session_list`, `doc_new`, `doc_open`, `doc_place`, `doc_select`, `doc_save`, `doc_export`, `doc_export_layers`, `doc_export_data_sets`, `doc_import_data_sets`, `doc_close` |
| Inspect and preview | `doc_inspect` (layer tree, history, selection), `render_preview` and `doc_render_preview` (bounded PNG, `max_side` default 1024, max 2048) |
| Engine commands | `command_list` (discover ids and parameter docs), `command_run`, `command_batch` (ordered steps, stops at first error by default) |
| Background jobs | `jobs_list`, `jobs_cancel` |
| Bridge only | `ui_inspect`, `ui_screenshot`, `ui_pointer`, `ui_menu_invoke`, `ui_set`, `control_call` |

Resources `photocraft://document` and `photocraft://commands` return live JSON matching `doc_inspect` and `command_list`.

Nearly everything beyond file and session handling is an engine command run with `command_run`, for example `layer.newAdjustmentLayer.hueSaturation` or `filter.blur.gaussianBlur`. Use `command_list` with `filter` to find ids, or run `photocraft-cli commands --filter blur` from a terminal.

### File formats

`photocraft-cli convert` lists `.pcraft` (native, lossless), `.psd`, `.png`, `.jpg`, `.tif`, `.webp` and `.exr`, with extra options for TGA, DDS and DPX output. `doc_save` writes `.pcraft` natively and exports other formats by file extension. Which exact formats each MCP tool accepts is defined upstream, so check `command_list` and tool errors rather than assuming.

## Working safely

- **Experiment on a copy.** Run `command_run` with `image.duplicate` (or `history.newDocument`) first. Both create a new active document and leave the source unchanged.
- **Batches are not transactions.** `command_batch` keeps earlier successful steps when a later step fails. Inspect with `doc_inspect`, and undo with `command_run` and `{"id":"edit.undo","params":{}}` once per undoable history entry.
- **Undo does not restore files.** Anything already written to disk stays written.
- **Saves can overwrite.** Upstream notes file saves may replace existing targets. Commit or back up source art before letting the agent save into the repo.

## Bridge mode (optional, not configured)

Use this to have the agent work in a document you have open and to use the UI tools. Upstream steps:

1. Start the desktop app with a private token file (the app creates it if missing) and roots:

   ```powershell
   & "C:\Program Files\PhotoCraft\photocraft.exe" --control 7878 --control-token-file C:\path\outside\repo\control.token --automation-read-root . --automation-write-root .
   ```

2. Add a second entry in your user-level config (not the committed file, since the token path is machine-specific):

   ```json
   "photocraft-live": {
     "type": "stdio",
     "command": "C:\\Program Files\\PhotoCraft\\photocraft-cli.exe",
     "args": ["mcp", "--bridge", "127.0.0.1:7878", "--control-token-file", "C:\\path\\outside\\repo\\control.token"]
   }
   ```

In bridge mode the desktop process owns the roots. Keep the token file outside the repo so it is never committed, and avoid `--control-token` on the command line because environment and process lists can expose it. This setup follows upstream's docs and was not run here.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `/mcp list` shows `photocraft` failed, or `ENOENT` | `command` doesn't point at an existing file. Check `dir "C:\Program Files\PhotoCraft"` and update the path |
| `cannot open automation read root` | The root directory doesn't exist or `.` isn't what you expect. Start omp from the repo root, or create the folder |
| A path is refused when opening or saving | It is outside the granted roots. Use a path under the root, or widen the root |
| Tool calls fail but the server is connected | Read the tool error. Failures return `isError`, and a reply-budget error means the step may have completed, so check `doc_inspect` before retrying |
| `ui_*` tools fail | They need bridge mode and a running desktop app. The headless server rejects them |
| Server not listed in omp | Run omp from the repo root, validate the JSON, then `/mcp reload` |

## Security

- Upstream states that tool schemas are not authorization boundaries, and the server has no scoped sessions or separation between trusted and high-impact tools. Anything connected to the server can use every tool within the granted roots. Do not expose it through an untrusted broker, shell, proxy or remote service.
- Stdio MCP opens no network listener. Bridge mode authenticates its loopback connection with a bearer token, but that proves possession of the token, not restricted access.
- omp treats committed MCP definitions as trusted input, and `stdio` entries run arbitrary commands. Review `.omp/mcp.json` before opening an unfamiliar checkout.

## Scope

This covers PhotoCraft's own `photocraft-cli mcp` server as documented in the PhotoCraft repo. ArtCraft's other apps and any broader ArtCraft agent integration are separate and not configured here.
