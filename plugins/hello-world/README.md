# Hello World: your first ULS plugin

This is an installable, dependency-free **ULS API v1 screen plugin**. It displays a configurable message on a 64×32 LED scoreboard. ULS Core remains separate from this repository.

## Files and why they exist

| File | Purpose |
| --- | --- |
| `uls-plugin.toml` | Identifies the plugin, its API version, capabilities and Python entry point. |
| `settings-schema.json` | Declares dashboard controls and validates their saved values. |
| `hello_world.py` | Implements the screen using ULS's `Framebuffer`. |
| `test_hello_world.py` | Checks framebuffer size and configurable output. |
| `README.md` | Explains installation and development. |

## How it runs

ULS discovers the TOML manifest without executing the plugin. After installation and enabling, the scheduler starts a separate Python worker for each eligible idle frame. The worker imports `hello_world:HelloWorldScreen`, constructs it, calls `configure(settings)`, then `render()`. The returned `Framebuffer(64,32)` becomes exactly 6,144 RGB bytes. Rendering must finish within the default 1.5-second timeout. No in-memory state survives between frames, and plugin code is **not sandboxed**.

The example uses no third-party libraries, HTTP requests, filesystem writes or persistent state. The `display_seconds` setting controls how long the host shows the plugin during idle rotation. A live game can suppress the plugin screen.

## Install from GitHub

In the ULS dashboard open **Plugin Manager** and enter:

```text
https://github.com/mcangeli/uls-plugins/tree/main/plugins/hello-world
```

Select **Review**, confirm `hello-world`, version `0.1.0` and the pinned commit, then **Install**. Enable the plugin, choose its display duration and message, and inspect **Open Board View** when no live game is taking priority. Installation does not enable it automatically. To uninstall, disable it first.

## Test locally

From a checkout of ULS Core with Python configured to import `universal_led`, and a separate checkout of this repository:

```bash
cd /path/to/universal-led-scoreboard
PYTHONPATH=/path/to/uls-plugins/plugins/hello-world:. python3 -m unittest test_hello_world -v
```

Check manifest and schema validation:

```bash
python3 - <<'PY'
from universal_led.plugin_manifest import load_plugin_manifest
from universal_led.plugin_settings_schema import load_settings_schema
package = '/path/to/uls-plugins/plugins/hello-world'
print(load_plugin_manifest(package))
print(load_settings_schema(package))
PY
```

Test the actual worker from the ULS Core directory:

```bash
python3 -m universal_led.native_plugin_worker \\
  /path/to/uls-plugins/plugins hello-world \\
  '{"display_seconds":12,"message":"HELLO"}' > /tmp/hello-world.rgb
wc -c /tmp/hello-world.rgb
```

Expected: **6144** bytes. The first worker argument is the **parent directory** containing the `hello-world` folder. Do not print debug messages to stdout in plugin code.

## Customize it

Change `message` in the dashboard or add a setting in `settings-schema.json` and read it in `configure()`. Draw with `frame.pixel(x,y,(r,g,b))` and `frame.text(text,x,y,color)`. The built-in font supports a limited uppercase character set; unsupported punctuation raises an exception. A ten-character string fits at x=2 using the 6-pixel glyph spacing. For more advanced screens, add your own rendering logic, but keep the 64×32 contract.

To publish an update, change the TOML `version`, commit the changes, review the new GitHub commit in Plugin Manager and update. ULS preserves enabled state and separately stored settings.

See the [ULS plugin developer guide](https://github.com/mcangeli/universal-led-scoreboard/blob/feature/0.9.0-dynamic-team-registry/docs/PLUGIN-DEVELOPMENT.md) for the full manifest and settings schema rules, security limits, and troubleshooting.
