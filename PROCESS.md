# Screenshot collection process

This document explains the complete Python Playwright workflow. [README.md](README.md) contains the quick-start commands.

## 1. Prepare the isolated runtime

The single dependency definition is `environment.yml`. It creates Python 3.12, pip, Playwright 1.58.0, python-dotenv 1.2.3, and their supporting packages in a dedicated Conda environment. `typing_extensions` is explicitly included so installation cannot accidentally rely on an existing user-site copy.

Use Anaconda PowerShell Prompt. From the repository, create the environment with `conda env create --prefix ./.conda-env --file environment.yml`, then activate it with `conda activate ./.conda-env`. On the existing machine, the environment is already created.

Run `python capture.py --install-browser` once and after Playwright updates. The runner sets Playwright's browser path to the active environment's `browsers` directory before importing the browser API. Playwright's bundled Node driver is an internal part of its Python package; you do not install Node separately.

Run `python capture.py --check-env`. The printed Python and Chromium paths should be under `.conda-env`. The environment disables Python user-site packages, and the runner checks where its imported dependencies came from. It refuses the base environment. Conda may maintain its own download/notice metadata outside the project; this does not install project packages into base.

## 2. Configure the output and capture settings

Open the local `.env` in a text editor. Set `SCREENSHOT_OUTPUT_DIR` to a folder you can write to. For example:

```dotenv
SCREENSHOT_OUTPUT_DIR="D:/Research/Competitor Screenshots"
COOKIE_CONSENT=accept
VIEWPORT_WIDTH=1440
VIEWPORT_HEIGHT=1000
SETTLE_MS=2000
SCROLL_DELAY_MS=500
MAX_SCROLLS=100
TIMEOUT_MS=45000
```

No screenshot is sent elsewhere automatically. The output location may be outside this repository; all images and reports for the run go there together. Keep the manifest and report with the images when sharing them.

Use `--output` or `--consent` for one-run overrides. Existing shell environment variables override values in `.env`. Other settings are validated at startup, and invalid numbers stop the run with an error.

## 3. Select competitors

The catalog contains 29 competitors and 32 pages: 13 Flowers competitors (16 pages), 9 Plants, and 7 Greetz NL. The three additional flower landing pages belong to Moonpig, Funky Pigeon, and M&S.

Run `python capture.py --list` to see IDs and URLs. All targets come from `config/competitors.json`. Each entry has a stable ID, name, category, and homepage URL; `flowerUrl` adds the optional second target.

Run all pages with `python capture.py`. To narrow a run, use `--category "Plants"`, `--competitor moonpig`, or `--page homepage`. Filters combine. Begin with one competitor when validating a new machine or changed popup rule.

## 4. Navigate and handle consent

Each target opens in a fresh browser context. UK categories use the English UK locale and London timezone; Greetz NL uses Dutch and Amsterdam. These settings do not change your network location.

After the initial document loads, the runner waits for dynamic content. It checks actual cookie buttons in the main page and iframes. It tries configured selectors and English/Dutch button labels.

The default accepts recognised cookie prompts. Setting `COOKIE_CONSENT=reject` instead rejects recognised prompts without falling back to acceptance. Actions are recorded in the manifest. The runner does not enter account details, submit subscriptions, make purchases, or solve CAPTCHAs.

## 5. Dismiss popups and scroll

The runner clicks recognised close buttons and checks again during scrolling. Common modal, newsletter, and cookie controls are supported. Pages are scrolled in increments of roughly 80% of the viewport height with a delay between steps.

Scrolling ends after several stable bottom/height checks or at the configured maximum. A limit warning means content may be incomplete or scrolling may still be obstructed. Increase `MAX_SCROLLS` for a long page, and `SCROLL_DELAY_MS` or `SETTLE_MS` for slow lazy loading.

The runner returns to the top, waits, checks fonts, and performs another popup pass. It does not expand every accordion, rotate every carousel, or navigate to other pages beyond the catalog targets.

## 6. Apply the final screenshot check

The runner checks for visible semantic dialogs, known consent panels, common popup containers, and large fixed overlays. It scans visible iframe content too.

If a popup or access challenge remains, the result is `blocked`. A timestamped `.diagnostic.png` may be saved, but no ordinary screenshot is created for that attempt. After rendering a candidate full-page screenshot, the page is checked again before the image is committed as a normal capture.

The checks intentionally favour reporting uncertain overlays for review. They cannot detect every custom implementation or eliminate the possibility of a very late popup. Visually review all final images; use manual mode for unusual sites.

## 7. Use manual mode when needed

Run, for example:

```powershell
python capture.py --competitor bloom-and-wild --manual
```

The browser opens and the terminal pauses. Dismiss the consent, promotion, or location popup in the browser, then press Enter in the terminal. The runner scrolls and performs its final check. If an overlay is still detected, it pauses once more for you to close it. If it remains after that, the result is blocked.

Manual mode requires an interactive terminal. Do not use it from an unattended job. A persistent access challenge should be recorded as blocked rather than treated as a completed homepage capture.

## 8. Maintain popup selectors

Edit `config/popups.json`. Keys under `sites` are competitor IDs. Site selectors run before global selectors:

```json
{
  "global": {
    "acceptSelectors": [],
    "rejectSelectors": [],
    "closeSelectors": [],
    "blockerSelectors": []
  },
  "sites": {
    "moonpig": {
      "closeSelectors": ["button[data-testid='replace-with-inspected-close-button']"],
      "blockerSelectors": ["#replace-with-inspected-popup-container"]
    }
  }
}
```

These are illustrative placeholders, not verified Moonpig selectors. Preserve the existing global configuration and add only selectors inspected on the real site. `blockerSelectors` identifies remaining visible popup containers; it does not click them. Never point close selectors at generic shopping or submit buttons.

After changing a rule, run the tests, capture the relevant competitor, inspect the image, and check the action log. Do not hide content with CSS to make a screenshot look complete.

## 9. Inspect output and retry

Images live directly under a competitor folder in the configured output root, for example `interflora/interflora_2026-09-29_14-30-05-123456_homepage.png`. The timestamp is the attempt's local start date and time, including microseconds to distinguish retries. Competitor names are lowercase with punctuation and spaces converted to hyphens. Page type distinguishes homepages from flower pages. Daily reports live in `reports/YYYY-MM-DD/`, using the computer's local date when the run starts. The README groups results by category and links to each image. Its manifest retains detailed timestamps, settings and browser version per page, actions, warnings, and detected blockers. Image paths in the manifest are relative to its report folder.

| Status | Review action |
| --- | --- |
| captured | Inspect the image from header to footer. |
| needs-review | Inspect loading/scroll warnings and retry if needed. |
| blocked | Inspect diagnostic evidence, fix popup handling, or use manual mode. |
| failed | Read the error and diagnostic; retry the affected target. |

Check the hero, product images, page body, and footer. Look for covered content, blank sections, unexpected redirects, or access challenges. Small floating controls may remain as part of the website.

Retries preserve earlier images and create new timestamped files. The daily report replaces the selected page's entry with its latest result while keeping other competitors' entries. A blocked retry links only to that attempt's diagnostic, never to a previous clean capture. Reports update after each completed page and include progress for the latest run. If interrupted, retry the affected pages; unfinished entries can still show an earlier attempt. Existing output from the old date/category layout is not moved. Run batches sequentially against the same output folder to avoid competing writes.

Exit codes are 0 for no warnings, 1 for a failure, 2 for blocked/review results without failures, and 130 for interruption.

## 10. Troubleshoot

| Symptom | Action |
| --- | --- |
| Conda command is missing | Open Anaconda PowerShell Prompt. |
| Environment already exists | Activate it; use the README's update commands when dependencies change. |
| Wrong Python or base-environment error | Activate `./.conda-env`; check `python -c "import sys; print(sys.executable)"`. |
| User-site packages enabled | Update from environment.yml, deactivate, and reactivate so PYTHONNOUSERSITE takes effect. |
| Chromium missing | Run `python capture.py --install-browser` after activation. |
| Output permission denied | Choose a writable folder in .env or pass --output. |
| Cookie or popup still visible | Use --manual or add precise selectors; do not use diagnostics as final images. |
| Scroll limit or missing images | Increase the relevant timing/scroll settings and rerun. |
| Navigation/network error | Verify the site opens normally, then retry the affected page. |
| Setting seems ignored | Check for an overriding shell environment variable or CLI flag. |

## 11. Test and maintain

Run `python -m unittest discover -s tests -v` inside the activated environment. Tests use a local web server and cover popup dismissal, blocked-popup behaviour, lazy content, image dimensions, separate output paths, and failure evidence. CI uses the same environment file and tests.

When changing dependencies, edit only `environment.yml`, update the Conda environment, reactivate it, reinstall the matching browser, and rerun tests. Keep viewport, consent choice, locale, and browser version consistent when comparing different capture dates. Website experiments and personalisation can still affect results.

Deactivate with `conda deactivate` when finished. Source code and configuration belong in Git; the environment, .env, browser binaries, and generated screenshots do not.

