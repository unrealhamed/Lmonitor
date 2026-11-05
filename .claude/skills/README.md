# Claude Code skills

Design skills for working on Lmonitor's UI with Claude Code. They load automatically in any
Claude Code session opened in this repository.

| Skill(s) | Source | License |
|---|---|---|
| animate, animation-performance, animation-vocabulary, apple-design, break-ui, choreograph, emil-design-eng, find-animation-opportunities, improve-animations, remove-animations, review-animations | https://github.com/emilkowalski/skills @ `c8a79627b59d72d764d6ab6f2c87c09a48169833` | MIT (`LICENSE-emilkowalski-skills`) |
| impeccable (v4.8.0) | https://github.com/pbakaus/impeccable @ `c8891a9ae865d6ee311836ae5199bfce0fe115b1` (`.claude/skills/impeccable`, the same build `npx impeccable install` writes) | Apache-2.0 (`LICENSE-impeccable`) |
| taste | https://github.com/senlindesign/taste-skill @ `6dce223f2f5665d3636ca9a44ec3a7aa1322a9b8` | README says MIT; the repo has no LICENSE file |

Not included from emilkowalski/skills (not applicable here): animate-expo, ask-sonner,
mobile-native, pick-ui-library, prototype, write-swift.

## Notes

- These skills target the web (CSS/React/HTML). For Lmonitor's Qt/QML interface
  (`lmonitor/qt/qml`), apply the principles and translate the APIs, e.g. CSS
  `transition`/`ease-out` -> QML `Behavior`/`NumberAnimation` with `Easing.OutCubic`.
- Impeccable was installed without its hooks (the `npx impeccable install --no-hooks`
  equivalent): its detector scans HTML/CSS/JSX/Vue/Svelte, not QML, and the hook commands
  use POSIX shell syntax that does not run from a Windows shell. Its launcher
  (`impeccable/scripts/impeccable`, `.cmd` on Windows) downloads the engine binary from the
  project's GitHub releases on first use.
- `taste` analyzes a live website URL and needs the Playwright MCP server (see `/.mcp.json`).

## Updating

- Impeccable: `npx impeccable update`, or re-copy `.claude/skills/impeccable` from a newer
  upstream commit.
- Others: re-copy the folders from a newer upstream commit and update the table above.
