# Target Ranking & Selection

How the robotic operator decides which observation to dispatch next.
Entry point: `roboOperator.load_best_observing_target(obstime_mjd)`, called
from `checkWhatToDo()` each time the observing loop needs a target. ToO
schedules always win over the survey: the survey is only consulted when no
ToO row survives the cuts.

## 1. ToO schedules (checked first)

`load_best_observing_target` globs `*.db` in the ToO schedule directory and
builds one combined candidate table:

1. **Parse (cached).** Each file is read through `_get_too_df`, which
   caches the parsed + schema-validated dataframe and only re-reads a file
   when its mtime changes. (Our own `log_observation` / `log_attempt`
   writes bump the mtime, so `observed`/`attempts` values are always
   fresh.)
2. **Per-file cuts**, applied in order — a file that ends up empty is
   logged with the reason and skipped:
   - **Window / bookkeeping:** `validStart <= now <= validStop`,
     `observed == 0`, `attempts < max_observation_attempts` (config,
     default 2).
   - **Camera observability:** the row's `camera` (missing column →
     `winter`) must be in config `active_cameras` AND not on a locked-out
     M3 port. This is what keeps the scheduler from churning on e.g.
     spring rows after a port 2 lockout.
   - **Elevation & airmass:** current airmass `< maxAirmass` (row value,
     or derived from telescope `min_alt` if the column is missing), and
     current altitude within telescope `[min_alt, max_alt]`.
   - **Ephemeris separation:** target not within the configured minimum
     distance of any body in `config['ephem']['min_target_separation']`
     (body positions computed once per scan, not per file).
3. **Ranking.** Survivors from all files are concatenated and sorted in a
   single call:

   ```python
   full_df.sort_values(by=["priority", "validStop"], ascending=[False, True])
   ```

   i.e. **highest priority first; ties broken by earliest deadline
   (validStop)**. Rows without a priority column get priority 0.
4. **Dispatch.** The top row wins: its origin file is loaded as the active
   schedule and the row becomes `currentObs`. The full ranked list is also
   dumped to `~/data/Valid_ToO_Observations_Ranked.csv` for realtime
   reference.

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

## 3. After dispatch: attempts vs. observed

`do_currentObs` executes `currentObs`. Two separate counters control
whether a row can be picked again:

- **`attempts`** is incremented when a row is tried (`log_attempt`). A row
  is skipped once `attempts >= max_observation_attempts`, so a failing
  target can't wedge the loop.
- **`observed`** is set to 1 (`log_observation`) only when every exposure
  of the row fully completed — any failed exposure leaves `observed = 0`
  so the row is retried (up to the attempts cap).

Both cuts are applied identically in the ToO and survey paths, so a row
drops out of ranking as soon as it is either done or out of attempts.
