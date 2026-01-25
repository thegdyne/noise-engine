## Implementation Request

You are implementing a software system. The specification below has been reviewed and validated through multiple rounds of dual-AI review (Claude + GPT) and is ready for implementation.

### Instructions
1. **Follow the specification EXACTLY** - it has been refined to resolve ambiguities and edge cases
2. **Do not deviate** from the data models, error codes, or structures defined
3. **If something seems unclear**, the spec is authoritative - implement as written
4. **Security warnings** in the spec are acknowledged risks, not implementation blockers
5. **Ask no clarifying questions** - the spec contains everything needed

### Deliverables
- Complete working implementation
- All endpoints/features functional as specified
- Error handling as specified
- Ready to run

---

## FROZEN SPECIFICATION

## Overview / Problem Statement
The system uses a unified modulation bus in SuperCollider (SC) where modulation “targets” are addressed by a canonical **149-column** layout (columns **0–148**). Python boids generate per-tick modulation contributions and must transmit them to SC so SC applies boid offsets onto unified target values.

Currently, the Python boid controller incorrectly splits routing at column 80 and sends generator-parameter contributions (cols 0–79) to a legacy OSC path (`/noise/gen/boid/offsets`) instead of the unified path (`/noise/boid/offsets`). Additionally, several Python/UI components still assume a 151-column grid and an FX range ending at column 150, contradicting the canonical unified layout.

This specification defines an unambiguous behavioral contract for:
1) consistent use of a **149x16** boid grid, and
2) unified routing and payload semantics so **all boid contributions across cols 0–148** modulate unified bus targets (including generator parameters).

## Goals
1. **Unified Routing:** All boid modulation offsets for any column 0–148 are sent only via OSC address `/noise/boid/offsets`.
2. **Canonical Grid Dimensions:** All boid and boid-UI code uses `GRID_COLS=149` and validates within `col ∈ [0,148]`, `row ∈ [0,15]`.
3. **Deterministic Mapping & Aggregation:** Mapping from `(row,col)` to unified target index and aggregation semantics are explicitly defined and deterministic.
4. **Robust Connection Behavior:** Sender acquisition, caching, send-failure handling, and reconnection behavior are explicitly defined (including race-prone transitions).
5. **Consistent Tick Snapshot:** Contributions, positions, and cell values emitted per tick correspond to the same post-physics-tick snapshot, and visualization emission responsibility is unambiguous.

## Non-Goals
1. Removing legacy code/artifacts (e.g., deleting `src/utils/boid_gen_router.py` or removing SC legacy OSC handlers). They may remain but must be unused by boids after this migration.
2. Changing SC bus layout, SC target ordering, tick rates, or SC-side application logic.
3. Changing boid physics, contribution computation logic, or GUI styling beyond dimension/range correctness.
4. Introducing new modulation targets or changing the number of columns/rows.

## Invariants
1. **Canonical Layout Source of Truth:** `supercollider/core/bus_unification.scd` defines the canonical unified target ordering and total count:
   - Unified target count: **149** targets
   - Unified target indices: **0..148** inclusive
2. **Canonical Boid Grid Dimensions:**
   - `GRID_COLS = 149` (col indices 0..148)
   - `GRID_ROWS = 16` (row indices 0..15)
3. **Semantic Column Ranges (must match UI labels, zoning, and validation):**
   - Gen Core: cols **0–39**
   - Gen Custom: cols **40–79**
   - Mod Slots: cols **80–107**
   - Channels: cols **108–131**
   - FX: cols **132–148**
4. **Unified OSC Routing Only:** Boid runtime MUST NOT emit boid offsets to `/noise/gen/boid/offsets`. All boid offsets go only to `/noise/boid/offsets`.
5. **Unified Target Index Domain for OSC Payload:** The boid offsets OSC message uses **unified target indices** (0..148), not absolute SC bus numbers.
6. **Row Does Not Select a Different Unified Target:** The unified target index is determined solely by column. Row is for simulation/visualization only.
7. **OSC Numeric Types Are Semantically Significant:**
   - `targetIndex` MUST be transmitted as OSC **int32** (type tag `'i'`).
   - `offset` MUST be transmitted as OSC **float32** (type tag `'f'`).

## Data Models
### Contribution (raw, from engine)
A contribution is a triple:
- `row: int` in [0..15]
- `col: int` in [0..148]
- `value: float` finite (not NaN/Inf)

Produced each tick by:
- `contributions: List[Tuple[int, int, float]]`

### Unified Target Mapping
A pure mapping function exists in Python:

**Function name/location (canonical):**
- `src/utils/boid_bus.py:grid_to_bus(row: int, col: int) -> int`

**Behavioral contract:**
- For valid inputs (`0<=row<=15` and `0<=col<=148`), it MUST return:
  - `target_index = col`
- For invalid inputs (including but not limited to `col==149`, `col<0`, `row<0`, `row>15`, `col>148`), it MUST raise `ValueError`.
- It MUST be pure/deterministic (no IO, no time dependence, no external state).

### Aggregated Offsets (per tick)
After mapping and filtering, offsets are aggregated into:
- `offsets_by_target: Dict[int, float]` where:
  - key: `target_index` in [0..148]
  - value: aggregated `offset: float` finite

**Aggregation rule (normative; row explicitly ignored):**
- Aggregation is strictly **by column/target**:
  - `offsets_by_target[col] = Σ value_i` for all contributions whose `col` equals that target’s column, regardless of `row`.

### OSC Message: `/noise/boid/offsets`
**Address:** `/noise/boid/offsets`

**Arguments:** a flat, even-length list of pairs:
- `[targetIndex0, offset0, targetIndex1, offset1, ...]`

**Payload construction rules (normative):**
1. Build `offsets_by_target` using mapping + summation (by column; row ignored).
2. Drop any target where the aggregated offset is exactly `0.0` after summation.
3. Serialize pairs sorted by ascending `targetIndex` to guarantee deterministic ordering.
4. **Type requirements (normative):**
   - `targetIndex` MUST be encoded as OSC int32 (`'i'`) for every pair.
   - `offset` MUST be encoded as OSC float32 (`'f'`) for every pair.

**Maximum size invariant:**
- At most 149 pairs (298 numeric arguments).

### Required Interfaces (for dependency clarity)
#### `OscClient` (authoritative connection state + typed send capability)
BoidController MUST hold a reference `self._osc_client` that conforms to:

- `is_connected() -> bool`  
  Returns current connection status. This is the **sole authority** used by `_get_bus_sender()` to gate sender creation and use.

- `send(address: str, args: list) -> None` **OR** an equivalent typed-builder API (see below).  
  Sends an OSC message.

**Normative typing requirement:** the `OscClient` implementation MUST provide a way to ensure:
- Python-side indices are transmitted with OSC type `'i'` (int32)
- Python-side offsets are transmitted with OSC type `'f'` (float32)

If the existing OSC library does not guarantee `'i'` for Python `int` values, the implementation MUST use a typed message builder / explicit type-tag API.

#### Normative OSC int32/float32 encoding mechanism (implementation contract)
When constructing/sending `/noise/boid/offsets`, the implementation MUST ensure explicit OSC typing if there is any risk of auto-coercion.

Minimal normative example using `python-osc` style builders (or equivalent):
- For each pair:
  - `add_arg(targetIndex, arg_type='i')`
  - `add_arg(offset, arg_type='f')`

Example (illustrative, normative behavior):
```python
from pythonosc.osc_message_builder import OscMessageBuilder

b = OscMessageBuilder(address="/noise/boid/offsets")
b.add_arg(int(target_index), arg_type="i")   # MUST be 'i'
b.add_arg(float(offset), arg_type="f")       # MUST be 'f'
msg = b.build()
udp_client.send(msg)
```

If the codebase wraps OSC differently, an adapter MUST exist such that `BoidBusSender` can request `'i'` and `'f'` encodings with equivalent guarantees.

#### `BoidBusSender`
A sender is responsible for validation/mapping/aggregation and OSC send.

Canonical constructor signature (normative):
- `BoidBusSender(osc_client: OscClient, address: str = "/noise/boid/offsets")`

The sender MUST NOT perform blocking work in `send_offsets`.

## State Machine / States
### BoidController Tick Lifecycle (per tick)
Each tick has three phases:
1. **Physics phase:** advance boid simulation
2. **Snapshot phase:** collect outputs (contributions, positions, cell values) from the same post-tick state
3. **IO + Emit phase:** attempt OSC send, then emit visualization signals

### Controller Connectivity States
The controller maintains a cached sender reference (`self._bus_sender`) that may be `None`.

#### State: Disabled
- Condition: `self._state.enabled == False`
- Behavior:
  - Do not call `engine.tick()`
  - Do not send OSC
  - Do not emit visualization signals from `_tick()`

#### State: Enabled, Sender Unavailable
- Condition: `self._state.enabled == True` AND `_get_bus_sender()` returns `None` OR `_get_bus_sender()` raised during construction and was handled in `_tick()` as unavailable
- Behavior per tick:
  1. `engine.tick()`
  2. Collect snapshot: `contributions`, `positions`, `cell_values` (post-tick)
  3. Skip OSC send
  4. Emit visualization signals using the snapshot from this tick

#### State: Enabled, Sender Available
- Condition: `self._state.enabled == True` AND `_get_bus_sender()` returns a sender instance
- Behavior per tick:
  1. `engine.tick()`
  2. Collect snapshot: `contributions`, `positions`, `cell_values` (post-tick)
  3. Attempt `bus_sender.send_offsets(contributions)`
     - If send fails (exception), handle per “Errors” and treat sender as unavailable going forward
     - If send results in an empty payload (no-op), that is still a successful call
  4. Emit visualization signals using the same snapshot

### Snapshot Consistency Contract (Visualization + OSC)
Within a single `_tick()` invocation:
- `engine.tick()` MUST be called exactly once.
- `contributions`, `positions`, and `cell_values` MUST all be retrieved after that `engine.tick()` call and MUST correspond to the same post-tick engine state.
- `send_offsets(contributions)` MUST use the `contributions` from that same post-tick snapshot.
- **Visualization emission location (normative):**
  - `positions_updated.emit(...)` and `cells_updated.emit(...)` MUST be invoked by `BoidController._tick()` (not by the sender).
  - These emits MUST occur after the `send_offsets(...)` attempt returns (or is skipped due to no sender), using the snapshot collected in the Snapshot phase.
  - Visualization emits MUST occur for every enabled tick regardless of OSC availability, send success, or “empty payload” no-op.

## Error Handling / Errors
### Responsibility Boundaries (normative)
- **BoidController** responsibilities:
  - Call `send_offsets(raw_contributions)` without pre-mapping and without pre-aggregating.
  - Catch exceptions from:
    - `_get_bus_sender()` sender construction (if any), and treat as sender unavailable for that tick
    - `send_offsets()` OSC transmission failures
  - Never allow exceptions to escape `_tick()`.
  - On send exception: mark sender unusable for subsequent ticks (details below).
  - Emit visualization signals after send attempt/skip per Snapshot Consistency.
- **BoidBusSender** responsibilities:
  - Validate, map, and aggregate raw contributions.
  - Ensure only valid, well-typed, well-formed OSC payloads are sent (including int32 indices and float32 offsets).
  - Never send legacy OSC paths.
  - Never emit visualization signals.

### `BoidBusSender.send_offsets()` exception and validation contract (P0)
`send_offsets(contributions)` MUST follow these rules:
1. **Validation/mapping failures MUST NOT raise:**
   - Invalid contributions (out-of-range row/col, NaN/Inf value, mapping `ValueError`) MUST be dropped silently (optionally logged) and MUST NOT raise exceptions.
2. **`osc_client.send(...)` failures MUST propagate:**
   - `send_offsets()` MUST NOT catch or suppress exceptions thrown by the underlying OSC transmission call (socket/disconnect/etc.).
   - Such exceptions MUST propagate to the controller so the controller can invalidate the cached sender.
3. **Empty/no-op is normal:**
   - If all contributions are dropped or aggregate to zero, `send_offsets()` MUST return normally without sending any OSC message.

### Contribution Validation (performed inside `BoidBusSender.send_offsets`)
For each raw contribution `(row,col,value)`:
- If `value` is not finite (NaN/Inf): drop it.
- Else call `grid_to_bus(row,col)`:
  - If it raises `ValueError`: drop the contribution and continue.
  - If it returns `target_index`: continue.
- After mapping, perform a defensive range check:
  - If `target_index` is not in `[0..148]`: drop the contribution and continue.
- These drops MUST NOT raise exceptions and MUST NOT prevent other valid contributions from being sent.

### Aggregation and Empty Payload (explicit no-op semantics)
- After filtering+aggregation:
  - If there are **no** targets with non-zero aggregated offsets:
    - `send_offsets` MUST NOT send an OSC message (no-op).
    - `send_offsets` MUST return normally (no exception).
    - The controller MUST still emit visualization signals for that tick (per Snapshot Consistency).

### Send Failures and Sender Unavailability
A send failure is any exception thrown while attempting to transmit OSC (e.g., socket error, disconnected client).

Normative behavior:
1. `BoidController._tick()` MUST wrap `bus_sender.send_offsets(...)` in try/except.
2. On exception:
   - The controller MUST set `self._bus_sender = None` (invalidate cache).
   - The controller MUST continue and still emit visualization signals for the tick.

### `_get_bus_sender()` Acquisition, Caching, and Recovery Contract (including race semantics)
`BoidController._get_bus_sender()` is the only method `_tick()` uses to acquire a sender.

Normative behavior:
1. **Caching:** If `self._bus_sender` is non-None, `_get_bus_sender()` MUST return it without creating a new sender.
2. **Connection gating (authoritative):** If `self._osc_client.is_connected()` is `False`, `_get_bus_sender()` MUST return `None` and MUST NOT create a sender.
3. **Atomicity / race-prone transition rule (normative):**
   - `_get_bus_sender()` MUST check `self._osc_client.is_connected()` immediately before constructing a sender.
   - If `BoidBusSender(...)` constructor raises any exception (e.g., because connection dropped between checks), the exception MUST propagate out of `_get_bus_sender()` and `self._bus_sender` cache MUST remain `None`.
   - `_tick()` MUST catch this exception and treat it as “sender unavailable” for that tick (i.e., proceed without OSC send and still emit visualization).
4. **Lazy initialization:** If `self._osc_client.is_connected()` is `True` and `self._bus_sender` is None, `_get_bus_sender()` MUST create:
   - `self._bus_sender = BoidBusSender(self._osc_client, address="/noise/boid/offsets")`
   and then return it.
5. **Recovery:** After a send failure invalidates the cache, subsequent ticks call `_get_bus_sender()`; once `self._osc_client.is_connected()` becomes `True` again, a new sender MUST be created and sending resumes automatically.

Additional constraints:
- `_get_bus_sender()` MUST be non-blocking (no sleeps, no network handshakes inside tick). It may consult already-known connection state only.

### Legacy Routing Prohibition (enforced at runtime)
- The boid controller and boid bus sender MUST NOT instantiate or call any legacy generator-specific boid router.
- No runtime code path initiated by boids may emit `/noise/gen/boid/offsets`.

## Behavioral Implementation Requirements
### Grid/Range Corrections (must be applied)
- `src/boids/boid_engine.py`: `GRID_COLS = 149`
- `src/boids/boid_state.py`: FX range checks and stored ranges use **132–148** inclusive (never 150)
- `src/gui/boid_overlay.py`: scale/draw using **149** columns
- `src/gui/boid_panel.py`: scale/draw using **149** columns; UI text references **132–148**

### Boid Controller Routing Change (must be applied)
- `src/boids/boid_controller.py`:
  - Remove generator-routing split and any reference/import/use of `BoidGenRouter`
  - In `_tick()`, send all contributions (any col 0–148) only via unified bus sender

Normative `_tick()` ordering (with explicit exception handling responsibilities):
1. If disabled: return
2. `engine.tick()`
3. Read snapshot (post-tick): `contributions`, `positions`, `cell_values`
4. Attempt to acquire sender:
   - `sender = _get_bus_sender()` inside try/except; on exception treat as `None`
5. If `sender` is not None:
   - call `sender.send_offsets(contributions)` inside try/except
   - on exception: set `self._bus_sender = None`
6. Emit `positions_updated(positions)` and `cells_updated(cell_values)` using the snapshot from step 3 (always for enabled ticks)

### BoidBusSender `send_offsets` Contract (must be implemented to spec)
`send_offsets(contributions)` MUST:
1. Validate contributions (finite values, valid row/col)
2. Map via `grid_to_bus(row,col)` (returns col; may raise `ValueError` which is handled by dropping)
3. Defensively drop mapped indices not in `[0..148]`
4. Aggregate strictly by column/target using summation (row ignored)
5. Build sorted payload with explicit OSC types: `[i(targetIndex), f(offset), ...]`
6. If payload empty: no-op, return normally
7. Otherwise send exactly one OSC message:
   - address `/noise/boid/offsets`
   - with alternating int32/float32 typed args
8. Not catch/suppress exceptions from the underlying OSC send call; those propagate

## Acceptance Criteria / Acceptance Tests
### A. Mapping Contract and Aggregation (explicit row rule)
1. **Mapping identity across rows:**
   - For any `row in [0..15]` and `col in [0..148]`, `grid_to_bus(row,col)` returns `col`.
2. **Aggregation strictly by column (row ignored):**
   - Given contributions `[(0, 10, 0.2), (5, 10, -0.05), (2, 11, 1.0)]`,
   - `send_offsets` aggregates by column:
     - target 10 offset `0.15`
     - target 11 offset `1.0`

### B. OSC Payload Types and Encoding Mechanism
1. When at least one offset is sent:
   - The OSC argument list alternates index/offset pairs.
   - Each `targetIndex` is encoded as OSC int32 (type tag `'i'`), not float.
   - Each `offset` is encoded as OSC float32 (type tag `'f'`).
2. If the OSC library does not guarantee int32 for Python `int`, implementation uses an explicit type-tag mechanism (builder or wrappers) to force `'i'` and `'f'` as specified.
3. SC-side observable expectation:
   - In the SC OSCdef handler for boid offsets, the received `targetIndex` values are `Integer` (not `Float`).

### C. Unified Routing (No Split)
1. When boids are enabled and contributions include cols in both ranges (e.g., col 10 and col 120):
   - only `/noise/boid/offsets` is emitted.
2. `/noise/gen/boid/offsets` is never emitted during boid operation.

### D. Sender Unavailability, Constructor Race, and Recovery
1. If `self._osc_client.is_connected()` is `False`:
   - `_get_bus_sender()` returns `None`
   - `_tick()` still advances physics and emits visualization signals
   - No OSC offsets are sent
2. If connection drops during sender construction and `BoidBusSender(...)` raises:
   - `_get_bus_sender()` propagates the exception and cache remains `None`
   - `_tick()` catches it, sends nothing, and still emits visualization signals
3. If `send_offsets` throws due to transmission failure:
   - `send_offsets` propagates the exception
   - `_tick()` catches it, invalidates cached sender (`self._bus_sender=None`), and continues
   - Visualization signals still emit for that tick
4. If `self._osc_client.is_connected()` transitions to `True` later:
   - `_get_bus_sender()` creates and caches a new sender automatically
   - Subsequent ticks resume sending offsets without restarting the app

### E. Empty Payload Behavior and Visualization Timing
1. If all contributions are invalid or aggregate to exactly zero across all targets:
   - `send_offsets` sends no OSC message and returns normally
   - `_tick()` still emits `positions_updated` and `cells_updated` for that tick
2. Visualization emission occurs only in `BoidController._tick()` and always after the send attempt/skip returns, using the tick snapshot (no sender-driven emits).

### F. Grid Dimensions and FX Range Correctness
1. Any rendering/scaling uses 149 columns:
   - overlay/panel compute `cell_w = w / 149.0` and positions derived from `/ 149.0`
2. FX zone logic applies only to cols 132–148 inclusive:
   - No references to cols 149–150 exist in behavior or checks
3. UI text that mentions FX columns says “132–148”.

### G. End-to-End Generator Modulation Through Unified Bus
1. With SC booted using unified bus unification scripts and Python connected:
   - enabling boids produces audible/observable modulation on generator parameters (cols 0–79)
2. This modulation occurs without any legacy handler participation and continues to work across Python restart/reconnect.

---

## Spec Metadata
- **Spec Version**: 4
- **Grind Rounds**: 3
- **Review Mode**: dealbreakers_p0_design
- **Generated**: 2026-01-25
- **Total Cost**: $0.35
- **Validated By**: Claude (AI0 + AI1) + GPT (AI2)


---

Begin implementation now.

