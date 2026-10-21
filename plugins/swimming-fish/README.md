# Swimming Fish

A small animated 64×32 native ULS screen plugin, with a gold fish swimming across dark-blue water, moving tail and rising bubbles.

## GitHub review URL

`https://github.com/mcangeli/universal-led-scoreboard/tree/feature/0.9.0-dynamic-team-registry/plugins/swimming-fish`

Review in **Plugins → Review GitHub plugin**, then install it disabled. Its unique ID (`swimming-fish`) avoids the already-installed `hello-world` collision.

**Current limitation:** v0.9 plugin installation and inventory do not yet connect installed screens to the live rotation. Installation verifies the GitHub workflow; it does not automatically animate the board.

## Local preview

From the repository root:

```bash
PYTHONPATH=plugins/swimming-fish:. python3 - <<'PY'
from swimming_fish import SwimmingFishScreen
from pathlib import Path
Path('/tmp/swimming-fish.ppm').write_bytes(SwimmingFishScreen().render().ppm())
print('Wrote /tmp/swimming-fish.ppm')
PY
```

No third-party dependencies or network calls.
