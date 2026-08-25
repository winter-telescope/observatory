#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
night_report.py

End-of-night reporting machinery for the robotic operator:

  - ErrorContextRecorder: a logging.Handler that keeps a rolling buffer of
    the wsp log and, when an error is triggered, writes a self-contained
    "error report" file holding N lines of log context from BEFORE the
    error and N lines from AFTER it. The report file is designed to be
    debugged after the fact on its own (e.g. uploaded to an LLM or read
    by a human with no access to the full night log).

  - NightTally: a small persistent (json-backed) per-night tally of
    attempted / completed / failed / aborted observations and errors,
    plus a formatter that renders the tally as a slack-friendly
    end-of-night summary. The tally is written to disk on every update,
    so a wsp restart mid-night does not lose the counts.

Both are wired up in roboOperator: the recorder is attached to the shared
wsp logger at init, broadcast_hardware_error triggers captures + error
tallies, the observing loop feeds attempt/result tallies, and
post_night_summary() (a wintercmd, also fired by a roboManager trigger at
dawn) posts the formatted summary to slack.

@author: nlourie
"""

import json
import logging
import os
import threading
from collections import deque
from datetime import datetime


class ErrorContextRecorder(logging.Handler):
    """
    Logging handler that captures log context around errors.

    Always keeps the last ``n_before`` formatted log lines in a ring
    buffer. When ``trigger()`` is called (or a record at
    ``auto_trigger_level`` or above passes through), it snapshots the
    ring as the "before" context and starts collecting the next
    ``n_after`` lines as the "after" context. The capture is flushed to
    a report file when the after-buffer fills, or on the first emit
    after ``timeout_s`` elapses, or when ``flush_pending()`` is called
    explicitly (e.g. from the end-of-night summary).

    Only one capture is open at a time: errors that fire while a capture
    is open are noted INSIDE the open report instead of spawning a new
    file, because errors cascade (one rotator jam produces dozens of
    downstream roboErrors) and one report per cascade is what you want
    to read afterwards. A per-night file cap backstops runaway loops.
    """

    # match the wsp file-log format (utils.setup_logger / logging_setup)
    FMT = (
        "%(asctime)s.%(msecs).03d [%(filename)s:%(lineno)s - %(funcName)s()] "
        "%(levelname)s: %(threadName)s: %(message)s"
    )
    DATEFMT = "%Y-%m-%d  %H:%M:%S"

    def __init__(
        self,
        report_dir_func,
        n_before=500,
        n_after=500,
        timeout_s=300.0,
        max_reports_per_night=50,
        auto_trigger_level=logging.ERROR,
    ):
        """
        report_dir_func: zero-arg callable returning the directory to
            write reports into (called at capture time, so the night
            rollover is always respected). The directory is created if
            needed.
        """
        super().__init__(level=logging.DEBUG)
        self.setFormatter(logging.Formatter(self.FMT, datefmt=self.DATEFMT))
        self.report_dir_func = report_dir_func
        self.n_before = int(n_before)
        self.n_after = int(n_after)
        self.timeout_s = float(timeout_s)
        self.max_reports_per_night = int(max_reports_per_night)
        self.auto_trigger_level = auto_trigger_level

        self._ring = deque(maxlen=self.n_before)
        self._pending = None  # dict while a capture is open
        self._reports_written = {}  # {report_dir: count}
        # logging.Handler gives us self.lock (an RLock) and acquire/release.
        # emit() runs with it held (via Handler.handle); trigger() and
        # flush_pending() take it explicitly since they're called from
        # outside the logging framework.

    # ------------------------------------------------------------------
    def emit(self, record):
        try:
            line = self.format(record)
        except Exception:
            return
        try:
            pend = self._pending
            if pend is not None:
                pend["after"].append(line)
                overtime = (
                    datetime.utcnow() - pend["opened_utc"]
                ).total_seconds() > self.timeout_s
                if len(pend["after"]) >= self.n_after or overtime:
                    self._flush_locked()
            # ring is appended AFTER serving the open capture, so the
            # triggering line itself sits at the tail of "before" and the
            # marker in the report lands exactly at the error
            self._ring.append(line)

            # auto-capture on ERROR-level records that arrive with no
            # capture open (and that didn't come from an explicit trigger,
            # which will have opened one already)
            if self._pending is None and record.levelno >= self.auto_trigger_level:
                self._open_capture_locked(
                    context="log",
                    cmd="-",
                    system="-",
                    msg=record.getMessage()[:500],
                )
        except Exception:
            # never let report bookkeeping break the logging chain
            pass

    # ------------------------------------------------------------------
    def trigger(self, context="?", cmd="?", system="?", msg=""):
        """
        Explicitly open a capture for an error (e.g. a roboError from
        broadcast_hardware_error). Returns the report filepath this
        error's context will be (or is being) written to, or None if
        reporting is unavailable (cap hit / dir failure).
        """
        self.acquire()
        try:
            if self._pending is not None:
                # error cascade: note it inside the open report
                self._pending["extra_errors"].append(
                    f"{datetime.utcnow().isoformat()} | system={system} | "
                    f"cmd={cmd} | context={context} | {msg}"
                )
                return self._pending["path"]
            return self._open_capture_locked(context, cmd, system, msg)
        except Exception:
            return None
        finally:
            self.release()

    def flush_pending(self):
        """Flush any open capture immediately (end of night, shutdown)."""
        self.acquire()
        try:
            if self._pending is not None:
                self._flush_locked()
        except Exception:
            pass
        finally:
            self.release()

    # ------------------------------------------------------------------
    def _open_capture_locked(self, context, cmd, system, msg):
        try:
            report_dir = self.report_dir_func()
            os.makedirs(report_dir, exist_ok=True)
        except Exception:
            return None
        n_written = self._reports_written.get(report_dir, 0)
        if n_written >= self.max_reports_per_night:
            return None

        now = datetime.utcnow()
        safe_sys = "".join(c if c.isalnum() else "_" for c in str(system))[:20]
        safe_cmd = "".join(c if c.isalnum() else "_" for c in str(cmd))[:30]
        path = os.path.join(
            report_dir,
            f"errorreport_{now.strftime('%Y%m%d_%H%M%S')}_{safe_sys}_{safe_cmd}.log",
        )
        self._pending = {
            "path": path,
            "opened_utc": now,
            "context": context,
            "cmd": cmd,
            "system": system,
            "msg": msg,
            "before": list(self._ring),
            "after": [],
            "extra_errors": [],
        }
        self._reports_written[report_dir] = n_written + 1
        return path

    def _flush_locked(self):
        pend, self._pending = self._pending, None
        if pend is None:
            return
        try:
            hdr = [
                "=" * 78,
                "WSP ERROR REPORT",
                f"error time (UTC): {pend['opened_utc'].isoformat()}",
                f"system:  {pend['system']}",
                f"command: {pend['cmd']}",
                f"context: {pend['context']}",
                f"message: {pend['msg']}",
                f"log lines: {len(pend['before'])} before / "
                f"{len(pend['after'])} after",
                "",
                "This file is self-contained: it holds the wsp log context "
                "surrounding the",
                "error above. The '>>> ERROR HERE <<<' marker sits at the "
                "moment the error",
                "was raised. Additional errors that occurred while this "
                "capture was open",
                "(an error cascade) are listed below rather than in "
                "separate files.",
                "=" * 78,
            ]
            if pend["extra_errors"]:
                hdr += ["", "ADDITIONAL ERRORS DURING THIS CAPTURE:"]
                hdr += [f"  {e}" for e in pend["extra_errors"]]
                hdr += ["=" * 78]
            body = (
                hdr
                + ["", f"----- LOG BEFORE ERROR ({len(pend['before'])} lines) -----"]
                + pend["before"]
                + ["", ">>> ERROR HERE <<<", ""]
                + [f"----- LOG AFTER ERROR ({len(pend['after'])} lines) -----"]
                + pend["after"]
                + [""]
            )
            with open(pend["path"], "w") as f:
                f.write("\n".join(body))
        except Exception:
            pass


class NightTally:
    """
    Persistent per-night tally of observing outcomes, json-backed so the
    counts survive a wsp restart mid-night. The night key comes from
    ``night_func`` (utils.tonight_local: rolls over at 08:00 local, same
    convention as the ToO attempts reset).
    """

    def __init__(self, summary_dir, night_func, log_func=None):
        self.summary_dir = summary_dir
        self.night_func = night_func
        self.log = log_func or (lambda msg: None)
        self._lock = threading.Lock()
        self.data = self._load()

    # ------------------------------------------------------------------
    def _path_for(self, night):
        return os.path.join(self.summary_dir, f"night_{night}.json")

    def _fresh(self, night):
        return {
            "night": night,
            "attempted": 0,
            "completed": 0,
            "failed": 0,
            "aborted": 0,
            "targets": {},  # key -> {name, camera, filters, obsHistIDs,
            #                          n_attempted, n_completed, total_exptime_s}
            "errors": [],  # {time_utc, system, cmd, msg, report}
        }

    def _load(self):
        night = self.night_func()
        try:
            with open(self._path_for(night), "r") as f:
                data = json.load(f)
            if data.get("night") == night:
                return data
        except (OSError, ValueError):
            pass
        return self._fresh(night)

    def _save(self):
        try:
            os.makedirs(self.summary_dir, exist_ok=True)
            tmp = self._path_for(self.data["night"]) + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.data, f, indent=1)
            os.replace(tmp, self._path_for(self.data["night"]))
        except Exception as e:
            self.log(f"night tally: could not save: {e}")

    def _roll_if_new_night(self):
        night = self.night_func()
        if night != self.data.get("night"):
            self.data = self._fresh(night)

    @staticmethod
    def _target_key(obs):
        name = str(obs.get("targName", "") or "").strip()
        if name and name.lower() not in ("nan", "none"):
            return name
        return f"obsHistID {obs.get('obsHistID', '?')}"

    def _target_entry(self, obs):
        key = self._target_key(obs)
        t = self.data["targets"].setdefault(
            key,
            {
                "name": key,
                "camera": str(obs.get("camera", "winter")),
                "filters": [],
                "obsHistIDs": [],
                "n_attempted": 0,
                "n_completed": 0,
                "total_exptime_s": 0.0,
            },
        )
        filt = str(obs.get("filter", "?"))
        if filt not in t["filters"]:
            t["filters"].append(filt)
        try:
            ohid = int(obs.get("obsHistID", -1))
            if ohid not in t["obsHistIDs"]:
                t["obsHistIDs"].append(ohid)
        except (TypeError, ValueError):
            pass
        return t

    # ------------------------------------------------------------------
    def record_attempt(self, obs):
        try:
            with self._lock:
                self._roll_if_new_night()
                self.data["attempted"] += 1
                self._target_entry(obs)["n_attempted"] += 1
                self._save()
        except Exception as e:
            self.log(f"night tally: record_attempt failed: {e}")

    def record_result(self, obs, completed, aborted=False):
        """
        completed: the observation ran end-to-end (row marked observed=1).
        aborted:   only looked at when completed is False — the failure
                   was a stop/weather interruption rather than a target
                   or hardware problem.
        """
        try:
            with self._lock:
                self._roll_if_new_night()
                t = self._target_entry(obs)
                if completed:
                    self.data["completed"] += 1
                    t["n_completed"] += 1
                    try:
                        t["total_exptime_s"] += float(obs.get("visitExpTime", 0.0))
                    except (TypeError, ValueError):
                        pass
                elif aborted:
                    self.data["aborted"] += 1
                else:
                    self.data["failed"] += 1
                self._save()
        except Exception as e:
            self.log(f"night tally: record_result failed: {e}")

    def record_error(self, system, cmd, msg, report_path=None):
        try:
            with self._lock:
                self._roll_if_new_night()
                self.data["errors"].append(
                    {
                        "time_utc": datetime.utcnow().isoformat(),
                        "system": str(system),
                        "cmd": str(cmd),
                        "msg": str(msg)[:300],
                        "report": os.path.basename(report_path) if report_path else None,
                    }
                )
                self._save()
        except Exception as e:
            self.log(f"night tally: record_error failed: {e}")

    # ------------------------------------------------------------------
    def format_summary(self, error_report_dir=None):
        """Render the tally as a slack-friendly text block."""
        with self._lock:
            self._roll_if_new_night()
            d = self.data

        lines = [f":crescent_moon: *Night summary for {d['night']}*"]
        lines.append(
            f"*Observed:* {d['completed']}/{d['attempted']} attempted"
            f"  |  *Failed:* {d['failed']}"
            f"  |  *Aborted (weather/stop):* {d['aborted']}"
            f"  |  *Errors:* {len(d['errors'])}"
        )

        observed = {
            k: t for k, t in d["targets"].items() if t["n_completed"] > 0
        }
        if observed:
            lines.append("")
            lines.append(f"*Targets observed ({len(observed)}):*")
            for t in sorted(
                observed.values(), key=lambda t: -t["total_exptime_s"]
            ):
                filters = "/".join(t["filters"])
                lines.append(
                    f"  • {t['name']} ({t['camera']}, {filters}): "
                    f"{t['n_completed']} visit"
                    f"{'s' if t['n_completed'] != 1 else ''}, "
                    f"{t['total_exptime_s']:.0f} s total exposure"
                )
        else:
            lines.append("")
            lines.append("*No targets fully observed.*")

        never_completed = {
            k: t for k, t in d["targets"].items() if t["n_completed"] == 0
        }
        if never_completed:
            lines.append(
                f"*Attempted but never completed ({len(never_completed)}):* "
                + ", ".join(
                    f"{t['name']} ({t['n_attempted']}x)"
                    for t in never_completed.values()
                )
            )

        if d["errors"]:
            # group errors by (system, cmd) for digestibility
            by_syscmd = {}
            for e in d["errors"]:
                by_syscmd.setdefault((e["system"], e["cmd"]), []).append(e)
            lines.append("")
            lines.append(f"*Errors ({len(d['errors'])}):*")
            for (system, cmd), errs in sorted(
                by_syscmd.items(), key=lambda kv: -len(kv[1])
            ):
                reports = sorted({e["report"] for e in errs if e["report"]})
                rep_str = f" — report: {', '.join(reports)}" if reports else ""
                lines.append(f"  • {system} x{len(errs)} (cmd: {cmd}){rep_str}")
            if error_report_dir:
                lines.append(f"  error report files: {error_report_dir}")

        return "\n".join(lines)
