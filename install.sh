#!/bin/sh
# symlink claude-shard 進 ~/.claude(repo 是唯一源頭)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
CLAUDE="$HOME/.claude"

link() { # $1=repo path, $2=target path
  if [ -e "$2" ] && [ ! -L "$2" ]; then
    echo "SKIP: $2 已存在且不是 symlink——手動處理後重跑"; return
  fi
  rm -f "$2"
  ln -s "$1" "$2"
  echo "linked: $2 -> $1"
}

mkdir -p "$CLAUDE/skills" "$CLAUDE/agents" "$CLAUDE/shards/locks"
link "$HERE/skills/shard"      "$CLAUDE/skills/shard"
link "$HERE/skills/shards"     "$CLAUDE/skills/shards"
link "$HERE/agents/worker.md"  "$CLAUDE/agents/worker.md"

POLICY="$CLAUDE/shards/policy.json"
if [ ! -f "$POLICY" ]; then
  cat > "$POLICY" <<'EOF'
{
  "_comment": "per-repo land 策略 registry。_default=ask:沒登記的 repo 第一次 land 先偵測 deploy 訊號、停下問一次,答案記回 repos。策略: local-merge | merge-no-push | pr",
  "_default": "ask",
  "repos": {}
}
EOF
  echo "created: $POLICY"
fi
echo "done — 新 skill 下個 Claude Code session 生效"
