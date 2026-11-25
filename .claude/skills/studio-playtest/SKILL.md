---
name: studio-playtest
description: Use when a Roblox gameplay, UI or networked feature needs to be tested or verified in Roblox Studio play mode, or before calling a Roblox feature done.
---

# Playtesting in Roblox Studio

A feature is done when you have watched it work in play mode on both the Client and the Server data models. A returned tool call doesn't count.

## Steps

1. **State.** Run `get_studio_state`. If a playtest is already running and you need to edit first, stop it.
2. **Start** with `start_stop_play`.
3. **Drive the game like a player** with `character_navigation`, `user_keyboard_input` and `user_mouse_input`. Test UI through real input on UI instances, not by calling handlers directly. For long scripted scenarios, use the Studio `subagent` tool with type `playtest`.
4. **Observe:**
   - `get_console_output` for errors and warnings.
   - `screen_capture`, optionally with a camera position and look-at target, for visual feedback.
   - `execute_luau` on **Server** and on **Client**, returning values that prove the state: currency, inventory, positions, UI visibility.
5. **Edge cases** from the AGENTS.md definition of done: respawn, leaving mid-action and rejoining. For UI, check phone, tablet and desktop with the Studio device-simulation skill (`skill` tool).
6. **Stop** with `start_stop_play` before any further edits.

## Report

| Check | Result |
| --- | --- |
| Console errors and warnings | none, or a quote of each one |
| Server state | the values returned |
| Client state | the values returned |
| Visual | what the screen capture showed |
| Not tested | multi-client play (no tool covers it, so ask the user to run it), plus anything else you skipped |
