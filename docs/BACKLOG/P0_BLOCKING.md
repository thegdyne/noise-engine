# P0 Blocking


## Preset Pack Integration ⚠️ CRITICAL
**Impact:** Blocks Imaginarium workflow — users can't auto-load pack from preset

1. Add `pack: Optional[str] = None` to `PresetState` in `preset_schema.py`
2. Update `to_dict()` and `from_dict()` to include pack
3. In `main_frame.py._apply_preset()`, switch pack BEFORE loading slots
4. In `main_frame.py._save_preset()`, include current pack

## UI: Disable Header Buttons Until SC Connected
User can load packs/presets before SC connection, causing wasted clicks.
- Add `_set_header_buttons_enabled(enabled: bool)` method
- Only CONNECT, CONSOLE, RESTART enabled on startup
- Enable all after SC connection confirmed

## SC: getSynchronous Crash on Server Disconnect
`Server-getControlBusValue only supports local servers` error in `mod_osc.scd` and `mod_apply_v2.scd`.
- Wrap getSynchronous calls in try/catch, or use Bus.get with callback

## CLEAR MOD Button
Button to remove all modulation routes (main UI + mod matrix window).
- Requires `/noise/mod/route/clear_all` OSC message (see below)

## Mod Routing: OSC Clear All
Loading preset or CLEAR MOD clears UI but SC keeps old routes.
1. Add to `supercollider/core/mod_routing.scd`:
   ```supercollider
   OSCdef(\modRouteClearAll, { ~modRoutes.clear; }, '/noise/mod/route/clear_all');
   ```
2. Add to `src/config/__init__.py`: `'mod_route_clear_all': '/noise/mod/route/clear_all'`
3. Update `_on_mod_routes_cleared()` to send OSC clear message
