# cetar

A physics-based whip overlay for Windows. Hold the middle mouse button, swing, and crack a whip over any window on screen — terminals included.

*Cetar* is the Indonesian onomatopoeia for the sound of a whip crack.

## Features

- **Works everywhere.** A transparent, click-through, always-on-top overlay spans every connected monitor, so the whip appears on top of any application.
- **Real whip motion.** While you swing, the lash trails behind the handle. When your hand stops, it rolls out from handle to tip, reaches full extension, and cracks. Then it recoils.
- **Directional.** The whip cracks in the direction you swung. Pulling your hand back after a crack is recognised as a wind-up and ignored.
- **Cartoon impact.** Each crack spawns a jagged starburst with onomatopoeia, impact lines, orbiting dizzy stars and a speech bubble, plus a synthesized crack sound.
- **Window shake.** The window under the tip shakes briefly when hit.
- **Zero dependencies.** Python standard library only (`tkinter`, `ctypes`, `winsound`).

## Requirements

- Windows 10 or 11
- Python 3.8+ with Tk (included in the python.org installer)

## Usage

```powershell
pythonw cetar.py
```

`pythonw` runs it without a console window. Use `python cetar.py` instead to see errors in the console.

| Action | Input |
|---|---|
| Draw the whip | Hold the middle mouse button |
| Crack | Swing quickly, then stop |
| Quit | `Ctrl` + `Shift` + `Q` |

## Configuration

Tuning constants live at the top of `cetar.py`:

| Constant | Default | Effect |
|---|---|---|
| `N`, `SEG` | `38`, `13` | Number of segments and segment length (px). The first `H` segments form the handle. |
| `H` | `6` | Handle length in segments |
| `MAX_TILT` | `0.5` | Maximum handle tilt (radians) |
| `GRAV`, `DAMP` | `0.6`, `0.92` | Gravity and velocity damping of the resting lash |
| `HAND_SPEED` | `18` | Hand speed (px per step) that counts as a swing. Lower it if cracking takes too much effort. |
| `LASH_FRAMES` | `7` | Duration of the roll-out before the crack (steps of 1/60 s). Lower means snappier. |
| `LASH_WAVE` | `0.35` | Width of the travelling roll-out wave along the lash |
| `RETURN_STEPS` | `40` | Window after a crack in which an opposite-direction swing counts as a wind-up |
| `RECOIL` | `18` | Strength of the tip's recoil after the crack |

## How it works

- **Overlay.** A borderless Tk window covers the virtual desktop. Its background is a colour key made transparent with `-transparentcolor`. The extended styles `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE` make it click-through and keep it out of the taskbar.
- **Input.** The cursor and middle button are polled with `GetCursorPos` and `GetAsyncKeyState`. No global hooks are installed.
- **Timing.** Simulation runs at a fixed 60 Hz timestep independent of Tk's timer resolution. Cursor positions are interpolated between steps.
- **Resting lash.** The lash uses Verlet integration with follow-the-leader length constraints and velocity correction ([Müller et al., 2012](https://matthias-research.github.io/pages/publications/FTLHairFur.pdf)). Each segment keeps its exact length without the constraint injecting energy.
- **Crack.** Swing direction is accumulated while hand speed is above `HAND_SPEED`. When the hand decelerates, segment angles are blended toward the swing direction by a smoothstep wave that travels from handle to tip, rotating over the top. The crack fires at full extension.
- **Window shake.** `WindowFromPoint` locates the top-level window under the tip, and `SetWindowPos` offsets it through a short decaying sequence.

## Testing

```powershell
python test_cetar.py
```

These are headless physics checks, with no window and no mouse. They verify that:

- a fast swing produces exactly one crack, after the hand stops, in the swing direction;
- a slow swing produces none;
- the lash length is preserved and the lash comes to rest;
- a right–left–right sequence yields two right-hand cracks.

## Limitations

- Maximized windows are not shaken.
- The middle click still reaches the application underneath. In browsers, for example, this can trigger autoscroll.
- Windows running with higher privileges than the overlay (e.g. an elevated terminal) cannot be moved.

## License

[MIT](LICENSE)
