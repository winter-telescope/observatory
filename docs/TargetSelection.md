# Target Ranking & Selection

How the robotic operator decides which observation to dispatch next.
Entry point: `roboOperator.load_best_observing_target(obstime_mjd)`, called
from `checkWhatToDo()` each time the observing loop needs a target. ToO
schedules always win over the survey: the survey is only consulted when no
ToO row survives the cuts.

## 1. ToO schedules (checked first)

`load_best_observing_target` globs `*.db` in the ToO schedule directory and
builds one combined candidate table:

1. **Nightly attempts reset.** Once per observing night (the
   `utils.tonight_local()` string, which rolls over at 08:00 local), every
   unobserved row in every ToO file gets its `attempts` counter zeroed —
   a row that struck out last night (weather, hardware, a since-fixed
   config bug) deserves fresh tries tonight. The last-reset night is
   persisted in `last_attempts_reset_night.txt` in the ToO directory, so a
   wsp **restart mid-night does not re-grant attempts**; only the first
   scan after the 8am rollover does.
2. **Parse (cached).** Each file is read through `_get_too_df`, which
   caches the parsed + schema-validated dataframe keyed on the file's
   `(mtime, size)` and only re-reads a file when that stamp changes — see
   §4 for what does and doesn't invalidate the cache.
3. **Per-file cuts**, applied in order — a file that ends up empty is
   logged with the reason and skipped:
   - **Window / bookkeeping:** `validStart <= now <= validStop`,
     `observed == 0`, `attempts < max_observation_attempts` (config,
     default 2).
   - **Camera observability:** the row's `camera` (missing column →
     `winter`) must be in config `active_cameras` AND not on a locked-out
     M3 port. This is what keeps the scheduler from churning on e.g.
     spring rows after a port 2 lockout.
   - **Filter validity:** the row's `filter` must be one of the camera's
     valid filters — the keys of that camera's block in the config
     `filters:` section (NOT `filter_wheels:`, which only maps wheel
     positions; the two must be kept in sync when a filter is installed).
     `do_currentObs` re-checks this at dispatch, so without this cut a
     mismatch churns: the row ranks best, fast-fails the dispatch check,
     burns an attempt, repeats (2026-08-23: ~15 min silently eating all
     45 spring/Hs rows after Hs was added to `filter_wheels:` but not
     `filters:`).
   - **Elevation & airmass:** current airmass `< maxAirmass` (row value,
     or derived from telescope `min_alt` if the column is missing), and
     current altitude within telescope `[min_alt, max_alt]`.
   - **Ephemeris separation:** target not within the configured minimum
     distance of any body in `config['ephem']['min_target_separation']`
     (body positions computed once per scan, not per file).
4. **Ranking.** Survivors from all files are concatenated and sorted in a
   single call:

   ```python
   full_df.sort_values(by=["priority", "validStop"], ascending=[False, True])
   ```

   i.e. **highest priority first; ties broken by earliest deadline
   (validStop)**. Rows without a priority column get priority 0.
5. **Dispatch.** The top row wins and becomes `currentObs`. Its origin
   file is wired up as the active schedule — but only actually re-loaded
   (`loadSchedule` = full `SELECT *` + schema validation) **if it isn't
   already the loaded schedule**; while working through one ToO file,
   cycle N+1 skips the reload entirely. The row count the scan just
   computed is handed to `updateCurrentObs(..., n_remaining=...)` so it
   doesn't re-query the file either. The full ranked list is dumped to
   `~/data/Valid_ToO_Observations_Ranked.csv` for realtime reference.

## 2. Survey schedule (fallback)

If no ToO row survives, the survey file is loaded and
`schedule.getTopRankedObs(obstime_mjd, allowed_cameras=...)` picks the row:

- `getRankedObs` applies the same window / observed / attempts cuts via
  pandas (`validStop >= now`, then `observed == 0`, `attempts < max`,
  then `validStart <= now`) and validates the dataframe.
- The camera observability cut is applied to the ranked list (rows with no
  `camera` column count as `winter`).
- **Note:** the survey path does *not* re-sort — rows keep the schedule
  file's order (survey files are generated pre-sorted; the "Valid
  Observations Ranked by validStop" log lines reflect that file order).
  The top ranked observation is simply the first surviving row.
- The survey path still runs `updateCurrentObs` in full-query mode
  (`n_remaining=None`): when `currentObs` is None, `end_of_schedule`
  depends on whether rows could still become valid **later** tonight
  (`remaining_observable_entries`), which only the query can answer.

## 3. After dispatch: attempts vs. observed

`do_currentObs` executes `currentObs`. Two separate counters control
whether a row can be picked again:

- **`attempts`** is incremented when a row is tried (`log_attempt`, via
  `_log_schedule_write` — see §4). A row is skipped once
  `attempts >= max_observation_attempts`, so a failing target can't wedge
  the loop — but only until the nightly reset (§1 step 1) hands
  unobserved rows their attempts back the next night.
- **`observed`** is set to 1 (`log_observation`) only when every exposure
  of the row fully completed — any failed exposure leaves `observed = 0`
  so the row is retried (up to the attempts cap).

Both cuts are applied identically in the ToO and survey paths, so a row
drops out of ranking as soon as it is either done or out of attempts.

## 4. Caching & per-cycle cost

The observing loop re-runs the whole selection before **every**
observation, so the preamble cost is paid per target. Where the time goes
and what keeps it small:

- **Parsed-file cache** (`_get_too_df`): each ToO file is `SELECT *`'d and
  schema-validated once, then served from memory. The cache key is the
  file's `(mtime, size)`, so a hand-edited file or a freshly dropped one
  is picked up on the next scan with no restart. Schema-invalid files are
  cached as invalid (and skipped silently) until they change on disk;
  transient read errors (e.g. sqlite locked mid-write) are not cached and
  retry next scan.
- **Our own writes don't invalidate the cache.**
  `roboOperator._log_schedule_write` wraps `log_attempt` /
  `log_observation`: it verifies the cached parse still matches the file
  on disk, does the SQL write, applies the identical change to the cached
  dataframe in memory, and re-stamps the cache entry. (Before this, our
  own attempt-logging bumped the mtime and forced a ~2.5 s re-parse of
  the active file on every cycle.) If the pre-write stamp doesn't match —
  someone else edited the file — the write still lands but the cache is
  left stale so the next scan re-parses from disk. The nightly attempts
  reset (§1 step 1) writes directly and deliberately invalidates, once
  per night.
- **No redundant reloads.** Dispatch skips `loadSchedule` when the chosen
  file is already the active schedule, and passes `n_remaining` to
  `updateCurrentObs` so it skips its own re-query. Together with the
  cache this means the steady-state cycle (same ToO file as last time)
  does **zero** sqlite reads of the active file.
- **Schema validation is compiled once.** `wintertoo_validate` builds its
  jsonschema validator at import time and serializes the whole dataframe
  in one pass (~40× faster than the old per-row
  `jsonschema.validate` calls). A 79-row file validates in a few ms, so
  even a genuine re-parse is cheap.
- **Log volume:** `getRankedObs` logs only the top 5 ranked rows (one log
  call) — the full ranking lives in
  `~/data/Valid_ToO_Observations_Ranked.csv`.

What still runs every cycle: the glob, the per-file cuts on the cached
dataframes, one astropy AltAz frame + ephemeris body computation per scan,
and the ranked-CSV write. (History: before 2026-08 the same active file
was read and row-by-row-validated three times per cycle — scan, reload,
re-query — costing ~9 s per observation.)
