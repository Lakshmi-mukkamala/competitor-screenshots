"""Command-line entry point. Activate the project Conda environment first."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime

from competitor_screenshots.config import ROOT, load_catalog, load_settings, select_targets
from competitor_screenshots.environment import configure_environment


def main():
    parser = argparse.ArgumentParser(description='Python Playwright full-page competitor screenshots. Settings: .env')
    parser.add_argument('--list', action='store_true', help='List matching pages without opening a browser')
    parser.add_argument('--category', help='Flowers, Plants, or Greetz NL')
    parser.add_argument('--competitor', help='Exact competitor ID or name')
    parser.add_argument('--page', choices=['all', 'homepage', 'flowers-and-plants'], default='all')
    parser.add_argument('--output', help='Override SCREENSHOT_OUTPUT_DIR from .env')
    parser.add_argument('--consent', choices=['accept', 'reject'], help='Override COOKIE_CONSENT from .env')
    parser.add_argument('--headed', action='store_true', help='Display the browser')
    parser.add_argument('--manual', action='store_true', help='Display browser and pause for manual popup handling')
    parser.add_argument('--install-browser', action='store_true', help='Install Chromium inside the active Conda environment')
    parser.add_argument('--check-env', action='store_true', help='Print and verify environment/browser paths')
    args = parser.parse_args()
    if args.list:
        targets = select_targets(load_catalog(), args.category, args.competitor, args.page)
        for target in targets:
            print(f'{target["category"]:10}  {target["id"]:20}  {target["page"]:18}  {target["url"]}')
        print(f'{len(targets)} pages')
        return 0
    prefix, browser_path = configure_environment()
    if args.install_browser:
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
    from playwright.sync_api import sync_playwright
    if args.install_browser or args.check_env:
        with sync_playwright() as playwright:
            executable = Path(playwright.chromium.executable_path)
            print(json.dumps({'python': sys.executable, 'condaPrefix': str(prefix), 'browserCache': str(browser_path),
                              'chromium': str(executable), 'chromiumInstalled': executable.exists()}, indent=2))
            if not executable.exists():
                raise RuntimeError('Chromium is missing. Run: python capture.py --install-browser')
        return 0
    if args.manual and not sys.stdin.isatty():
        raise ValueError('--manual requires an interactive terminal.')
    settings = load_settings(args.output, args.consent)
    targets = select_targets(load_catalog(), args.category, args.competitor, args.page)
    config = json.loads((ROOT / 'config/popups.json').read_text(encoding='utf-8'))
    from competitor_screenshots.capture import capture_target, now
    from competitor_screenshots.report import write_report, prepare_daily_report, replace_result
    output_dir = Path(settings['output'])
    run_dir = output_dir / 'reports' / datetime.now().date().isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)
    report = prepare_daily_report(run_dir, targets, now())
    current_results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not (args.headed or args.manual))
        try:
            write_report(run_dir, report)
            for index, target in enumerate(targets, 1):
                print(f'[{index}/{len(targets)}] {target["category"]} / {target["name"]} / {target["page"]}', flush=True)
                result = capture_target(browser, target, settings, config, output_dir, args.manual)
                # Report image links are relative to the daily report directory.
                for key in ('screenshot', 'diagnostic'):
                    if key in result:
                        result[key] = Path(os.path.relpath(output_dir / result[key], run_dir)).as_posix()
                result.update(browser=browser.version, settings=settings)
                current_results.append(result)
                replace_result(report, result)
                report['lastRun']['completedCount'] = len(current_results)
                write_report(run_dir, report)
                print(f'  {result["status"]}: {result.get("error", " ".join(result["warnings"]))}', flush=True)
            report['completedAt'] = now()
            report['lastRun']['completedAt'] = report['completedAt']
            write_report(run_dir, report)
        finally:
            browser.close()
    print(f'Report: {run_dir / "README.md"}')
    statuses = {r['status'] for r in current_results}
    return 1 if 'failed' in statuses else 2 if statuses & {'blocked', 'needs-review'} else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('Capture interrupted. Completed-page reports remain in the output folder.', file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
