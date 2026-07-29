# Monorepo note — claude-shard

This package lives in the **coding-agent-mcps** workspace as an **ops example + Claude Code skill source**, next to media / peer / review packages.

| Item | Value |
| --- | --- |
| Public publish remote | https://github.com/howardpen9/claude-shard |
| Install surface | `./install.sh` → symlinks under `~/.claude` (not npm) |
| Role in monorepo | Claude Code **dispatcher + auto-land** pattern; reference for worktree parallel + deploy-safe merge |
| Primary host | **Claude Code only** (skill + `agents/worker.md`) |

**Not the same layer as:**

| Package | Layer |
| --- | --- |
| `grok-peer/` | Grok → peer slash (Codex / Claude / Kimi / Gemini) |
| `grok-build-media/` | Host → Grok Build **media** |
| `grok-mcp/` / `kimi-code-mcp/` | Host → **review / second opinion** MCP |

**Publish workflow:** edit here (or in a public checkout), then:

```bash
./scripts/sync-public-remote.sh claude-shard --dry-run
./scripts/sync-public-remote.sh claude-shard --push -m "sync: claude-shard …"
```

Do not treat the monorepo git remote as the install URL for end users — public clone URL is `howardpen9/claude-shard`.

See monorepo root `AGENTS.md` · `docs/PLAYBOOK.md` § parallel / Claude Code.
