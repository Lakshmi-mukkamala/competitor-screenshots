"""Load selector rules or Chrome Recorder clicks from user-owned JSON files.

Recordings are data: navigation, scripts, typing, and other actions never run.
"""
import json
from pathlib import Path
from urllib.parse import urlsplit

from .config import ROOT


def recording_filename(target, mapping):
    host = (urlsplit(target['url']).hostname or '').removeprefix('www.')
    entry = mapping.get(host)
    if isinstance(entry, dict):
        return entry.get(target['page'])
    return entry


def parse_recording(data, consent):
    keys = ('acceptSelectors', 'rejectSelectors', 'closeSelectors', 'blockerSelectors')
    if isinstance(data, dict) and any(key in data for key in keys):
        rules = {key: data.get(key, []) for key in keys}
        if any(not isinstance(items, list) or any(not isinstance(s, str) for s in items)
               for items in rules.values()):
            raise ValueError('Selector rules must be arrays of strings')
        return rules, []
    if not isinstance(data, dict) or not isinstance(data.get('steps'), list):
        raise ValueError('Expected selector rules or a Chrome Recorder object with steps')
    # Unlabelled recordings are assumed to record accepting cookies. Never replay
    # them for reject mode unless their author explicitly labelled them reject.
    choice = data.get('consent', 'accept')
    if choice not in ('accept', 'reject'):
        raise ValueError('Recording consent must be accept or reject')
    if choice != consent:
        return {}, []
    clicks = []
    for step in data['steps']:
        if not isinstance(step, dict):
            raise ValueError('Each recorded step must be an object')
        if step.get('type') != 'click':
            continue
        alternatives = []
        for candidate in step.get('selectors', []):
            chain = [candidate] if isinstance(candidate, str) else candidate
            if not isinstance(chain, list) or any(not isinstance(s, str) for s in chain):
                raise ValueError('Invalid recorded selector')
            # Chained recorder selectors can represent shadow roots; only plain
            # selectors are supported here (Playwright CSS pierces open roots).
            if len(chain) != 1:
                continue
            selector = chain[0]
            if selector.startswith(('aria/', 'pierce/', 'text/')):
                if selector.startswith('pierce/'):
                    alternatives.append(selector[7:])
                continue
            alternatives.append('xpath=' + selector[6:] if selector.startswith('xpath/') else selector)
        if not alternatives:
            raise ValueError('Recorded click has no supported CSS or XPath selector')
        clicks.append(alternatives)
    if not clicks:
        raise ValueError('Recording contains no supported clicks')
    return {}, clicks


def load_recording(target, settings, warnings):
    mapping = json.loads((ROOT / 'config/cookie-recordings.json').read_text(encoding='utf-8'))
    filename = recording_filename(target, mapping['files'])
    if not filename:
        return {}, []
    directory = settings.get('cookie_recordings_dir')
    if not directory:
        return {}, []
    try:
        data = json.loads((Path(directory) / filename).read_text(encoding='utf-8-sig'))
        return parse_recording(data, settings['consent'])
    except (OSError, ValueError, TypeError) as exc:
        warnings.append(f'Cookie recording {filename} unavailable or unsupported ({type(exc).__name__}); using popup fallback.')
        return {}, []


def replay_clicks(page, clicks, actions):
    from playwright.sync_api import Error
    from .popups import click_visible
    # Consume a sequence once, resuming on later dismissal passes if a control
    # has not appeared yet. Alternatives for one step never cause extra clicks.
    while clicks:
        clicked = False
        for frame in page.frames:
            if frame.is_detached():
                continue
            for selector in clicks[0]:
                try:
                    clicked = click_visible(frame.locator(selector), f'recorded cookie click: {selector}', actions)
                except Error:
                    continue
                if clicked:
                    break
            if clicked:
                break
        if not clicked:
            return
        clicks.pop(0)
        page.wait_for_timeout(400)
