@AGENTS.md

# Claude Code notes

AGENTS.md above is the source of truth for every agent. This file only adds what is specific to Claude Code. omp also reads this file, so each note below names the tool it applies to.

- **MCP config.** Claude Code loads the three servers from [`.mcp.json`](.mcp.json). omp uses [`.omp/mcp.json`](.omp/mcp.json). Keep the two in sync: when you change one, change the other and the matching file in `docs/`. Approve the servers when Claude Code first prompts for them, and check them with `/mcp`.
- **Tool names.** In Claude Code, the bare tool names in AGENTS.md are `mcp__<server>__<tool>`, for example `mcp__Roblox_Studio__script_read`, `mcp__blender__look` and `mcp__photocraft__render_preview`.
- **"subagent" in AGENTS.md** means the Roblox Studio tool `mcp__Roblox_Studio__subagent` (types `explore` and `playtest`). It is not Claude Code's Agent tool.
- **Skills** in [`.claude/skills/`](.claude/skills/) hold the step-by-step procedures: `mcp-status`, `studio-script-edit`, `studio-playtest`, `studio-insert-asset`, `blender-prop` and `photocraft-image`.
- **Subagents** in [`.claude/agents/`](.claude/agents/): `blender-artist` and `photocraft-artist` do asset work so that the `look` and `render_preview` images stay out of the main conversation. They can't ask the user anything, so they return assets that need attribution instead of importing them. Put those to the user (AGENTS.md rule 6) and re-dispatch once approved. `luau-reviewer` checks Studio changes against AGENTS.md before you call a feature done.
- **Permissions** in [`.claude/settings.json`](.claude/settings.json) allow the read-only inspection tools, ask before Roblox Studio generation or edits to MCP and settings files, and deny `record_trajectory_feedback` plus the paid Blender generators `generate_3d` and `generate_gaussian_world`. Personal overrides go in `.claude/settings.local.json`, which is gitignored. That includes pre-allowing the Blender and PhotoCraft write tools, which the shared settings deliberately leave to each person.
- **macOS and other installs.** The committed Studio and PhotoCraft entries are Windows-specific. Override them per machine with `claude mcp add --scope local` (see the docs in `docs/`). Don't edit the committed entries.
