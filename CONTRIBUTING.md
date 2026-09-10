# Contributing

This project uses Python Playwright in the Conda environment defined by `environment.yml`. Activate `./.conda-env` before running capture or tests. Add dependencies only to that file; do not install into base or use pip --user.

Competitors belong in `config/competitors.json`. IDs must be unique lowercase slugs, with categories Flowers, Plants, or Greetz NL. The optional flowerUrl adds a second page.

Inspect actual popup controls before adding site selectors in `config/popups.json`. Keep close selectors precise, preserve global rules, and use blockerSelectors for unusual overlays. Do not hide page content with CSS.

Run `python -m unittest discover -s tests -v` after code changes. For site-specific changes, also run the relevant live capture and visually inspect the full image and action log.

See [PROCESS.md](PROCESS.md) for the complete workflow. Do not commit environments, caches, credentials, local .env settings, or screenshot output.

