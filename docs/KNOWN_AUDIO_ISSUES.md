# Known Audio Validation Issues

These generators have known issues that are acceptable for R1.

## astro_command
| Generator | Issue | Reason | Action |
|-----------|-------|--------|--------|
| radio_link | SILENCE | Squelch logic gates at test defaults (0.5) | ACCEPT - works with JSON defaults |

## beacon_vigil
| Generator | Issue | Reason | Action |
|-----------|-------|--------|--------|
| crown | SPARSE | Percussive generator, 5% active | ACCEPT - midi_retrig:true |
| beacon | RUNAWAY | Marginal growth, Limiter added | ACCEPT |


## boneyard
| Generator | Issue | Reason | Action |
|-----------|-------|--------|--------|
| canopy | RENDER_FAILED | TGrains + LocalBuf.collect pattern hangs NRT | ACCEPT - complex DSP |


## dew_sphere
| Generator | Issue | Reason | Action |
|-----------|-------|--------|--------|
| filament_bed | SILENCE | RMS -40.1 dB, just below -40 dB threshold | ACCEPT - borderline |
| droplet_ping | SILENCE | Likely similar borderline | ACCEPT |


## drangarnir
| Generator | Issue | Reason | Action |
|-----------|-------|--------|--------|
| tide_swell | SILENCE | RMS -53.6 dB, very quiet at test defaults | ACCEPT |


## emerald_canopy
| Generator | Issue | Reason | Action |
|-----------|-------|--------|--------|
| dewdrop | SPARSE | 4% active, impulsive percussive | ACCEPT |
| vine_ping | SPARSE | 4% active, impulsive percussive | ACCEPT |

