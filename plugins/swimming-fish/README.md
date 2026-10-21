# Swimming Fish: animated native ULS plugin

This is the **animation and settings** example. For the simplest possible screen start with Core's bundled [Hello World](https://github.com/mcangeli/universal-led-scoreboard/tree/feature/0.9.0-dynamic-team-registry/plugins/hello-world); for external data and text see [Daily Calendar](../daily-calendar/README.md).

## Source files

- `uls-plugin.toml`: plugin ID, version, API v1 screen capability and `swimming_fish:SwimmingFishScreen` entry point.
- `settings-schema.json`: dashboard fields for display duration, swimming speed, and fish color.
- `swimming_fish.py`: no-dependency frame renderer, with a configurable animation speed and palette.
- `README.md`: this walkthrough.

## How the renderer works

1. ULS starts a new plugin process for **each requested frame**. `__init__` sets defaults; `configure(settings)` receives validated dashboard values.
2. `render()` allocates `Framebuffer(64, 32)`, fills it with dark water using `frame.pixel(x, y, rgb)`, then draws the fish silhouette, moving tail and bubbles.
3. Animation position derives from `time.monotonic()` multiplied by the configured speed. **No in-memory animation counter survives between frames.**
4. `render()` returns the framebuffer. ULS serializes it to RGB pixels. No PNG, Pillow, display driver or physical LED matrix is needed in plugin code.
5. The ULS scheduler controls when this screen is eligible and how long it displays, using `display_seconds`.

The fish position wraps as time advances; its color is chosen from the validated `fish_color` settings field. To build your own animation, change the pixel-drawing loops while keeping the `render()` contract.

## Install and preview

In ULS **Plugin Manager → Available plugins**, select **Swimming Fish → Review & install**, then enable it. Alternatively review:

`https://github.com/mcangeli/uls-plugins/tree/main/plugins/swimming-fish`

Open Settings to change speed, color, and display duration. View it during non-live rotation using **Open Board View** or the physical 64×32 panel.

From a ULS checkout with this plugin directory available, render a frame locally:

```bash
PYTHONPATH=plugins/swimming-fish:. python3 - <<'PY'
from swimming_fish import SwimmingFishScreen
from pathlib import Path
screen = SwimmingFishScreen()
screen.configure({"animation_speed": 1.5, "fish_color": "blue"})
frame = screen.render()
assert (frame.width, frame.height) == (64, 32)
Path("/tmp/swimming-fish.ppm").write_bytes(frame.ppm())
PY
```

For manifest/schema validation and the subprocess worker contract, see the [ULS plugin development guide](https://github.com/mcangeli/universal-led-scoreboard/blob/feature/0.9.0-dynamic-team-registry/docs/PLUGIN-DEVELOPMENT.md). The plugin has no external dependencies and does not access the network.
