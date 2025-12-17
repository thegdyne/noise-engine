# Integr8TOR - Event Stream Architecture

**Status:** Design Complete  
**Created:** December 17, 2025  
**Version:** 1.0

---

## Vision

A real-time event streaming backbone that integrates every parameter change in Noise Engine, making it available to an ecosystem of consumers — visual layers, analysers, recorders, other synths, external tools.

**Current:** Python ↔ OSC ↔ SuperCollider (point-to-point, ephemeral)

**Future:** Everything publishes to stream → anything can subscribe

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Noise Engine│     │ Visual Layer│     │  Recorder   │
│   (Python)  │     │  (TouchDes) │     │  (Python)   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │ publish           │ subscribe         │ subscribe
       ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────┐
│                 KAFKA / REDPANDA                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │ noise.params       (keyed by path)              │ │
│  │ noise.mod          (keyed by bus id)            │ │
│  │ noise.audio        (keyed by source)            │ │
│  │ noise.events       (keyed by type)              │ │
│  │ noise.state        (compacted, keyed)           │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## Design Principles

| Principle | Decision |
|-----------|----------|
| Audio control latency | **Keep OSC** (sub-2ms required) |
| Ecosystem distribution | Kafka/Redpanda (5-20ms acceptable) |
| Delivery guarantee | **At-least-once + idempotent consumers** |
| Topic count | **5 topics** (not hundreds) |
| Message ordering | Per-partition via keys |

### Three-Lane Architecture

Noise Engine uses three communication layers, each optimised for its purpose:

| Lane | Transport | Latency | Purpose |
|------|-----------|---------|---------|
| GUI ↔ GUI | Qt signals | <1ms | Intra-GUI state (fast, synchronous, no serialization) |
| Python ↔ SC | OSC | <2ms | Audio control (tight loop, must be fast) |
| Engine → World | Integr8tor | 10-20ms | Broadcast for external consumers (visuals, recorders) |

**Critical:** Integr8tor is a side-channel that can be unplugged without breaking synthesis. Visuals can crash, Kafka can be down, and the synth still runs.

### Publish Semantics

Publish is **non-blocking** - the engine never waits for consumers. But it's not "fire and forget":

- Producer uses `enable.idempotence=True` and `acks=all`
- Delivery failures surface via callback, not UI latency
- Failures are logged/metered, never block audio path

```python
def set_param(self, slot, param, value):
    # Fast path (audio) - always runs
    self.osc.send(f'/noise/gen/{slot}/{param}', value)
    
    # Broadcast path (ecosystem) - non-blocking, failures logged
    self.integr8tor.publish_param(slot, param, value)
```

---

## Topics (5 Total)

| Topic | Key Examples | Partitions | Retention | Purpose |
|-------|--------------|------------|-----------|---------|
| `noise.params` | `gen.1.cutoff`, `master.volume`, `mod.2.rate` | 4 | 1 hour | All parameter changes |
| `noise.mod` | `bus.0`, `bus.15` | 1 | 1 minute | Mod bus values @ 30fps |
| `noise.audio` | `gen.1`, `master` | 1 | 1 minute | Level meters @ 30fps |
| `noise.events` | `note_on`, `preset_load` | 1 | 24 hours | Sparse events |
| `noise.state` | `preset`, `routing` | 1 | Compacted | Current state (latest only) |

### Topic Separation: Params vs Mod Bus Values

**`noise.params`** - User/preset-driven parameter changes:
- Generator params: `gen.1.cutoff`, `gen.3.frequency`
- Mod source knobs: `mod.2.rate`, `mod.1.depth` 
- Master params: `master.volume`, `master.compressor.ratio`

**`noise.mod`** - Continuous modulation output (30fps telemetry):
- LFO/Sloth bus values: `bus.0`, `bus.1`, ... `bus.15`
- Used for visual animation, not for replay (too dense)

Mod source *knobs* go through `noise.params` for recording/replay. Mod *output values* go through `noise.mod` for visuals only.

### Keys Are Mandatory

Kafka ordering is per-partition. Keys determine partition assignment:

```python
# ❌ No key = random partition = no ordering guarantee
producer.produce('noise.params', msg)

# ✅ Keyed = same partition = ordered per parameter
producer.produce('noise.params', msg, key=b'gen.1.cutoff')
```

Compacted topics (`noise.state`) require keys or compaction is meaningless.

**Note:** The Kafka key matches the `path` field in the message. Consumers can filter by key without parsing the payload.

---

## Message Envelope

Every message includes deduplication and replay-safety fields:

```python
{
    "v": 1,                          # Schema version
    "session_id": "uuid-string",     # Unique per performance (shared by all producers)
    "producer_id": "python.gui",     # Unique per producer (for multi-producer dedupe)
    "seq": 12345,                    # Monotonic per producer
    "ts_ms": 1702828800000,          # Millisecond timestamp
    "path": "gen.1.cutoff",          # Canonical parameter path
    "value": 0.75,                   # Normalized 0-1 (authoritative)
    "value_mapped": 2400.0,          # Optional: Hz, dB, etc. (derived, not required)
    "actor": "user",                 # user | mod | midi | preset | replay | telemetry
    "source": "python"               # python | supercollider | bridge
}
```

### Actor Rules

| Actor | Meaning | Recorder | Replay Yields |
|-------|---------|----------|---------------|
| `user` | Human interaction | ✅ Store | ✅ Yes |
| `mod` | Modulation system | ✅ Store | ❌ No |
| `midi` | External MIDI | ✅ Store | ❌ No |
| `preset` | Preset load | ✅ Store | ❌ No |
| `telemetry` | Meters/levels | ❌ Skip | N/A |
| `replay` | Automation playback | ❌ Skip | N/A |

**Critical:** Replay sets `actor="replay"` so recorders don't re-ingest replayed events.

**Note on presets:** Preset loads create discontinuities (many params change at once). During replay, use snapshots to restore state at a point in time rather than replaying preset events directly.

---

## Rate Limiting

| Source | Max Rate | Rationale |
|--------|----------|-----------|
| UI parameter changes | 60 Hz per path | Clamp drag events |
| Mod bus values | 30 Hz | Visual refresh rate |
| Audio levels | 30 Hz | Visual refresh rate |
| Events (note_on, etc.) | Immediate | Sparse, latency-sensitive |

```python
class RateLimiter:
    def __init__(self, max_hz: float = 60):
        self.min_interval = 1.0 / max_hz
        self.last_publish = {}
    
    def should_publish(self, path: str) -> bool:
        now = time.monotonic()  # NTP-safe
        last = self.last_publish.get(path, 0)
        if now - last >= self.min_interval:
            self.last_publish[path] = now
            return True
        return False
```

---

## Producer: Integr8tor Class

```python
from confluent_kafka import Producer
import msgpack
import time
import uuid

class Integr8tor:
    def __init__(self, bootstrap_servers='localhost:19092', producer_id='python.gui',
                 session_id: str = None):
        self.producer = Producer({
            'bootstrap.servers': bootstrap_servers,
            'linger.ms': 5,
            'batch.size': 16384,
            'compression.type': 'lz4',
            'enable.idempotence': True,
            'acks': 'all',
        })
        self.session_id = session_id or str(uuid.uuid4())
        self.producer_id = producer_id
        self.seq = 0
        self.rate_limiter = RateLimiter(max_hz=60)
    
    def set_session(self, session_id: str):
        """Set session ID for recording boundaries. Resets seq counter."""
        self.session_id = session_id
        self.seq = 0
    
    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq
    
    def _on_delivery(self, err, msg):
        if err:
            print(f"[Integr8tor] Delivery failed for {msg.key()}: {err}")
    
    def _envelope(self, path: str, value: float, actor: str = 'user', 
                  value_mapped: float = None) -> bytes:
        return msgpack.packb({
            'v': 1,
            'session_id': self.session_id,
            'producer_id': self.producer_id,
            'seq': self._next_seq(),
            'ts_ms': int(time.time() * 1000),
            'path': path,
            'value': value,
            'value_mapped': value_mapped,
            'actor': actor,
            'source': 'python',
        }, use_bin_type=True)
    
    def publish_param_path(self, path: str, value: float, 
                           actor: str = 'user', value_mapped: float = None):
        """Publish any parameter by full path. Use for replay and non-generator params."""
        # Bypass rate limiter for replay/preset (must apply all values faithfully)
        if actor not in ('replay', 'preset') and not self.rate_limiter.should_publish(path):
            return
        
        self.producer.produce(
            'noise.params',
            self._envelope(path, value, actor, value_mapped),
            key=path.encode(),
            on_delivery=self._on_delivery
        )
        self.producer.poll(0)
    
    def publish_param(self, slot: int, param: str, value: float, 
                      actor: str = 'user', value_mapped: float = None):
        """Publish generator parameter. Builds path as gen.{slot}.{param}."""
        path = f'gen.{slot}.{param}'
        self.publish_param_path(path, value, actor, value_mapped)  # Serve callbacks
    
    def publish_mod(self, bus: int, value: float, source_type: str = 'lfo'):
        path = f'bus.{bus}'
        msg = msgpack.packb({
            'v': 1,
            'session_id': self.session_id,
            'producer_id': self.producer_id,
            'seq': self._next_seq(),
            'ts_ms': int(time.time() * 1000),
            'path': path,
            'bus': bus,
            'value': value,
            'source_type': source_type,
            'actor': 'mod',
            'source': 'python',
        }, use_bin_type=True)
        self.producer.produce(
            'noise.mod',
            msg,
            key=path.encode(),
            on_delivery=self._on_delivery
        )
        self.producer.poll(0)
    
    def publish_level(self, source: str, peak: float, rms: float = None):
        msg = msgpack.packb({
            'v': 1,
            'session_id': self.session_id,
            'producer_id': self.producer_id,
            'seq': self._next_seq(),
            'ts_ms': int(time.time() * 1000),
            'path': source,
            'peak': peak,
            'rms': rms,
            'actor': 'telemetry',
            'source': 'python',
        }, use_bin_type=True)
        self.producer.produce(
            'noise.audio',
            msg,
            key=source.encode(),
            on_delivery=self._on_delivery
        )
        self.producer.poll(0)
    
    def publish_event(self, event_type: str, data: dict, actor: str = 'user'):
        msg = msgpack.packb({
            'v': 1,
            'session_id': self.session_id,
            'producer_id': self.producer_id,
            'seq': self._next_seq(),
            'ts_ms': int(time.time() * 1000),
            'type': event_type,
            'actor': actor,
            'source': 'python',
            **data,
        }, use_bin_type=True)
        self.producer.produce(
            'noise.events',
            msg,
            key=event_type.encode(),
            on_delivery=self._on_delivery
        )
        self.producer.poll(0)
    
    def publish_state(self, key: str, state: dict):
        msg = msgpack.packb({
            'v': 1,
            'session_id': self.session_id,
            'producer_id': self.producer_id,
            'seq': self._next_seq(),
            'ts_ms': int(time.time() * 1000),
            'actor': 'preset',
            'source': 'python',
            'key': key,
            'state': state,
        }, use_bin_type=True)
        self.producer.produce(
            'noise.state',
            msg,
            key=key.encode(),
            on_delivery=self._on_delivery
        )
        self.producer.poll(0)
    
    def flush(self):
        self.producer.flush()
```

---

## Consumer: Idempotent Pattern

```python
from confluent_kafka import Consumer
from collections import OrderedDict
import msgpack

class IdempotentConsumer:
    def __init__(self, group_id: str, topics: list, 
                 bootstrap_servers='localhost:19092',
                 auto_offset_reset='latest'):
        """
        Args:
            auto_offset_reset: 'latest' for visuals (realtime), 
                               'earliest' for recorder/debug (replay from start)
        """
        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': auto_offset_reset,
        })
        self.consumer.subscribe(topics)
        self.seen = OrderedDict()  # (session_id, producer_id, seq) -> True
        self.max_seen = 50000
    
    def _is_new(self, data: dict) -> bool:
        key = (data['session_id'], data.get('producer_id', '?'), data['seq'])
        if key in self.seen:
            return False
        
        self.seen[key] = True
        
        # LRU pruning: remove oldest entries by insertion order
        while len(self.seen) > self.max_seen:
            self.seen.popitem(last=False)
        
        return True
    
    def poll_new(self, timeout: float = 0.01):
        """Poll and return message only if not a duplicate."""
        msg = self.consumer.poll(timeout)
        if msg is None or msg.error():
            return None
        
        data = msgpack.unpackb(msg.value(), raw=False)
        if not self._is_new(data):
            return None  # Duplicate
        
        return {
            'topic': msg.topic(),
            'key': msg.key().decode() if msg.key() else None,
            'data': data,
        }
    
    def drain(self):
        """Drain all pending messages, return list of new ones."""
        messages = []
        while True:
            msg = self.consumer.poll(0)
            if msg is None:
                break
            if msg.error():
                continue
            data = msgpack.unpackb(msg.value(), raw=False)
            if not self._is_new(data):
                continue
            messages.append({
                'topic': msg.topic(),
                'key': msg.key().decode() if msg.key() else None,
                'data': data,
            })
        return messages
```

---

## Session Recorder (Streams to Disk)

```python
import msgpack

class SessionRecorder:
    def __init__(self, bootstrap_servers='localhost:19092', 
                 auto_offset_reset='latest'):
        """
        Args:
            auto_offset_reset: 'latest' for live recording,
                               'earliest' to capture from topic start
        """
        self.consumer = IdempotentConsumer(
            group_id=f'recorder-{uuid.uuid4()}',
            topics=['noise.params', 'noise.events', 'noise.mod'],
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset=auto_offset_reset
        )
        self.current_state = {}
        self.snapshot_interval_ms = 5000
        self.last_snapshot_ms = 0
    
    def record(self, output_path: str, duration_seconds: float):
        start = time.time()
        
        with open(output_path, 'wb') as f:
            packer = msgpack.Packer(use_bin_type=True)
            
            while time.time() - start < duration_seconds:
                msg = self.consumer.poll_new(timeout=0.01)
                if msg is None:
                    continue
                
                data = msg['data']
                
                # Skip replay and telemetry (prevent feedback, exclude meters)
                if data.get('actor') in ('replay', 'telemetry'):
                    continue
                
                # Write event
                f.write(packer.pack({
                    'type': 'event',
                    'topic': msg['topic'],
                    'key': msg['key'],
                    'data': data,
                }))
                
                # Track state for snapshots (normalized values only)
                if msg['topic'] == 'noise.params':
                    self.current_state[data['path']] = data['value']
                
                # Periodic snapshot for scrubbing
                ts_ms = data.get('ts_ms', 0)
                if ts_ms - self.last_snapshot_ms > self.snapshot_interval_ms:
                    f.write(packer.pack({
                        'type': 'snapshot',
                        'ts_ms': ts_ms,
                        'state': dict(self.current_state),
                    }))
                    self.last_snapshot_ms = ts_ms
        
        print(f"[Integr8tor] Recorded {duration_seconds}s to {output_path}")
    
    @staticmethod
    def load(path: str) -> tuple[list, list]:
        events = []
        snapshots = []
        
        with open(path, 'rb') as f:
            unpacker = msgpack.Unpacker(f, raw=False)
            for item in unpacker:
                if item['type'] == 'snapshot':
                    snapshots.append(item)
                else:
                    events.append(item)
        
        return events, snapshots
```

---

## Session Player (With User Pinning)

```python
class SessionPlayer:
    def __init__(self, integr8tor: Integr8tor):
        self.integr8tor = integr8tor
        self.pinned_paths = {}  # path -> pin_until_ts
        self.pin_duration_ms = 3000  # User override lasts 3s
        self.playing = False
    
    def user_touched(self, path: str):
        """Call when user manually adjusts a parameter during playback."""
        self.pinned_paths[path] = time.monotonic() * 1000 + self.pin_duration_ms
    
    def _is_pinned(self, path: str) -> bool:
        if path not in self.pinned_paths:
            return False
        if time.monotonic() * 1000 > self.pinned_paths[path]:
            del self.pinned_paths[path]
            return False
        return True
    
    def stop(self):
        self.playing = False
    
    def play(self, recording_path: str, speed: float = 1.0):
        events, snapshots = SessionRecorder.load(recording_path)
        
        if not events:
            print("[Integr8tor] No events to play")
            return
        
        self.playing = True
        self.pinned_paths.clear()
        
        base_ts = events[0]['data']['ts_ms']
        start = time.monotonic() * 1000
        
        for event in events:
            if not self.playing:
                break
            
            data = event['data']
            path = data.get('path')
            
            # Skip if user has pinned this path
            if path and self._is_pinned(path):
                continue
            
            # Wait for correct relative time
            target_offset = (data['ts_ms'] - base_ts) / speed
            while self.playing and (time.monotonic() * 1000 - start) < target_offset:
                time.sleep(0.001)
            
            if not self.playing:
                break
            
            # Republish with actor='replay'
            if event['topic'] == 'noise.params':
                self.integr8tor.publish_param_path(
                    path=data['path'],
                    value=data['value'],
                    actor='replay'
                )
        
        self.playing = False
        self.integr8tor.flush()  # Ensure all events delivered
        print("[Integr8tor] Playback complete")
    
    def scrub_to(self, recording_path: str, ts_ms: int):
        """Jump to a point in time using nearest snapshot."""
        events, snapshots = SessionRecorder.load(recording_path)
        
        # Find nearest snapshot before target time
        nearest = None
        for snap in snapshots:
            if snap['ts_ms'] <= ts_ms:
                nearest = snap
            else:
                break
        
        if nearest:
            # Apply snapshot state
            for path, value in nearest['state'].items():
                self.integr8tor.publish_param_path(path, value, actor='replay')
            self.integr8tor.flush()  # Ensure all events delivered
```

---

## Infrastructure

### Docker Compose (Redpanda - Recommended)

```yaml
version: '3'
services:
  redpanda:
    image: redpandadata/redpanda:latest
    command:
      - redpanda start
      - --smp 1
      - --memory 512M
      - --overprovisioned
      - --node-id 0
      - --kafka-addr internal://0.0.0.0:9092,external://0.0.0.0:19092
      - --advertise-kafka-addr internal://redpanda:9092,external://localhost:19092
    ports:
      - "19092:19092"   # Host access
      - "9644:9644"     # Admin API
    volumes:
      - redpanda-data:/var/lib/redpanda/data

  console:
    image: redpandadata/console:latest
    ports:
      - "8080:8080"
    environment:
      KAFKA_BROKERS: redpanda:9092  # Internal listener
    depends_on:
      - redpanda

volumes:
  redpanda-data:
```

**Listeners:**
- Host applications: `localhost:19092`
- Container applications: `redpanda:9092`

### Topic Creation

```bash
#!/bin/bash
# create-topics.sh

rpk topic create noise.params \
  --partitions 4 \
  -c retention.ms=3600000

rpk topic create noise.mod \
  --partitions 1 \
  -c retention.ms=60000

rpk topic create noise.audio \
  --partitions 1 \
  -c retention.ms=60000

rpk topic create noise.events \
  --partitions 1 \
  -c retention.ms=86400000

rpk topic create noise.state \
  --partitions 1 \
  -c cleanup.policy=compact \
  -c min.cleanable.dirty.ratio=0.1
```

---

## Integration: Dual Publisher

```python
class DualPublisher:
    """Publishes to both OSC (for SC) and Integr8tor (for ecosystem)."""
    
    def __init__(self, osc_bridge, integr8tor: Integr8tor):
        self.osc = osc_bridge
        self.integr8tor = integr8tor
    
    def set_param(self, slot: int, param: str, value: float,
                  actor: str = 'user', value_mapped: float = None):
        # OSC for SC (low latency)
        self.osc.send(f'/noise/gen/{slot}/{param}', value)
        
        # Kafka for ecosystem
        self.integr8tor.publish_param(slot, param, value, actor, value_mapped)
    
    def set_mod_param(self, slot: int, param: str, value: float):
        self.osc.send(f'/noise/mod/{slot}/{param}', value)
        # Mod params don't need Kafka - mod bus values are published separately
    
    def set_master_param(self, param: str, value: float):
        self.osc.send(f'/noise/master/{param}', value)
        self.integr8tor.publish_param_path(f'master.{param}', value)
```

---

## Session Management

A `session_id` groups all events from a recording/performance. For multi-producer setups (GUI + SC bridge), all producers must share the same session.

### Recording Boundaries

```python
import uuid

# When recording starts, generate shared session
shared_session = str(uuid.uuid4())

# Set on all producers
gui_integr8tor.set_session(shared_session)
sc_bridge_integr8tor.set_session(shared_session)

# Now all events share session_id, enabling unified replay
```

### Single Producer (Default)

If only one producer exists, `session_id` auto-generates on init. No action needed.

---

## Consumer Examples

### TouchDesigner (Visual Layer)

```python
from confluent_kafka import Consumer
import msgpack

consumer = Consumer({
    'bootstrap.servers': 'localhost:19092',
    'group.id': 'touchdesigner-visual',
    'auto.offset.reset': 'latest',
})
consumer.subscribe(['noise.params', 'noise.mod', 'noise.audio'])

def update():
    """Call from TouchDesigner's execute DAT at 30-60fps."""
    while True:
        msg = consumer.poll(0)
        if msg is None:
            break
        if msg.error():
            continue
        
        data = msgpack.unpackb(msg.value(), raw=False)
        key = msg.key().decode()
        
        # Exact match for specific parameter
        if key == 'gen.1.cutoff':
            op('filter_intensity').par.value0 = data['value']
        
        # Prefix match for all params from a generator
        elif key.startswith('gen.2.'):
            param = key.split('.')[-1]
            op(f'gen2_{param}').par.value0 = data['value']
        
        # Mod bus values for visual animation
        elif key.startswith('bus.'):
            bus_num = int(key.split('.')[1])
            op('mod_visual').par[f'bus{bus_num}'] = data['value']
```

**Key matching rules:**
- Use exact match (`key == 'gen.1.cutoff'`) for specific parameters
- Use prefix match (`key.startswith('gen.1.')`) for groups
- Never use substring match (`'cutoff' in key`) - catches `cutoff_env`, `filter_cutoff_lfo`, etc.

### Resolume / VDMX (via OSC Bridge)

```python
from pythonosc import udp_client

osc_client = udp_client.SimpleUDPClient("127.0.0.1", 7000)  # Resolume OSC port

for msg in consumer.drain():
    key = msg['key']
    value = msg['data']['value']
    
    # Forward to Resolume as OSC
    osc_path = f"/noise/{key.replace('.', '/')}"
    osc_client.send_message(osc_path, value)
```

### Max/MSP (via udpreceive)

```python
# Python bridge sends to Max's udpreceive
osc_client = udp_client.SimpleUDPClient("127.0.0.1", 9000)

for msg in consumer.drain():
    if msg['topic'] == 'noise.mod':
        # Send mod bus values as list for Max's multislider
        osc_client.send_message("/noise/mod/buses", [msg['data']['value']])
```

---

## Phase 0: Prove Value with SQLite (Optional)

Before any streaming infrastructure, prove recording/replay works:

```python
import sqlite3
import time

class SimpleRecorder:
    def __init__(self, db_path='session.db'):
        self.db = sqlite3.connect(db_path)
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS params (
                ts_ms INTEGER,
                path TEXT,
                value REAL,
                actor TEXT
            )
        ''')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_ts ON params(ts_ms)')
    
    def log(self, path: str, value: float, actor: str = 'user'):
        self.db.execute(
            'INSERT INTO params VALUES (?, ?, ?, ?)',
            (int(time.time() * 1000), path, value, actor)
        )
        self.db.commit()
    
    def replay(self, speed: float = 1.0):
        cursor = self.db.execute('SELECT * FROM params ORDER BY ts_ms')
        rows = cursor.fetchall()
        
        if not rows:
            return
        
        base_ts = rows[0][0]
        start = time.monotonic() * 1000
        
        for ts_ms, path, value, actor in rows:
            target = (ts_ms - base_ts) / speed
            while (time.monotonic() * 1000 - start) < target:
                time.sleep(0.001)
            
            print(f"Replay: {path} = {value}")
            # Send to OSC here
```

---

## Implementation Phases

| Phase | Scope | Sessions |
|-------|-------|----------|
| 0 | SQLite recorder (prove value, zero infra) | 0.5 |
| A | Docker + Redpanda + basic produce/consume | 1 |
| B | `Integr8tor` class integrated into Noise Engine | 1-2 |
| C | SC bridge (levels + mod buses @ 30fps) | 1 |
| D | Session recorder + player with scrubbing | 1 |
| E | TouchDesigner consumer template | 1-2 |
| F | Schema registry + Avro (optional) | 1 |

---

## Latency Budget

| Path | Latency | Use For |
|------|---------|---------|
| Python → OSC → SC | 0.5-2ms | Audio control ✅ |
| Python → Kafka → Consumer | 5-20ms | Visuals ✅ Recording ✅ |
| Python → Kafka → Bridge → SC | 10-30ms | Non-audio sync only |

**Rule:** OSC for audio. Integr8tor for everything else.

---

## Dependencies

```
# requirements.txt
confluent-kafka>=2.3.0
msgpack>=1.0.0

# Optional
fastavro>=1.9.0  # For Avro schemas later
```

### Msgpack Settings (Critical)

Always use these flags to avoid bytes/string confusion:

```python
# Packing - ensures strings stay as strings
msgpack.packb(data, use_bin_type=True)

# Unpacking - returns str not bytes for string fields  
msgpack.unpackb(raw_bytes, raw=False)
```

Without `raw=False`, dict keys come back as `b'session_id'` instead of `'session_id'`.

### Timestamp Strategy

The code uses two different time sources intentionally:

| Context | Time Source | Reason |
|---------|-------------|--------|
| Message `ts_ms` field | `time.time()` | Wall-clock for "when did this happen" (recordings need real timestamps) |
| Replay/pin scheduling | `time.monotonic()` | NTP-safe for "how long has elapsed" (immune to clock jumps) |

This split is correct: recordings store wall-clock, playback uses monotonic intervals.

---

## Files

```
src/integr8tor/
├── __init__.py
├── integr8tor.py       # Main producer class
├── consumer.py         # IdempotentConsumer
├── recorder.py         # SessionRecorder
├── player.py           # SessionPlayer
├── dual_publisher.py   # OSC + Kafka wrapper
└── simple_recorder.py  # SQLite Phase 0

docker/
├── docker-compose.yml
└── create-topics.sh
```
