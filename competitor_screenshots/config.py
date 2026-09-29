import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = ('Flowers', 'Plants', 'Greetz NL')


def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


def load_catalog():
    catalog = json.loads((ROOT / 'config/competitors.json').read_text(encoding='utf-8'))
    ids = set()
    from urllib.parse import urlparse
    for item in catalog:
        if (item['category'] not in CATEGORIES or not item['name']
                or not re.fullmatch(r'[a-z0-9-]+', item['id']) or item['id'] in ids):
            raise ValueError(f'Invalid competitor: {item}')
        ids.add(item['id'])
        for url in (item['url'], item.get('flowerUrl')):
            if url and (urlparse(url).scheme != 'https' or not urlparse(url).netloc):
                raise ValueError(f'Invalid HTTPS URL: {url}')
    return catalog


def select_targets(catalog, category=None, competitor=None, page='all'):
    if category and category.lower() not in [c.lower() for c in CATEGORIES]:
        raise ValueError(f'Unknown category. Choose: {", ".join(CATEGORIES)}')
    targets = []
    for item in catalog:
        if category and item['category'].lower() != category.lower():
            continue
        if competitor and competitor.lower() not in (item['id'], item['name'].lower()):
            continue
        for kind, url in [('homepage', item['url']), ('flowers-and-plants', item.get('flowerUrl'))]:
            if url and page in ('all', kind):
                targets.append({**item, 'page': kind, 'url': url})
    if not targets:
        raise ValueError('No matching pages. Use --list to see competitor IDs.')
    return targets


def load_settings(output=None, consent=None, env_file=None):
    from dotenv import dotenv_values
    values = {**dotenv_values(env_file or ROOT / '.env'), **os.environ}

    def integer(key, default, low, high):
        value = int(values.get(key, default))
        if not low <= value <= high:
            raise ValueError(f'{key} must be between {low} and {high}.')
        return value

    output_path = Path(output or values.get('SCREENSHOT_OUTPUT_DIR') or './screenshots').expanduser()
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    choice = consent or values.get('COOKIE_CONSENT', 'accept')
    if choice not in ('accept', 'reject'):
        raise ValueError('COOKIE_CONSENT must be accept or reject.')
    return {
        'cookie_recordings_dir': values.get('COOKIE_RECORDINGS_DIR', 'G:/Shared drives/Arena Competitor Comparison/Running Process/Cookies'),
        'output': str(output_path.resolve()), 'consent': choice,
        'viewport': {'width': integer('VIEWPORT_WIDTH', 1440, 320, 3840), 'height': integer('VIEWPORT_HEIGHT', 1000, 320, 2160)},
        'settle': integer('SETTLE_MS', 2000, 0, 30000),
        'scroll_delay': integer('SCROLL_DELAY_MS', 500, 50, 5000),
        'max_scrolls': integer('MAX_SCROLLS', 100, 1, 500),
        'timeout': integer('TIMEOUT_MS', 45000, 1000, 180000),
    }
