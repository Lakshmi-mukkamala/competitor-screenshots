from datetime import datetime, timezone
from pathlib import Path
import re

from .config import slug
from .popups import dismiss_popups, find_blockers, site_rules
from .recordings import load_recording, replay_clicks


def now():
    return datetime.now(timezone.utc).isoformat()


def scroll_page(page, settings, on_step=lambda _: None):
    stable, last_height = 0, 0
    for step in range(settings['max_scrolls']):
        on_step(step)
        state = page.evaluate('''() => {
          const root = document.scrollingElement || document.documentElement;
          window.scrollBy(0, Math.max(250, innerHeight * .8));
          return {height: root.scrollHeight, bottom: root.scrollTop + innerHeight >= root.scrollHeight - 3};
        }''')
        page.wait_for_timeout(settings['scroll_delay'])
        stable = stable + 1 if state['bottom'] and state['height'] == last_height else 0
        last_height = state['height']
        if stable >= 3:
            return {'reachedBottom': True, 'steps': step + 1, 'height': last_height}
    return {'reachedBottom': False, 'steps': settings['max_scrolls'], 'height': last_height}


def capture_target(browser, target, settings, config, run_dir, manual=False):
    record = dict(competitor=target['name'], id=target['id'], category=target['category'],
                  page=target['page'], requestedUrl=target['url'], capturedAt=now(),
                  status='failed', actions=[], warnings=[])
    folder = Path(slug(target['category'])) / target['id']
    (run_dir / folder).mkdir(parents=True, exist_ok=True)
    # A same-day retry replaces this page's previous output, including failures.
    for suffix in ('.png', '.diagnostic.png'):
        (run_dir / folder / (target['page'] + suffix)).unlink(missing_ok=True)
    nl = target['category'] == 'Greetz NL'
    context = browser.new_context(viewport=settings['viewport'], device_scale_factor=1,
                                  locale='nl-NL' if nl else 'en-GB',
                                  timezone_id='Europe/Amsterdam' if nl else 'Europe/London',
                                  color_scheme='light', reduced_motion='reduce', accept_downloads=False)
    page = context.new_page()
    page.set_default_timeout(5000)
    page.on('dialog', lambda dialog: dialog.dismiss())
    rules = site_rules(config, target['id'])
    recorded_rules, recorded_clicks = load_recording(target, settings, record['warnings'])
    for key, selectors in recorded_rules.items():
        rules[key] = selectors + rules.get(key, [])

    def dismiss():
        replay_clicks(page, recorded_clicks, record['actions'])
        dismiss_popups(page, rules, settings['consent'], record['actions'])

    def diagnostic():
        try:
            filename = folder / (target['page'] + '.diagnostic.png')
            page.screenshot(path=str(run_dir / filename), full_page=True, timeout=10000)
            record['diagnostic'] = filename.as_posix()
        except Exception:
            pass

    try:
        response = page.goto(target['url'], wait_until='domcontentloaded', timeout=settings['timeout'])
        record['httpStatus'] = response.status if response else None
        if response and response.status >= 400:
            raise RuntimeError(f'HTTP {response.status}')
        page.wait_for_timeout(settings['settle'])
        dismiss()
        if manual:
            input(f'Handle popups for {target["name"]}, then press Enter here to scroll: ')
        record['scroll'] = scroll_page(page, settings, lambda step: dismiss() if step % 5 == 0 else None)
        if not record['scroll']['reachedBottom']:
            record['warnings'].append('Scroll limit reached; the page may be incomplete or scrolling blocked.')
        page.evaluate('window.scrollTo(0, 0)')
        page.wait_for_timeout(settings['settle'])
        dismiss()
        page.evaluate('() => Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 3000))])')
        # A quiet window catches many delayed exit/newsletter prompts.
        page.wait_for_timeout(1000)
        dismiss()
        blockers = find_blockers(page, rules)
        if manual and blockers:
            input('A popup still appears to be visible. Close it in the browser, then press Enter for the final check: ')
            dismiss()
            blockers = find_blockers(page, rules)
        record['title'] = page.title()
        record['finalUrl'] = page.url
        quality = page.evaluate('''() => ({
          text: (document.body?.innerText || '').slice(0, 5000),
          incompleteImages: [...document.images].filter(i => i.getBoundingClientRect().width > 0 && (!i.complete || !i.naturalWidth)).length
        })''')
        challenge = re.search(r"verify (?:you are|you're) human|checking your browser|access denied|just a moment|captcha|pardon our interruption", record['title'] + '\n' + quality['text'], re.I)
        if blockers or challenge:
            record['status'] = 'blocked'
            record['blockers'] = blockers
            record['warnings'].append('A popup or access challenge remains. No clean screenshot was saved; use --manual or update popup rules.')
            diagnostic()
            return record
        if quality['incompleteImages']:
            record['warnings'].append(f'{quality["incompleteImages"]} images are not fully loaded.')
        if len(quality['text'].strip()) < 100:
            record['warnings'].append('Very little page text was loaded.')
        image = page.screenshot(full_page=True, animations='disabled', timeout=settings['timeout'])
        # Recheck after rendering before committing an image as a regular capture.
        blockers = find_blockers(page, rules)
        if blockers:
            record['status'] = 'blocked'
            record['blockers'] = blockers
            record['warnings'].append('An overlay appeared during capture. Only diagnostic evidence was saved.')
            diagnostic()
        else:
            filename = folder / (target['page'] + '.png')
            (run_dir / filename).write_bytes(image)
            record['screenshot'] = filename.as_posix()
            record['status'] = 'needs-review' if record['warnings'] else 'captured'
    except Exception as exc:
        record['error'] = str(exc)
        record['finalUrl'] = page.url
        diagnostic()
    finally:
        context.close()
    return record
