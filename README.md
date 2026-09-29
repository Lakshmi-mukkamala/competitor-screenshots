# Competitor screenshots — Python Playwright

Cookie recording integration and the automation launcher are documented in [automation/README.md](automation/README.md). All 44 supplied cookie filenames are mapped in `config/cookie-recordings.json`; files are loaded from the configured shared-drive path at capture time.

Capture full-page competitor websites after accepting cookie prompts, dismissing recognised popups, and scrolling to load content. All runtime packages are defined in [environment.yml](environment.yml) and installed in a dedicated Conda environment.

| Category | Competitors | Pages |
| --- | ---: | ---: |
| Flowers | 13 | 16 |
| Plants | 9 | 9 |
| Greetz NL | 7 | 7 |
| **Total** | **29** | **32** |

All supplied URLs are in [config/competitors.json](config/competitors.json). Moonpig, Funky Pigeon, and M&S each include their homepage and flower landing page.

## 1. Create the environment (first use)

Open **Anaconda PowerShell Prompt**, go to this repository, and run:

```powershell
cd C:/Users/LakshmiMukkamala/competitor-screenshots
conda env create --prefix ./.conda-env --file environment.yml
conda activate ./.conda-env
python capture.py --install-browser
python capture.py --check-env
```

**The environment has already been created on this machine.** For everyday use, start with activation in step 3. Use the creation command only for a fresh checkout or after removing the environment.

Python, Playwright, python-dotenv, and their dependencies live under `.conda-env/`. Chromium is installed under `.conda-env/browsers/`. The runner refuses to capture from Conda base, a different Python interpreter, or user-site packages. There is no Node, npm, pnpm, or separate requirements.txt setup.

`environment.yml` is the single dependency definition. Conda resolves its supporting libraries; it is not an exact cross-platform lockfile. `.env` contains capture settings, not package dependencies.

If `conda` is unavailable in an ordinary terminal, use Anaconda PowerShell Prompt. On another machine, install Miniconda/Anaconda first and change the `cd` path. The Python commands also work from an activated environment on macOS/Linux; Linux may additionally need Chromium's OS libraries.

## 2. Choose where screenshots go

A working `.env` file is included locally. On a fresh clone, create it once:

```powershell
Copy-Item .env.example .env
```

Edit this line in `.env` to choose any writable destination:

```dotenv
SCREENSHOT_OUTPUT_DIR="D:/Research/Competitor Screenshots"
```

The default is `./screenshots`. Relative paths resolve from the repository folder. Use forward slashes on Windows and quote paths containing spaces. Output uses one folder per local calendar date, such as `2026-09-10`. Same-day runs replace only the selected pages and merge their results into the daily report. Other pages and earlier dates are preserved. Run batches sequentially when using the same output folder.

| Setting | Default | Purpose |
| --- | --- | --- |
| SCREENSHOT_OUTPUT_DIR | ./screenshots | Root folder for images and reports |
| COOKIE_CONSENT | accept | Accept recognised cookie prompts; optionally use reject |
| VIEWPORT_WIDTH | 1440 | Browser width in CSS pixels |
| VIEWPORT_HEIGHT | 1000 | Browser viewport height; PNG captures the full document |
| SETTLE_MS | 2000 | Wait after navigation and returning to the top |
| SCROLL_DELAY_MS | 500 | Wait between scroll steps |
| MAX_SCROLLS | 100 | Bound scrolling on long/infinite pages |
| TIMEOUT_MS | 45000 | Navigation and screenshot timeout |

Settings precedence: command-line overrides, then existing shell environment variables, then `.env`, then defaults. `.env` is ignored by Git; `.env.example` is the shareable template. An output folder inside the repository other than `screenshots/` should also be added to `.gitignore`.

## 3. Run captures

Activate the environment in each new terminal:

```powershell
conda activate ./.conda-env

# List all 32 target pages
python capture.py --list

# Capture all pages
python capture.py

# Capture a category
python capture.py --category "Flowers"
python capture.py --category "Plants"
python capture.py --category "Greetz NL"

# Capture a single competitor or homepage
python capture.py --competitor moonpig
python capture.py --competitor moonpig --page homepage

# One-run output override
python capture.py --category "Plants" --output "D:/Research/Plant captures"

# Display the browser and pause for manual popup handling
python capture.py --competitor bloom-and-wild --manual

# Display the browser without pausing
python capture.py --competitor interflora --headed

# See all options
python capture.py --help

# Finish the session
conda deactivate
```

Use `--manual` in an interactive terminal: handle the popup in the displayed browser, then press Enter in the terminal. A remaining detected popup prompts for a final check after scrolling.

## 4. Review the results

Open the dated run folder shown at the end of the command:

```text
<your-output-folder>/2026-09-10/
  README.md
  manifest.json
  flowers/moonpig/homepage.png
  flowers/moonpig/flowers-and-plants.png
  plants/patch-plants/homepage.png
  greetz-nl/kaartje2go/homepage.png
```

| Status | Meaning |
| --- | --- |
| captured | Full-page PNG saved; automated popup checks passed. Visually inspect it. |
| needs-review | PNG saved without a detected popup, but loading or scrolling warnings remain. |
| blocked | Popup or access challenge remains. Only a clearly named `.diagnostic.png` is saved. |
| failed | Navigation/capture error; a diagnostic image is saved when possible. |

Exit codes: `0` = captured without warnings; `1` = failure/configuration error; `2` = blocked or needs-review; `130` = interrupted. The report is updated after each completed page.

**Popup checks are conservative, but no generic script can guarantee detection of every future site design.** The runner clicks actual controls and checks before and after screenshot rendering. It does not hide overlays with CSS or label detected popup images as clean. Always visually inspect the entire image before using it. Use manual mode or site rules for anything missed.

## 5. Maintain and test

```powershell
conda activate ./.conda-env
python -m unittest discover -s tests -v
```

Tests cover all catalog counts, separate output folders, cookie choice, Dutch iframe controls, delayed popups, full-page lazy content, persistent-popup rejection, HTTP failures, and scroll limits. GitHub Actions runs the Python tests against a local fixture website.

To update dependencies, edit `environment.yml`, then:

```powershell
conda deactivate
conda env update --prefix ./.conda-env --file environment.yml --prune
conda activate ./.conda-env
python capture.py --install-browser
python capture.py --check-env
python -m unittest discover -s tests -v
```

Do not install packages into base or use `pip install --user`. Keep dependency changes in `environment.yml`. Existing browsers in the shared user cache from the earlier JavaScript setup are not used; shared caches are not automatically deleted.

## Project files

| File/folder | Purpose |
| --- | --- |
| environment.yml | Single package/environment definition |
| .env / .env.example | Local settings / template |
| capture.py | Python command-line entry point |
| competitor_screenshots/ | Capture, popup, environment, config, and report code |
| config/ | Competitor URLs and popup rules |
| tests/ | Local automated tests |
| scripts/setup.ps1 | Optional browser setup after Conda activation |
| .conda-env/ | Ignored isolated runtime and browsers |
| screenshots/ | Default ignored output folder |

Read [PROCESS.md](PROCESS.md) for the full operating process, troubleshooting, and popup-rule examples. See [CONTRIBUTING.md](CONTRIBUTING.md) for maintenance.

Implementation references: [Conda environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html), [Python Playwright screenshots](https://playwright.dev/python/docs/screenshots), and [browser installation](https://playwright.dev/python/docs/browsers).

