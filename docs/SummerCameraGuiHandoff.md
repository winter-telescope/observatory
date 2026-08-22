# SUMMER Camera GUI — Handoff / Requirements Doc

**Audience:** the agent/developer building the SUMMER camera GUI (the vendor-facing
control application, developed in its own repository outside `observatory`).

**Goal:** the SUMMER GUI must expose a command server that a WSP camera interface
daemon (a near-clone of
[`wsp/camera/daemons/spring_camera_daemon.py`](../wsp/camera/daemons/spring_camera_daemon.py))
can drive, so that SUMMER plugs into WSP exactly like SPRING does: `wintercmd`
`do_exposure`, `set_exposure`, TEC management, robotic startup/shutdown, scheduled
observations.

---

## 1. Where the GUI sits in the WSP camera architecture

WSP uses a 4-layer stack for every camera (see header of
[`wsp/camera/camera.py`](../wsp/camera/camera.py)):

```
wintercmd / roboOperator                    (main WSP process)
        │  method calls
        ▼
BaseCamera client                           (wsp/camera/camera.py, in WSP process)
        │  Pyro5 RPC (name server)
        ▼
Camera interface daemon                     (wsp/camera/daemons/<cam>_camera_daemon.py,
        │                                    built on wsp/camera/daemon_framework.py)
        │  vendor protocol — THIS IS THE INTERFACE YOU ARE BUILDING
        ▼
Vendor GUI / camera server  ◄── YOU         (owns the camera hardware, writes FITS)
        ▼
Camera hardware (SDK/driver)
```

Key division of labor:

- **The GUI owns the hardware.** It is the only process that talks to the camera
  SDK. It runs continuously (service/autostart), with or without a daemon
  connected, and is also usable by a human standing at the instrument.
- **The GUI writes the FITS files.** The daemon never sees pixel data; it tells
  the GUI the directory + basename and passes down a big list of FITS header
  cards (telescope pointing, weather, schedule metadata — see the example in the
  interface-test notebook). The GUI merges those with its own camera-level
  headers and writes the file.
- **The interface daemon is a thin client.** It polls the GUI for status at 1 Hz,
  translates WSP commands into GUI protocol commands, and decides
  command-completion by watching the polled status.

The working reference for the GUI side is the SPRING GUI's `pirtcam` server
(TCP, JSON request/response on port 5555). SUMMER's GUI does **not** need to use
the same transport (the qhy GUI's JSON-over-WebSocket transport is fine), but it
**must** reproduce the same command semantics and status contract described
below, because the daemon framework's completion logic depends on them.

## 2. The contract, derived from how the spring daemon uses its GUI

Everything in this section is a hard requirement extracted from
`spring_camera_daemon.py` + `daemon_framework.py`. File/line references point at
the code that consumes each behavior.

### 2.1 Client API the daemon needs

The daemon holds a persistent client object and calls these methods
(`spring_camera_daemon.py:38-46` and throughout). Ship a Python client class
(`summer_camera_gui/client.py`, e.g. `SummerClient`) with these exact method
names and semantics so the summer daemon can be a near-copy of spring's:

| Method | Semantics | Reply |
|---|---|---|
| `CameraClient(host, port)` + `.connect()` | open persistent connection | — |
| `get_status()` | return cached status snapshot, **fast, never blocks on hardware** | `{"status": "success", "data": {...}}` (see 2.2) |
| `set_exposure(seconds)` | request exposure time; returns immediately, settling happens in background | `{"status": "success", "message": ...}` |
| `set_save_path(dir)` | set output directory for next capture; create it if missing; accept `~` paths | status/message dict |
| `capture_frames(filename, nframes, object, observer, headers, wait_for_completion=False, debug=False)` | start capture and **return an ACK immediately** (see 2.4) | `{"status": "success"}` or `{"status": "error", "message": ...}` |
| `set_tec_enabled(bool)` | turn cooler on/off | status dict |
| `set_tec_temperature(float °C)` | set cooler setpoint | status dict |

Error convention: every reply is a dict with `"status": "success"` or
`"status": "error"` plus a human-readable `"message"`. Never raise/hang on
hardware failure — report it. The daemon treats any non-`success` status as a
command failure and goes to its ERROR state.

SUMMER-specific extras (gain, offset, read mode, USB traffic, ROI…) are welcome
as **additional** commands; they don't participate in the core contract. The
spring-only `set_correction(...)` calls have no summer equivalent and won't be
used.

### 2.2 `get_status` data contract

The daemon polls `get_status()` once per second
(`daemon_framework.py:420-471`) and reads `reply["data"]`. Required keys
(names must match exactly — the daemon does literal dict lookups,
`spring_camera_daemon.py:504-656`):

```jsonc
{
  "status": "success",
  "data": {
    // state machine — REQUIRED
    "camera_state": "READY",          // string, see vocabulary below
    "ready": true,
    "is_capturing": false,            // true from capture start until FITS fully written
    "current_frame": 0,               // progress info while capturing
    "total_frames": 0,
    "capture_time_remaining": 0.0,    // seconds

    // exposure — REQUIRED
    "exposure": 30.0,                 // SECONDS, float, echo of last set_exposure value

    // TEC / cooling — REQUIRED
    "tec_temp": -60.0,                // sensor temp, °C
    "tec_setpoint": -60.0,
    "tec_enabled": 1,                 // bool or 0/1
    "tec_locked": 1,                  // temp stable at setpoint (see 2.6)
    "tec_voltage": 5.27,              // if unavailable, report cooler power differently, see note

    // bookkeeping — REQUIRED
    "save_path": "~/data/images/20260814/summer",

    // housekeeping temps — spring reports these; report what SUMMER has,
    // use -888 for unavailable values (WSP's DEFAULT_STATUS_VALUE convention)
    "case_temp": 14.7,
    "digpcb_temp": 34.2,
    "senspcb_temp": 13.2
  }
}
```

Notes:

- **Units: exposure is float seconds.** If the camera SDK uses other units
  (µs, ms), convert at the server boundary and never leak them into the
  protocol.
- **`exposure` must echo back exactly the value set.** The daemon's
  set-exposure completion check is a float equality test
  (`spring_camera_daemon.py:447-463`): `status exposure == requested value` AND
  `camera_state == "READY"`. Store/echo the requested float, don't round-trip
  through the SDK's quantized µs value. If the SDK quantizes, echo the requested
  value in status and keep the true value in an extra key (e.g.
  `exposure_actual`).
- **JSON-native types only** (float/int/bool/str). No numpy scalars.
- `tec_voltage`: spring derives TEC current/percent from voltage. If SUMMER's
  SDK gives a different measure of cooler drive (e.g. PWM %), report
  `tec_voltage: -888` and add e.g. `tec_power_pct`; the summer daemon will
  override `tecGetPercentage()` etc. Just make sure *some* measure of cooler
  drive level is in the status.
- Extra keys are fine and encouraged (gain, offset, read mode, chip temp, sensor
  name…) — the summer daemon's `update_camera_state_info()` will forward them
  into WSP telemetry.

### 2.3 `camera_state` vocabulary

The daemon copies this string into its own state dict as `gui_state` and makes
decisions on it. Required values:

- `"READY"` — idle, can accept capture/exposure commands. The daemon's
  set-exposure completion literally checks `gui_state == "READY"`.
- `"SETTING_EXPOSURE"` — between `set_exposure` ack and the new time being
  active (this is what spring reports; keep the same string).
- `"EXPOSING"` (or similar) while capturing — informational; capture completion
  is decided by `is_capturing`, not by this string.
- An error string (e.g. `"ERROR"`) when the camera is unusable.

WSP's own state vocabulary is in [`wsp/camera/state.py`](../wsp/camera/state.py)
for reference, but the GUI's `camera_state` is its own field — only `"READY"`
and `"SETTING_EXPOSURE"` are load-bearing.

### 2.4 The capture lifecycle — the most important behavior to get right

The daemon's exposure flow (`spring_camera_daemon.py:154-305, 465-502`,
`daemon_framework.py:473-523`):

1. Daemon calls `set_save_path(imdir)`.
2. Daemon calls `capture_frames(filename=<basename, no path, no extension>,
   nframes=1, object=..., observer=..., headers=[...], wait_for_completion=False)`.
3. GUI replies with an **immediate ACK** (`{"status": "success"}`) — it must
   NOT block until the capture finishes. (If the GUI already has a blocking
   capture-and-wait command for interactive/scripting use, that's fine to keep,
   but the daemon cannot use it: the daemon's command worker must return
   promptly, and completion is detected by polling.)
4. Daemon then polls `get_status()` at 1 Hz. It considers the exposure
   **complete the first moment it sees `is_capturing == false`** (after a 1 s
   grace period following the command,
   `daemon_framework.py:478-485`).
5. On completion the daemon immediately symlinks/copies
   `<save_path>/<filename>.fits` as the "last image" and WSP may read it right
   away.

This forces three hard requirements:

- **R1 — `is_capturing` must be `true` in status *before* the capture ACK is
  sent.** The grace period is only 1 s; if the GUI acks and status still shows
  `is_capturing: false` a second later, the daemon declares the exposure
  complete while the shutter is still open, and WSP will try to use a
  nonexistent file. Set the flag synchronously with accepting the command.
- **R2 — `is_capturing` stays `true` through readout AND the FITS write**, and
  only goes `false` after the file is fully written and closed. The flag means
  "the requested product is not on disk yet", not "the sensor is integrating".
- **R3 — exact output filename.** The GUI must write exactly
  `<save_path>/<filename>.fits` — single file, single image HDU for
  `nframes=1`, no frame-number suffix, no cube naming, no timestamp decoration.
  The daemon computes this path itself (`makeImageFilepath`,
  `daemon_framework.py:615-629`) and never asks the GUI where the file went.
  (What to do for `nframes > 1` is an open decision — see §3; spring only ever
  uses `nframes=1`.)

Timing budget: the daemon times out the whole operation at
`2 * exptime + 30 s` (`spring_camera_daemon.py:154-158`). Capture + readout +
FITS write must comfortably fit in that.

Failure path: if the capture fails after the ACK (SDK error, disk full), set
`is_capturing: false` AND put the camera in an error `camera_state`, and log
loudly. (Known gap: the daemon currently keys only off `is_capturing`, so also
make sure a failed capture doesn't leave a stale/partial `.fits` file at the
target path.)

### 2.5 FITS writing and headers

- `headers` arrives as a list of `[key, value, comment-or-null]` triples or
  `(key, value[, comment])` tuples (JSON-safe; no astropy objects on the wire). The daemon pre-strips `OBJECT` and `OBSERVER` and passes them as the
  dedicated `object` / `observer` arguments — write those into the header too.
- The WSP header list is large (~100 cards: pointing, weather, schedule
  metadata — see the captured example in
  [`spring_camera_daemon_interface_test.ipynb`](../wsp/camera/daemons/spring_camera_daemon_interface_test.ipynb)).
  Pass them through verbatim; on key collision with GUI-generated cards, decide
  a consistent winner (spring/qhy convention: caller-supplied headers win).
- The GUI adds its own camera-truth cards: actual exposure time, gain/offset,
  read mode, detector temp at shutter, binning/ROI, sensor name, UTC of frame
  start (`DATE-OBS`/`UTCSHUT` style), etc.

### 2.6 TEC behavior

- `set_tec_temperature(t)` then `set_tec_enabled(True)` is the robotic startup
  sequence; the daemon then waits (up to 30 min) for
  `|tec_temp - setpoint| < 0.5 °C` before declaring the camera READY
  (`spring_camera_daemon.py:329-361, 398-426`). So the GUI's cooling loop must
  run unattended and keep reporting `tec_temp` faithfully during cooldown.
- `tec_locked` should mean "temperature is stable at setpoint" (spring GUI's
  definition; hysteresis of a few tenths °C over ~tens of seconds is fine).
  It is surfaced in WSP telemetry as `tec_steady`.
- Robotic shutdown = `set_tec_enabled(False)`; the daemon waits for warm-up
  (`tec_temp > -45 °C` for spring — summer's daemon will pick its own
  threshold). Consider a GUI-side ramped warm-up if the sensor needs one.

### 2.7 Connection & lifecycle robustness

- **The daemon auto-reconnects on any error** (`spring_camera_daemon.py:55-72`):
  a failed status poll marks the connection dead and it immediately re-runs
  `setup_connection()`. The server must therefore tolerate abrupt client
  disconnects and accept new connections indefinitely, with no per-connection
  state that matters (all state lives in the GUI, not the session).
- One controlling client at a time is sufficient, but don't wedge if a second
  connection arrives (the old spring GUI just serves whoever's connected).
- The GUI must run headless-capable / as an autostart service on the SUMMER
  camera machine and survive daemon restarts with zero interaction. On
  (re)connect the daemon may re-run its init sequence — init-type commands
  must be idempotent.
- `get_status` is called every second forever: serve it from a cached snapshot
  updated by the GUI's own poll loop; never make it synchronously touch the SDK.

## 3. Architecture decisions (proposed defaults — flag disagreements early)

1. **Transport is the GUI's choice** — raw TCP JSON (what SPRING's pirtcam
   uses), WebSocket, ZMQ: the daemon doesn't care. It cares about the client
   class API (§2.1) and the status shape (§2.2). Deliverable is a
   `SummerClient` Python class exposing the pirtcam `CameraClient` method names
   over whatever transport the GUI uses, installable (or vendorable) on the
   observatory machine.
2. **Reshape, don't adapt.** Implement the §2 contract *in the GUI/server*
   (new command handlers alongside — or replacing — `status`/`record`/`cooler`),
   instead of writing a thick translation layer in the daemon. The daemon should
   stay a near-copy of `spring_camera_daemon.py`; every semantic mismatch pushed
   into the daemon is a place summer and spring drift apart.
3. **Non-blocking capture is non-negotiable** (§2.4). A blocking
   capture-and-wait command can exist for human/scripting use, but the daemon
   path needs the ack-then-poll form with `is_capturing` semantics R1–R3.
4. **Port:** pick a fixed port ≠ 5555 (spring) so both GUIs can coexist on one
   machine if needed — proposal: **5566**. Put host/port in a config file, not
   hardcoded; the summer daemon will read its copy from WSP's `config.yaml`.
5. **Units at the boundary:** seconds and °C everywhere in the protocol;
   µs/SDK-native units stay inside the GUI.
6. **`nframes > 1`:** out of scope for WSP integration (daemon always sends
   `nframes=1`). If the GUI supports multi-frame for local use, fine, but the
   `nframes=1` path must satisfy R3 exactly.
7. **Naming:** the camera is `summer` everywhere (directories, FITS `INSTRUME`,
   config keys). WSP `config.yaml` already carries `summer` sections (darks/
   flats/focus) from the original SUMMER camera — the daemon work will reuse
   them. Default image dir the daemon will send:
   `~/data/images/<tonight>/summer`.
8. **Status extras are cheap — include them.** Anything in `data` can be piped
   into WSP telemetry by the daemon with ~3 lines. Gain, offset, read mode,
   ambient/chip temps, firmware, USB traffic: put them in.

## 4. Acceptance test (GUI side, no WSP needed)

A script driving only `SummerClient` must pass:

1. `connect()`; `get_status()` returns the §2.2 shape with all required keys.
2. `set_exposure(7.5)` → immediate ack; within a few seconds status shows
   `camera_state: "READY"` and `exposure: 7.5` (exact float).
3. `set_save_path(<tmpdir>)`; `capture_frames(filename="test_0001", nframes=1,
   object="TEST", observer="pytest", headers=[["FIELDID", 42, "test card"]],
   wait_for_completion=False)` → ack returns in ≪1 s; the *first*
   `get_status()` after the ack already shows `is_capturing: true` (R1).
4. Poll at 1 Hz until `is_capturing: false`; at that exact moment
   `<tmpdir>/test_0001.fits` exists, opens with astropy, and contains
   `OBJECT`, `OBSERVER`, `FIELDID`, and the GUI's own `EXPTIME` (R2, R3).
5. `set_tec_temperature(-5)`, `set_tec_enabled(True)` → status shows setpoint,
   `tec_enabled: 1`, falling `tec_temp`, and eventually `tec_locked: 1`;
   `set_tec_enabled(False)` reverses it.
6. Kill the client mid-capture, reconnect, `get_status()` still works and the
   capture completed on disk.
7. Send garbage JSON / unknown command → error reply, server stays up.

The mirror-image test already exists for spring:
`wsp/camera/daemons/spring_camera_daemon_interface_test.ipynb` (its captured
outputs are the ground-truth examples of the status shape).

## 5. Files the GUI agent should read (this repo)

Protocol ground truth (read first):

- `wsp/camera/daemons/spring_camera_daemon.py` — the consumer of the GUI
  protocol; every `self.cam.*` call is a contract requirement.
- `wsp/camera/daemons/spring_camera_daemon_interface_test.ipynb` — captured
  real `get_status()` replies from the SPRING GUI and a full example WSP header
  list.
- `wsp/camera/daemon_framework.py` — the polling/completion machinery
  (esp. `pollStatus`, `_check_pending_completion`, `makeImageFilepath`,
  `_exposure_complete`).
- This document.

Context (skim):

- `wsp/camera/state.py` — WSP camera state vocabulary.
- `wsp/camera/camera_command_decorators.py` — how async commands +
  `pending_completion` work.
- `wsp/camera/camera.py` — the BaseCamera client one layer up (shows what WSP
  ultimately does with status and files).
- `wsp/camera/implementations/spring_camera.py` — how a camera is instantiated
  in WSP (10 lines; summer's will mirror it).

The SUMMER GUI itself is developed in a separate repository; this bundle is
everything the GUI agent needs *from the observatory side* to implement the
contract.

## 6. What happens after the GUI (daemon-side plan, for context)

Once the GUI meets §2/§4, the observatory-side work is:

1. `wsp/camera/daemons/summer_camera_daemon.py` — copy spring's, swap the
   client import, adjust TEC thresholds/timeouts and `update_camera_state_info`
   keys, `create_camera_daemon(SummerCameraInterface, "SUMMERCamera")`.
2. `wsp/camera/implementations/summer_camera.py` — mirror spring's.
3. Wire `summer` into `config.yaml` daemon/telemetry sections, `wintercmd`,
   `systemControl`/`roboOperator` camera dicts (the `summer` filter/cal/focus
   config blocks already exist).
4. Interface-test notebook mirroring spring's.

The cleaner the GUI matches the contract, the more step 1 is a mechanical copy.
