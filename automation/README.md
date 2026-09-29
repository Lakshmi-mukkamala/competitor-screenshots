# Screenshot automation

Run the existing capture process using the project's Conda Python:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\automation\run.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\automation\run.ps1 --competitor arena-flowers --headed
```

For Windows Task Scheduler, use `powershell.exe` and arguments `-NoProfile -ExecutionPolicy Bypass -File "C:\Users\LakshmiMukkamala\competitor-screenshots\automation\run.ps1"`. Choose a schedule and run as the Windows user with access to the shared drive. No scheduled task has been registered. Avoid overlapping runs. Exit codes are preserved from capture.py (0 success, 1 failure, 2 review needed).

## Cookie click files

The default folder is `G:\Shared drives\Arena Competitor Comparison\Running Process\Cookies`. Override it with `COOKIE_RECORDINGS_DIR` in `.env`; an empty value disables loading. `config/cookie-recordings.json` maps all 44 supplied filenames by hostname, with separate homepage and flowers-and-plants entries for Moonpig and Greetz. Filenames, including `Telefora`, are preserved exactly. The mapping does not add websites to the capture catalog: only targets in `config/competitors.json` are captured.

Files are read on the machine running captures, once per target. Missing, malformed, or unsupported files create report warnings and fall back to existing popup handling. The shared-drive files were not accessed during implementation, so their format and selectors remain unverified.

Supported JSON formats:

- Selector rules: an object containing arrays named `acceptSelectors`, `rejectSelectors`, `closeSelectors`, and/or `blockerSelectors`, as in `config/popups.json` site rules.
- Chrome Recorder: an object with a `steps` array. Only `click` steps replay, using single CSS, `pierce/` CSS, or `xpath/` selector alternatives. Navigation, typing, scripts, coordinates, frame paths, and other steps are ignored; selectors are searched across current frames. Multi-selector shadow chains and aria/text-only clicks are unsupported. Missing controls are retried during later popup passes.

Recorder files default to accept consent. Add a top-level `"consent": "reject"` only to recordings of rejecting cookies to enable them in reject mode. Existing generic consent and close rules still run. Only cookie/popup clicks should be included in recordings, because every recorded click is treated as a popup action. Arbitrary instructions in JSON are never executed.

Final blocker detection still decides whether a clean screenshot can be saved. Review diagnostics and action logs when selectors no longer match the website.
