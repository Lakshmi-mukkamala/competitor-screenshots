"""Keep Python packages and browser binaries in the activated Conda environment."""
import os
from pathlib import Path
import sys
import site


def configure_environment():
    prefix = Path(sys.prefix).resolve()
    active = os.environ.get('CONDA_PREFIX')
    if (not active or Path(active).resolve() != prefix
            or os.environ.get('CONDA_DEFAULT_ENV') == 'base'
            or os.environ.get('COMPETITOR_SCREENSHOTS_ENV') != '1'):
        raise RuntimeError('Activate the project Conda environment first: conda activate ./.conda-env. See README.md.')
    browser_path = prefix / 'browsers'
    if site.ENABLE_USER_SITE:
        raise RuntimeError('User-site packages are enabled. Update and reactivate the project environment so PYTHONNOUSERSITE=1 takes effect.')
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browser_path)
    # Prevent an accidentally inherited user-site package from supplying Playwright.
    import playwright
    import dotenv
    import pyee
    import greenlet
    import typing_extensions
    for module in (playwright, dotenv, pyee, greenlet, typing_extensions):
        if not Path(module.__file__).resolve().is_relative_to(prefix):
            raise RuntimeError(f'{module.__name__} was loaded outside the Conda environment.')
    return prefix, browser_path
