#!/usr/bin/env python3
"""
SauceOfGrav v1.4.3 Simulation and MP4 Renderer
Based on SAUCE_OF_GRAV_SPEC_v1_4_3.md
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from dataclasses import dataclass, field
from typing import List
import warnings
warnings.filterwarnings('ignore')

# === CONFIG CONSTANTS (v1.4.3) ===

# Rate ranges
SAUCE_FREE_RATE_MIN = 0.001
SAUCE_FREE_RATE_MAX = 100.0
SAUCE_RATE_DEADBAND = 0.05

# Noise / thresholds
SAUCE_NOISE_RATE = 0.012
SAUCE_VELOCITY_EPSILON = 0.001

# Mass mapping
MASS_BASE = 0.25
MASS_GAIN = 2.1

# Coupling
HUB_COUPLE_BASE = 0.0
HUB_COUPLE_GAIN = 6.0
HUB_TENSION_EXP = 0.70
RING_COUPLE_BASE = 0.0
RING_COUPLE_GAIN = 3.5
RING_TENSION_EXP = 1.30

# Non-reciprocal ring
RING_SKEW = 0.015

# Gravity stiffness
GRAV_STIFF_BASE = 0.0
GRAV_STIFF_GAIN = 6.0

# Excursion
EXCURSION_MIN = 0.60
EXCURSION_MAX = 1.60

# CALM macro (v1.4.3)
CALM_DAMP_CALM = 1.30
CALM_DAMP_WILD = 0.75
CALM_VDP_CALM = 0.90
CALM_VDP_WILD = 1.15
CALM_KICK_CALM = 0.60

# Van der Pol
VDP_INJECT = 0.8
VDP_THRESHOLD = 0.35
VDP_HUB_MOD = 0.05
VDP_THRESHOLD_FLOOR = 0.05

# Calibration trims
TENSION_TRIM = [+0.012, -0.008, +0.015, -0.018]
MASS_TRIM = [-0.010, +0.014, -0.006, +0.011]

# Damping
SAUCE_DAMPING_BASE = 0.10
SAUCE_DAMPING_TENSION = 0.40

# Rails
SAUCE_RAIL_ZONE = 0.08
SAUCE_RAIL_ABSORB = 0.35

# Resonance
RESO_FLOOR_MIN = 0.0002
RESO_FLOOR_MAX = 0.0040
RESO_DRIVE_GAIN = 6.0
RESO_DELTAE_MAX = 0.01
RESO_RAIL_EXP = 1.4

# Kickstart
RESO_KICK_GAIN = 2.8
RESO_KICK_MAXF = 0.30
RESO_KICK_COOLDOWN_S = 0.20
KICK_PATTERNS = [
    [+1, -1, +1, -1],
    [+1, +1, -1, -1],
    [+1, -1, -1, +1],
]

# Hub dynamics
OVERSHOOT_TO_HUB_GAIN = 0.6
OVERSHOOT_MAX = 0.25
HUB_LIMIT = 2.0
DEPTH_DAMP_MIN = 0.005  # was 0.05
DEPTH_DAMP_MAX = 2.50

# Hub feed
HUB_FEED_GAIN = 8.0  # was 2.2
HUB_FEED_MAX = 0.35


def lerp(a, b, t):
    return a + (b - a) * t


def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    return 0


@dataclass
class SauceOfGravState:
    """Full simulation state"""
    # Outputs
    out: np.ndarray = field(default_factory=lambda: np.full(4, 0.5))
    vel: np.ndarray = field(default_factory=lambda: np.zeros(4))
    prev_side: np.ndarray = field(default_factory=lambda: np.zeros(4, dtype=int))
    overshoot_active: np.ndarray = field(default_factory=lambda: np.zeros(4, dtype=bool))
    overshoot_target: np.ndarray = field(default_factory=lambda: np.full(4, 0.5))
    overshoot_peak: np.ndarray = field(default_factory=lambda: np.zeros(4))
    
    # Hub
    hub_bias: float = 0.0
    hub_vel: float = 0.0
    
    # Kickstart
    kick_toggle: int = 1
    kick_index: int = 0
    kick_cooldown: float = 0.0


class SauceOfGravSim:
    def __init__(self, dt=1/400):
        self.dt = dt
        self.state = SauceOfGravState()
        
        # Parameters (normalized 0-1, except calm which is -1 to +1)
        self.gravity_norm = 0.5
        self.depth_norm = 0.5
        self.resonance_norm = 0.6
        self.excursion_norm = 0.6
        self.calm_bi = 0.0  # bipolar -1..+1
        self.tension_norm = np.full(4, 0.5)
        self.mass_norm = np.full(4, 0.5)
        
        # Ring topology
        self.prev_idx = [3, 0, 1, 2]  # prev(i)
        self.next_idx = [1, 2, 3, 0]  # next(i)
        
    def step(self):
        s = self.state
        dt = self.dt
        
        # === Step 2: Compute CALM multipliers ===
        if self.calm_bi < 0:
            calm_damp_mul = lerp(1.0, CALM_DAMP_CALM, -self.calm_bi)
            calm_vdp_mul = lerp(1.0, CALM_VDP_CALM, -self.calm_bi)
            calm_kick_mul = lerp(1.0, CALM_KICK_CALM, -self.calm_bi)
        else:
            calm_damp_mul = lerp(1.0, CALM_DAMP_WILD, self.calm_bi)
            calm_vdp_mul = lerp(1.0, CALM_VDP_WILD, self.calm_bi)
            calm_kick_mul = 1.0
        
        # === Step 3: Compute mappings ===
        gravity_influence = 1.0 - self.gravity_norm
        excursion_gain = EXCURSION_MIN + self.excursion_norm * (EXCURSION_MAX - EXCURSION_MIN)
        hub_target_raw = 0.5 + s.hub_bias * gravity_influence * excursion_gain
        hub_target = np.clip(hub_target_raw, 0, 1)
        
        k_grav = GRAV_STIFF_BASE + GRAV_STIFF_GAIN * self.gravity_norm
        
        # Per-output mappings with trims
        mass_eff = np.clip(self.mass_norm + np.array(MASS_TRIM), 0, 1)
        m = MASS_BASE + MASS_GAIN * mass_eff
        
        tension_eff = np.clip(self.tension_norm + np.array(TENSION_TRIM), 0, 1)
        k_hub = HUB_COUPLE_BASE + HUB_COUPLE_GAIN * (tension_eff ** HUB_TENSION_EXP)
        k_ring = RING_COUPLE_BASE + RING_COUPLE_GAIN * (tension_eff ** RING_TENSION_EXP)
        k_ring_fwd = k_ring * (1 + RING_SKEW)
        k_ring_bwd = k_ring * (1 - RING_SKEW)
        
        damping_base = (SAUCE_DAMPING_BASE + SAUCE_DAMPING_TENSION * (1 - tension_eff)) * calm_damp_mul
        
        HUB_DAMP = DEPTH_DAMP_MIN + self.depth_norm * (DEPTH_DAMP_MAX - DEPTH_DAMP_MIN)
        
        # === Step 4: Van der Pol effective damping ===
        hub_bias_norm = s.hub_bias / HUB_LIMIT
        vdp_threshold = VDP_THRESHOLD * (1 + VDP_HUB_MOD * hub_bias_norm)
        vdp_threshold = max(vdp_threshold, VDP_THRESHOLD_FLOOR)
        
        amp = np.abs(s.out - 0.5)
        vdp_factor = (VDP_INJECT * calm_vdp_mul) * (1 - (amp / vdp_threshold) ** 2)
        damping_effective = damping_base - vdp_factor
        
        # === Step 5: Inject velocity noise ===
        s.vel += np.random.normal(0, SAUCE_NOISE_RATE, 4) * np.sqrt(dt)
        
        # === Step 6: Compute forces ===
        F_grav = k_grav * (0.5 - s.out)
        F_hub = k_hub * (hub_target - s.out)
        
        # Non-reciprocal ring
        F_ring = np.zeros(4)
        for i in range(4):
            F_ring[i] = (k_ring_fwd[i] * (s.out[self.next_idx[i]] - s.out[i]) +
                        k_ring_bwd[i] * (s.out[self.prev_idx[i]] - s.out[i]))
        
        # === Step 7: Resonance ===
        moving = np.abs(s.vel) >= SAUCE_VELOCITY_EPSILON
        moving_count = np.sum(moving)
        
        E = 0.5 * np.sum(m * s.vel ** 2)
        E_floor = RESO_FLOOR_MIN + self.resonance_norm * (RESO_FLOOR_MAX - RESO_FLOOR_MIN)
        
        F_reso = np.zeros(4)
        alignment_factor = 0.0
        
        if moving_count > 0:
            vel_signs = np.sign(s.vel[moving])
            if len(vel_signs) > 0:
                alignment_factor = abs(np.sum(vel_signs)) / moving_count
        
        if alignment_factor > 0 and E < E_floor:
            drive_dir = sign(np.sum(s.vel[moving]))
            delta_E = np.clip(E_floor - E, 0, RESO_DELTAE_MAX)
            
            for i in range(4):
                if moving[i] and sign(s.vel[i]) == drive_dir:
                    F_reso[i] = drive_dir * alignment_factor * self.resonance_norm * RESO_DRIVE_GAIN * delta_E
                    rail_attn = (1 - abs(2 * s.out[i] - 1)) ** RESO_RAIL_EXP
                    F_reso[i] *= rail_attn
        
        # === Step 8: Kickstart ===
        s.kick_cooldown = max(0, s.kick_cooldown - dt)
        F_kick = np.zeros(4)
        
        if (self.resonance_norm > 0 and E < E_floor and 
            (moving_count == 0 or alignment_factor == 0) and 
            s.kick_cooldown == 0):
            
            kick_mag = np.clip(RESO_KICK_GAIN * (E_floor - E), 0, RESO_KICK_MAXF) * calm_kick_mul
            pattern = KICK_PATTERNS[s.kick_index]
            F_kick = np.array([s.kick_toggle * pattern[i] * kick_mag for i in range(4)])
            
            s.kick_toggle *= -1
            s.kick_index = (s.kick_index + 1) % 3
            s.kick_cooldown = RESO_KICK_COOLDOWN_S
        
        # === Step 9: Apply acceleration ===
        F_total = F_grav + F_hub + F_ring + F_reso + F_kick
        accel = F_total / m
        s.vel += accel * dt
        
        # === Step 10: Apply damping ===
        s.vel *= np.exp(-damping_effective * dt)
        
        # === Step 11: Integrate position ===
        s.out += s.vel * dt
        
        # === Step 12: Rail bumpers ===
        s.out = np.clip(s.out, 0, 1)
        d = np.minimum(s.out, 1 - s.out)
        u = np.clip((SAUCE_RAIL_ZONE - d) / SAUCE_RAIL_ZONE, 0, 1)
        s.vel *= (1 - SAUCE_RAIL_ABSORB * u ** 2)
        
        # === Step 13: Overshoot detection ===
        overshoot_impulses = np.zeros(4)
        
        for i in range(4):
            side_val = s.out[i] - hub_target
            side = sign(side_val)
            
            # Crossing check: (side != 0) AND (prev_side != 0) AND (side != prev_side)
            crossing = (side != 0 and s.prev_side[i] != 0 and side != s.prev_side[i] and
                       abs(s.vel[i]) >= SAUCE_VELOCITY_EPSILON)
            
            if crossing and not s.overshoot_active[i]:
                s.overshoot_target[i] = hub_target
                s.overshoot_active[i] = True
                s.overshoot_peak[i] = 0
            
            if s.overshoot_active[i]:
                e = s.out[i] - s.overshoot_target[i]
                if abs(e) > abs(s.overshoot_peak[i]):
                    s.overshoot_peak[i] = e
                
                # Completion on velocity sign flip
                if sign(s.vel[i]) != sign(s.overshoot_peak[i]) or abs(s.vel[i]) < SAUCE_VELOCITY_EPSILON:
                    overshoot_impulses[i] = np.clip(s.overshoot_peak[i], -OVERSHOOT_MAX, OVERSHOOT_MAX)
                    s.overshoot_active[i] = False
                    s.overshoot_peak[i] = 0
            
            # Update prev_side
            if side != 0:
                s.prev_side[i] = side
        
        # === Step 14: Hub update ===
        hub_impulse = OVERSHOOT_TO_HUB_GAIN * np.sum(overshoot_impulses)
        
        e_hub = s.out - hub_target
        work_sum = np.sum(e_hub * s.vel)
        hub_feed = np.clip(HUB_FEED_GAIN * work_sum, -HUB_FEED_MAX, HUB_FEED_MAX)
        
        s.hub_vel += (hub_impulse + hub_feed) * dt
        s.hub_vel *= np.exp(-HUB_DAMP * dt)
        s.hub_bias += s.hub_vel * dt
        s.hub_bias = HUB_LIMIT * np.tanh(s.hub_bias / HUB_LIMIT)
        
        # === Safety: NaN/Inf check ===
        for i in range(4):
            if not np.isfinite(s.out[i]) or not np.isfinite(s.vel[i]):
                s.out[i] = 0.5
                s.vel[i] = 0.0
        
        if not np.isfinite(s.hub_bias) or not np.isfinite(s.hub_vel):
            s.hub_bias = 0.0
            s.hub_vel = 0.0
        
        return s.out.copy()


def run_simulation(duration_s=30, dt=1/400):
    """Run simulation and collect output history"""
    sim = SauceOfGravSim(dt=dt)
    
    # Set interesting parameters
    sim.gravity_norm = 0.4
    sim.depth_norm = 0.5
    sim.resonance_norm = 0.65
    sim.excursion_norm = 0.6
    sim.calm_bi = 0.0  # neutral
    sim.tension_norm = np.array([0.55, 0.45, 0.50, 0.60])
    sim.mass_norm = np.array([0.45, 0.55, 0.50, 0.40])
    
    n_steps = int(duration_s / dt)
    history = np.zeros((n_steps, 4))
    hub_history = np.zeros(n_steps)
    
    for step in range(n_steps):
        # Slowly vary CALM from -0.5 to +0.5 over the run
        t = step * dt
        sim.calm_bi = 0.5 * np.sin(2 * np.pi * t / duration_s)
        
        history[step] = sim.step()
        hub_history[step] = sim.state.hub_bias
    
    return history, hub_history, dt


def create_mp4(history, hub_history, dt, filename='sauce_of_grav_v1_4_3.mp4', duration_s=30):
    """Create MP4 animation with single XY plot showing all 4 outputs as persistent orbits"""
    
    n_steps = len(history)
    t = np.arange(n_steps) * dt
    
    # Downsample for animation (target ~30fps video)
    fps = 30
    frame_interval = max(1, int(1 / (fps * dt)))
    frame_indices = np.arange(0, n_steps, frame_interval)
    n_frames = len(frame_indices)
    
    # Create figure
    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor('#1a1a2e')
    
    # Grid: main trace on top, hub in middle, two phase plots on bottom
    gs = fig.add_gridspec(3, 2, height_ratios=[2.5, 0.8, 2.5], hspace=0.35, wspace=0.25,
                          left=0.06, right=0.98, top=0.93, bottom=0.06)
    
    ax_main = fig.add_subplot(gs[0, :])  # full width
    ax_hub = fig.add_subplot(gs[1, :])   # full width
    ax_xy = fig.add_subplot(gs[2, 0])    # XY output phase space (left)
    ax_hub_phase = fig.add_subplot(gs[2, 1])  # Hub phase space (right)
    
    all_axes = [ax_main, ax_hub, ax_xy, ax_hub_phase]
    
    # Compute hub velocity for phase space
    hub_velocity = np.gradient(hub_history, dt)
    
    # Style axes
    for ax in all_axes:
        ax.set_facecolor('#16213e')
        ax.tick_params(colors='white', labelsize=9)
        ax.spines['bottom'].set_color('#444')
        ax.spines['top'].set_color('#444')
        ax.spines['left'].set_color('#444')
        ax.spines['right'].set_color('#444')
    
    # Colors for outputs
    colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3']
    
    # Window size (seconds to show in time plots)
    window_s = 8.0
    window_samples = int(window_s / dt)
    
    # Initialize time-series lines
    lines = []
    for i in range(4):
        line, = ax_main.plot([], [], color=colors[i], linewidth=1.5, label=f'Out {i+1}')
        lines.append(line)
    
    hub_line, = ax_hub.plot([], [], color='#FF00FF', linewidth=2)
    
    # Initialize XY orbit lines - persistent trails for all 4 outputs as 2 pairs
    xy_trail_1_2, = ax_xy.plot([], [], color=colors[0], linewidth=1.0, alpha=0.9, label='Out1 vs Out2')
    xy_trail_3_4, = ax_xy.plot([], [], color=colors[2], linewidth=1.0, alpha=0.9, label='Out3 vs Out4')
    xy_point_1_2, = ax_xy.plot([], [], 'o', color=colors[1], markersize=12, markeredgecolor='white', markeredgewidth=2)
    xy_point_3_4, = ax_xy.plot([], [], 'o', color=colors[3], markersize=12, markeredgecolor='white', markeredgewidth=2)
    
    # Initialize hub phase space lines - persistent trail
    hub_phase_trail, = ax_hub_phase.plot([], [], color='#FF00FF', linewidth=1.0, alpha=0.9)
    hub_phase_point, = ax_hub_phase.plot([], [], 'o', color='#FF00FF', markersize=12, markeredgecolor='white', markeredgewidth=2)
    
    # Setup main axis
    ax_main.set_ylabel('Output Value', color='white', fontsize=11)
    ax_main.set_ylim(-0.05, 1.05)
    ax_main.legend(loc='upper right', facecolor='#1a1a2e', edgecolor='#444', 
                   labelcolor='white', fontsize=9)
    ax_main.axhline(y=0.5, color='#444', linestyle='--', linewidth=0.5)
    ax_main.axhline(y=0.0, color='#333', linestyle='-', linewidth=0.5)
    ax_main.axhline(y=1.0, color='#333', linestyle='-', linewidth=0.5)
    
    # Setup hub axis
    ax_hub.set_ylabel('Hub', color='white', fontsize=11)
    ax_hub.set_xlabel('Time (s)', color='white', fontsize=11)
    # Autoscale hub to actual range with padding
    hub_min, hub_max = hub_history.min(), hub_history.max()
    hub_margin = max(0.1, (hub_max - hub_min) * 0.2)  # At least 0.1, or 20% padding
    ax_hub.set_ylim(hub_min - hub_margin, hub_max + hub_margin)
    ax_hub.axhline(y=0, color='#444', linestyle='--', linewidth=0.5)
    
    # Setup XY axis
    ax_xy.set_xlim(-0.05, 1.05)
    ax_xy.set_ylim(-0.05, 1.05)
    ax_xy.set_xlabel('X (Out1 / Out3)', color='white', fontsize=11)
    ax_xy.set_ylabel('Y (Out2 / Out4)', color='white', fontsize=11)
    ax_xy.set_title('Output Phase Space', color='white', fontsize=12)
    ax_xy.set_aspect('equal')
    ax_xy.axhline(y=0.5, color='#333', linestyle='--', linewidth=0.5)
    ax_xy.axvline(x=0.5, color='#333', linestyle='--', linewidth=0.5)
    ax_xy.grid(True, color='#333', linewidth=0.3, alpha=0.5)
    ax_xy.legend(loc='upper right', facecolor='#1a1a2e', edgecolor='#444', 
                 labelcolor='white', fontsize=9)
    
    # Setup hub phase space axis
    hub_pos_margin = max(0.1, (hub_history.max() - hub_history.min()) * 0.2)
    hub_vel_margin = max(0.5, (hub_velocity.max() - hub_velocity.min()) * 0.2)
    ax_hub_phase.set_xlim(hub_history.min() - hub_pos_margin, hub_history.max() + hub_pos_margin)
    ax_hub_phase.set_ylim(hub_velocity.min() - hub_vel_margin, hub_velocity.max() + hub_vel_margin)
    ax_hub_phase.set_xlabel('Hub Position', color='white', fontsize=11)
    ax_hub_phase.set_ylabel('Hub Velocity', color='white', fontsize=11)
    ax_hub_phase.set_title('Hub Phase Space', color='white', fontsize=12)
    ax_hub_phase.axhline(y=0, color='#333', linestyle='--', linewidth=0.5)
    ax_hub_phase.axvline(x=0, color='#333', linestyle='--', linewidth=0.5)
    ax_hub_phase.grid(True, color='#333', linewidth=0.3, alpha=0.5)
    
    title = fig.suptitle('SauceOfGrav v1.4.3 — CALM sweep (-0.5 → +0.5)', 
                         color='white', fontsize=14, fontweight='bold')
    
    # Stats text
    stats_text = ax_main.text(0.02, 0.98, '', transform=ax_main.transAxes, 
                              color='white', fontsize=9, verticalalignment='top',
                              fontfamily='monospace',
                              bbox=dict(boxstyle='round', facecolor='#1a1a2e', alpha=0.8))
    
    def init():
        for line in lines:
            line.set_data([], [])
        hub_line.set_data([], [])
        xy_trail_1_2.set_data([], [])
        xy_trail_3_4.set_data([], [])
        xy_point_1_2.set_data([], [])
        xy_point_3_4.set_data([], [])
        hub_phase_trail.set_data([], [])
        hub_phase_point.set_data([], [])
        return lines + [hub_line, xy_trail_1_2, xy_trail_3_4, xy_point_1_2, xy_point_3_4, hub_phase_trail, hub_phase_point, stats_text]
    
    def animate(frame):
        idx = frame_indices[frame]
        
        # Calculate window for time series
        start_idx = max(0, idx - window_samples)
        end_idx = idx
        
        if end_idx <= start_idx:
            return lines + [hub_line, xy_trail_1_2, xy_trail_3_4, xy_point_1_2, xy_point_3_4, hub_phase_trail, hub_phase_point, stats_text]
        
        t_window = t[start_idx:end_idx]
        
        # Update x limits for time plots
        ax_main.set_xlim(t_window[0], t_window[0] + window_s)
        ax_hub.set_xlim(t_window[0], t_window[0] + window_s)
        
        # Update output lines
        for i, line in enumerate(lines):
            line.set_data(t_window, history[start_idx:end_idx, i])
        
        # Update hub line
        hub_line.set_data(t_window, hub_history[start_idx:end_idx])
        
        # Update XY orbits - persistent from start to now
        xy_trail_1_2.set_data(history[0:idx, 0], history[0:idx, 1])
        xy_trail_3_4.set_data(history[0:idx, 2], history[0:idx, 3])
        
        # Current points
        xy_point_1_2.set_data([history[idx-1, 0]], [history[idx-1, 1]])
        xy_point_3_4.set_data([history[idx-1, 2]], [history[idx-1, 3]])
        
        # Update hub phase space - persistent from start to now
        hub_phase_trail.set_data(hub_history[0:idx], hub_velocity[0:idx])
        hub_phase_point.set_data([hub_history[idx-1]], [hub_velocity[idx-1]])
        
        # Calculate current stats
        current_t = t[idx]
        calm_val = 0.5 * np.sin(2 * np.pi * current_t / duration_s)
        
        # Range stats (over recent window)
        recent = history[max(0, idx-int(2/dt)):idx]
        if len(recent) > 10:
            ranges = np.ptp(recent, axis=0)
            correlations = []
            for i in range(4):
                for j in range(i+1, 4):
                    if np.std(recent[:, i]) > 0.001 and np.std(recent[:, j]) > 0.001:
                        corr = np.corrcoef(recent[:, i], recent[:, j])[0, 1]
                        if np.isfinite(corr):
                            correlations.append(abs(corr))
            avg_corr = np.mean(correlations) if correlations else 0
        else:
            ranges = np.zeros(4)
            avg_corr = 0
        
        stats_str = (f'Time: {current_t:.1f}s  CALM: {calm_val:+.2f}\n'
                    f'Ranges: {ranges[0]:.2f} {ranges[1]:.2f} {ranges[2]:.2f} {ranges[3]:.2f}\n'
                    f'Avg |corr|: {avg_corr:.2f}  Hub: {hub_history[idx]:.3f}')
        stats_text.set_text(stats_str)
        
        return lines + [hub_line, xy_trail_1_2, xy_trail_3_4, xy_point_1_2, xy_point_3_4, hub_phase_trail, hub_phase_point, stats_text]
    
    print(f"Creating animation with {n_frames} frames...")
    anim = animation.FuncAnimation(fig, animate, init_func=init,
                                   frames=n_frames, interval=1000/fps, blit=True)
    
    print(f"Saving to {filename}...")
    writer = animation.FFMpegWriter(fps=fps, bitrate=3000)
    anim.save(filename, writer=writer, dpi=100)
    plt.close()
    print("Done!")
    
    return filename


def compute_stats(history, dt):
    """Compute summary statistics"""
    print("\n=== SauceOfGrav v1.4.3 Simulation Stats ===\n")
    
    # Skip first 2 seconds (transient)
    skip = int(2 / dt)
    data = history[skip:]
    
    # Range (p95 - p05)
    print("Output ranges (p95 - p05):")
    for i in range(4):
        p95 = np.percentile(data[:, i], 95)
        p05 = np.percentile(data[:, i], 5)
        print(f"  out{i+1}: {p95-p05:.3f}  (p05={p05:.3f}, p95={p95:.3f})")
    
    # Correlations
    print("\nPairwise correlations:")
    correlations = []
    for i in range(4):
        for j in range(i+1, 4):
            corr = np.corrcoef(data[:, i], data[:, j])[0, 1]
            correlations.append(abs(corr))
            print(f"  out{i+1}-out{j+1}: {corr:+.3f}")
    
    print(f"\n  max |corr|: {max(correlations):.3f}")
    print(f"  avg |corr|: {np.mean(correlations):.3f}")
    
    # Rail zone time
    print("\nTime in rail zones (out < 0.08 or out > 0.92):")
    for i in range(4):
        in_rail = np.mean((data[:, i] < SAUCE_RAIL_ZONE) | (data[:, i] > 1 - SAUCE_RAIL_ZONE))
        print(f"  out{i+1}: {in_rail*100:.1f}%")
    
    # Clamp hits
    print("\nHard clamp hits (out = 0 or out = 1):")
    for i in range(4):
        at_zero = np.sum(data[:, i] <= 0.001)
        at_one = np.sum(data[:, i] >= 0.999)
        print(f"  out{i+1}: {at_zero} at 0, {at_one} at 1")


if __name__ == '__main__':
    print("Running SauceOfGrav v1.4.3 simulation...")
    duration = 30
    history, hub_history, dt = run_simulation(duration_s=duration)
    
    compute_stats(history, dt)
    
    output_path = os.path.expanduser('~/Downloads/sauce_of_grav_v1_4_3.mp4')
    create_mp4(history, hub_history, dt, filename=output_path, duration_s=duration)
    print(f"\nMP4 saved to: {output_path}")
