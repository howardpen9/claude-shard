# README concept art

| File | Use |
|------|-----|
| `hero.png` | Top banner · brand + live workers |
| `before-after.png` | Why shard exists |
| `flow.png` | fire → work → land → safe |
| `commands.png` | Command cheat sheet |
| `src/*.html` | Source for re-render |

## Re-render

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT="$(pwd)/docs/assets"

"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1280,640 --screenshot="$OUT/hero.png" \
  "file://$OUT/src/01-hero.html"

"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1280,720 --screenshot="$OUT/before-after.png" \
  "file://$OUT/src/02-before-after.html"

"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1280,560 --screenshot="$OUT/flow.png" \
  "file://$OUT/src/03-flow.html"

"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1280,480 --screenshot="$OUT/commands.png" \
  "file://$OUT/src/04-commands.html"
```
