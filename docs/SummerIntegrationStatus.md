# SUMMER Integration — Status Notes & Action Plan

*Updated 2026-08-15. Companion to [SummerCameraGuiHandoff.md](SummerCameraGuiHandoff.md)
(GUI contract) and `WspSummerDaemonHandoff.md` (GUI repo → WSP handoff).*

SUMMER = QHY42PRO camera + ZWO 7-position EFW filter wheel on telescope
port 2 (shared with SPRING). Goal: summer works in WSP exactly like spring —
`wintercmd` exposures/TEC, robotic `checkWhatToDo` observing, focus loops,
pointing models.

---

## Architecture map (who runs where)

```
MAIN COMPUTER (192.168.1.10, ns_host)
  wsp/systemControl:
    camdict["summer"]  = SummerCamera client      -> Pyro "SUMMERCamera"
    fwdict["summer"]   = summer_filterwheel client -> Pyro "SUMMERfw"
    launches summerFilterd.py locally (daemonlist)

SUMMER CAMERA PC (Windows, this machine)
  summer_camera_daemon.py (Pyro "SUMMERCamera", registers to ns 192.168.1.10)
      -> SummerClient (WebSocket, localhost:5566)
      -> CMOS Control GUI headless service (repo zwo-camera-control, branch qhy42):
         python -m cmos_camera_gui --headless --ws-port 5566 --auto-connect qhy --instrument summer

VISCAM RASPBERRY PI (192.168.1.228) - python 3.9, DO NOT TOUCH port 5001
  port 5001: web_server.py (legacy, UNCHANGED) - spring FLI wheel + Uniblitz shutter,
             cron keepalive, system python 3.9
  port 5002: summer_fw_server.py (NEW) - ZWO EFW via zwo_efw package,
             needs its own python >= 3.12 (miniforge) env + cron keepalive

REMOTE ANALYSIS COMPUTER (TBD — Nate)
  summer image-analysis daemon (pirt_daemon-style Pyro object):
    solve_astrometry(...) + run_focus_loop(...) — see contract below
```

`viscamd.py` / `viscam.py` are the OLD (2022) control-side path to the pi —
launch is commented out in systemControl, wintercmd wiring commented out:
vestigial, ignore.

## Key technical facts (hard-won, don't rediscover)

- **zwo_efw library** (github.com/mit-kavli-institute/python-zwo-efw-filter-wheel):
  bundles the ZWO SDK (all platforms incl. pi armv7) — nothing to download.
  Requires **python >= 3.12** (pyproject pin; code itself needs >= 3.10).
  pip-installable from git without poetry.
- **zwo_efw is 1-INDEXED**: slots 1..N matching the physical labels.
  `get_position` returns `None` while moving. Passing slot 0 sends SDK
  position -1 → triggers a **~30 s calibration spin** (this bit us once).
- **Summer FW protocol is therefore 1-indexed end-to-end** (unlike spring's
  0-indexed FLI): slots 1..7, dark = slot 7, home ≡ slot 1, **poll sentinel
  n=0** (not n=8 — avoids collision with 8-slot EFW models).
- EFW moves: ~1.6 s adjacent, ~2.5 s multi-slot hop. Pi endpoint blocks
  until settled (mirrors FLI semantics), 30 s server-side timeout.
- No shutter on summer — darks use the blocked wheel slot.
- Camera GUI contract (set_exposure exact-float echo, is_capturing through
  FITS write, `<save_path>/<filename>.fits` exactly): SummerCameraGuiHandoff.md.
  GUI passed full acceptance 2026-08-14 on real QHY42PRO.
- Camera daemon deltas from spring (7, all implemented): config-driven
  host/port, no-op init, tec_power_pct instead of voltage, shutdown =
  `not tec_enabled` (no warm-up wait — flagged decision), setpoint clamped
  -45..+20 C loudly, summer status extras (gain/offset/usbtraffic/gps_locked/
  gps_seq/vendor/idle_mode), image dir `.../summer`.
- Camera GUI no-hotplug constraint: QHY SDK enumerates at process start;
  replug ⇒ restart GUI service (daemon reconnect loop rides through).

## Done (code in repo; ✔hw = verified on real hardware)

**Camera stack (2026-08-15):**
- `wsp/camera/daemons/summer_camera_daemon.py` + interface-test notebook
- `wsp/camera/implementations/summer_camera.py`
- systemControl: SummerCamera + camdict["summer"]
- wintercmd: `--summer` works in doExposure/setExposure wait-loops;
  fixed latent `--winter default=True` bug that made `--summer` command
  winter in tecStart/tecStop/tecSetSetpoint/startupCamera/shutdownCamera/
  killCameraDaemon
- config.yaml `summer_camera:` block (gui_host/gui_port 5566, tec_setpoint 0.0)
- telemetry: summer camera exptime/TEC fields

**Filter wheel stack (2026-08-15):** ✔hw — full chain bench-tested with a
real 5-slot EFW on the camera PC: library walk-all-slots; `summer_fw_server`
endpoint (poll/goto/home/error paths); `summerFilterd` over Pyro (homes on
startup, goToFilter, invalid-position rejection); TRUE end-to-end
`local_filterwheel.newCommand.emit(signalCmd(...))` (the exact wintercmd
fw_goto path) → Pyro → daemon → HTTP → SDK → wheel.
- `wsp/viscam/summer_fw_server.py` (port 5002, deployment recipe in docstring)
- `wsp/filterwheel/summerFilterd.py` (Pyro "SUMMERfw"), `summer_filterwheel.py`,
  `summerfw_config.yaml`
- systemControl: summerfwd launch + fwdict["summer"] (makes `fw_goto --summer` live)
- telemetry: summer_fw fields
- `web_server.py` fully reverted — pi's spring server needs NO deployment

## Action plan

### Phase 1 — Deployment (no code; unblocks manual operation)

- [ ] **Camera PC env**: install Pyro5 + wsp deps + `pip install -e` the GUI
      repo into the env that will run `summer_camera_daemon.py`
      (the miniconda `qhy` env lacks Pyro5; `cmos_camera_gui` currently
      importable only via repo src path)
- [ ] Run GUI headless service (port 5566) + summer camera daemon
      (`-n 192.168.1.10`); service/autostart both
- [ ] Run `summer_camera_daemon_interface_test.ipynb` — the daemon has
      never talked to the real GUI yet
- [ ] **Pi**: miniforge env (check `uname -m`; armv7l → flag, miniforge
      builds are scarce), python >= 3.12;
      `pip install flask git+https://github.com/mit-kavli-institute/python-zwo-efw-filter-wheel.git@main`
- [ ] Pi: install `efw.rules` udev file (bundled in zwo_efw repo under
      `zwo_efw/efw_sdk/EFW_SDK/EFW_linux_mac_SDK_V1.7/lib/`) →
      `/etc/udev/rules.d/`, reload, replug; confirm spring FLI wheel still
      enumerates
- [ ] Pi: deploy `summer_fw_server.py`, add second cron keepalive line,
      `curl localhost:5002/summer_filter_wheel?n=0`
- [ ] **Real filter loadout** into `summerfw_config.yaml` +
      `config.yaml filter_wheels.summer` (both are PLACEHOLDERS:
      u,g,r,i,empty,empty,dark) — keep them in sync
- [ ] Smoke test from main computer: `fw_goto 3 --summer`,
      `startupCamera -c`, `doExposure --summer -t`

### Phase 2 — Robotic observing loop (4 small edits → checkWhatToDo works)

- [ ] config.yaml: add `summer:` under `telescope.ports.2.cameras` with
      `pointing_model_file` (bootstrap = spring's
      `pointing_model_spring_20251022.pxp`) — **single biggest unlock**:
      required by get_port_for_camera / get_camera_info / switchCamera /
      mount_model_load
- [ ] Confirm a loadable `.pxp` exists on the PWI4 machine (spring's file OK)
- [ ] config.yaml: add `"summer"` to `active_cameras`
      (gates roboOperator.py:6114)
- [ ] roboOperator.py:6420: `["winter", "spring"]` → include `"summer"` so
      the in-observation filter change actually moves the summer wheel
- [ ] config.yaml: `cal_params.summer.darks.filterID: 'r'` → `'dark'`
      (stale from shuttered old-summer; no shutter now, darks = blocked
      slot) and add `dark` to `filters.summer` if scheduled darks wanted
- [ ] Scheduler: nightly schedule rows with `camera=summer` + summer filters
- [ ] First `robo_switch_camera summer` under supervision (rotator
      stow/lockout machinery is port-based and already exercised by spring)
- Watch-items: roboOperator.py:2916 pixel-offset sign "might have to be
  flipped for SUMMER" (surfaces in first on-sky pointing checks);
  focusTracker has no summer best-focus until first focus run (switchCamera
  just logs and skips the focuser move)

### Phase 3 — Remote analysis daemon (Nate, remote computer)

One pirt_daemon-style Pyro object (suggested name: register as e.g.
`"summer_image_daemon"`; must see the summer image paths — run on the
camera PC or mount its data):

- [ ] `solve_astrometry(science_image, output_dir, timeout)` →
      `{ra, dec, ra_guess, dec_guess, pixel_scale, rotation_deg}`
      (deg; consumed at roboOperator.py:7726-7741)
- [ ] `run_focus_loop(image_list, output_dir, post_plot)` →
      `{"best_focus": <microns>, ...}` (consumed at roboOperator.py:5587-5593)

### Phase 4 — WSP-side focus + pointing branches (small, can land anytime)

- [ ] roboOperator.py:~5581: `elif loop_camname == "summer":` →
      summer analysis daemon `run_focus_loop` (mirror the spring block)
- [ ] roboOperator.py:~7710: `elif self.camname == "summer":` →
      summer analysis daemon `solve_astrometry` (mirror the spring block)
- [ ] Fix roboOperator.py:7603 `fw_goto 2` in remakePointingModel: no camera
      flag ⇒ defaults to the WINTER wheel (latent bug spring lives with).
      Make camera-aware with per-camera pointing filter position
- [ ] Check roboOperator.py:5764 (`if self.camname not in ["winter","spring"]`)
      — unreviewed focus-path guard, may need summer added

### Phase 5 — On-sky commissioning (order matters)

- [ ] `doFocusSeq --summer` (needs Phase 3+4 focus branch) — also populates
      focusTracker so switchCamera racks the focuser
- [ ] `robo_switch_camera summer` + `robo_remakePointingModel`; then
      `mount_model_save pointing_model_summer_<date>.pxp` and update
      `telescope.ports.2.cameras.summer.pointing_model_file`
- [ ] First scheduled summer night; verify darks (dark slot), flats
      (config flat model params are old-summer values — revisit exptime
      model constants), dithers, FITS headers

## Direct answers (as of 2026-08-15)

- **checkWhatToDo with summer?** Not yet — Phase 1 deployment + the four
  Phase 2 edits, then yes.
- **Pointing model?** WSP side is ~10 lines (Phase 4) once the Phase 3
  daemon exists; until then `remakePointingModel` hits "no recipe" and
  returns.
- **Focus?** Same shape: focus_loop config for summer already exists;
  blocked only on Phase 3 daemon + the Phase 4 elif.
