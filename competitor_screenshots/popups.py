import re

COOKIE_NAMES = {
    'accept': re.compile(r'^(accept all(?: cookies)?|allow all(?: cookies)?|accept cookies|agree and continue|accept & continue|accept and continue|alle cookies accepteren|alles accepteren|accepteer alle cookies|accepteren|akkoord)$', re.I),
    'reject': re.compile(r'^(reject all(?: cookies)?|decline all(?: cookies)?|reject optional cookies|only necessary(?: cookies)?|necessary cookies only|alle cookies weigeren|alles weigeren|weigeren|alleen noodzakelijke cookies)$', re.I),
}
CLOSE_NAMES = re.compile(r'^(close|close dialog|close modal|close popup|dismiss|no thanks|no, thanks|not now|sluiten|nee bedankt|nee, bedankt|×|✕)$', re.I)
DIALOGS = '[role="dialog"], [aria-modal="true"], dialog[open], [class*="klaviyo-form"]'


def site_rules(config, competitor):
    local = config.get('sites', {}).get(competitor, {})
    return {key: local.get(key, []) + config.get('global', {}).get(key, [])
            for key in ('acceptSelectors', 'rejectSelectors', 'closeSelectors', 'blockerSelectors')}


def click_visible(locator, description, actions):
    from playwright.sync_api import Error
    for i in range(min(locator.count(), 12)):
        item = locator.nth(i)
        if not item.is_visible():
            continue
        try:
            item.click(timeout=1000, no_wait_after=True)
            actions.append(description)
            return True
        except Error:
            continue
    return False


def dismiss_popups(page, rules, consent, actions):
    from playwright.sync_api import Error
    for _ in range(4):
        clicked = False
        for frame in page.frames:
            if frame.is_detached():
                continue
            try:
                for selector in rules.get(f'{consent}Selectors', []):
                    clicked = click_visible(frame.locator(selector), f'{consent}: {selector}', actions) or clicked
                clicked = click_visible(frame.get_by_role('button', name=COOKIE_NAMES[consent]), f'{consent}: named cookie control', actions) or clicked
                for selector in rules.get('closeSelectors', []):
                    clicked = click_visible(frame.locator(selector), f'close: {selector}', actions) or clicked
                clicked = click_visible(frame.locator(DIALOGS).get_by_role('button', name=CLOSE_NAMES), 'close: named dialog control', actions) or clicked
            except Error:
                if not frame.is_detached():
                    raise
        if not clicked:
            break
        page.wait_for_timeout(400)


# Inspect both semantic dialogs and common non-semantic fixed overlays. This is
# deliberately conservative: false positives go to diagnostics, not clean output.
BLOCKERS_JS = r'''() => {
  const visible = e => {
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    if (r.width <= 0 || r.height <= 0 || r.right <= 0 || r.left >= innerWidth) return false;
    const emptyPlaceholder = !e.children.length && !e.textContent.trim() && s.pointerEvents === 'none'
      && ['rgba(0, 0, 0, 0)', 'transparent'].includes(s.backgroundColor)
      && s.backgroundImage === 'none' && s.boxShadow === 'none' && s.backdropFilter === 'none';
    if (emptyPlaceholder) return false;
    for (let parent = e; parent; parent = parent.parentElement) {
      const style = getComputedStyle(parent);
      if (style.visibility === 'hidden' || style.display === 'none' || Number(style.opacity) <= .01) return false;
      if (style.position === 'fixed' && (r.bottom <= 0 || r.top >= innerHeight)) return false;
    }
    return true;
  };
  const explicit = [...document.querySelectorAll('[role="dialog"], [aria-modal="true"], dialog[open], #onetrust-banner-sdk, #CybotCookiebotDialog')];
  const overlays = [...document.querySelectorAll('div, section, aside, form')].filter(e => {
    if (!visible(e)) return false;
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    const named = /cookie|consent|popup|pop-up|modal|newsletter|klaviyo|attentive/i.test(e.id + ' ' + e.className);
    const fixed = s.position === 'fixed';
    const sizable = r.width >= 180 && r.height >= 80;
    const large = r.width * r.height > innerWidth * innerHeight * .3 && r.height > innerHeight * .3;
    const controls = e.querySelector('button, input, [role="button"]');
    return sizable && ((named && (fixed || s.position === 'absolute') && controls) || (fixed && large && Number(s.zIndex) > 10));
  });
  return [...new Set([...explicit, ...overlays])].filter(visible).filter((e, i, all) =>
    !all.some(other => other !== e && other.contains(e))
  ).map(e => ({tag: e.tagName, id: e.id, text: (e.innerText || '').slice(0, 180)})).slice(0, 20);
}'''


def find_blockers(page, rules):
    blockers = []
    for frame in page.frames:
        if frame.is_detached():
            continue
        if frame != page.main_frame and not frame.frame_element().is_visible():
            continue
        for item in frame.evaluate(BLOCKERS_JS):
            blockers.append({**item, 'frame': frame.url})
        for selector in rules.get('blockerSelectors', []):
            locator = frame.locator(selector)
            if any(locator.nth(i).is_visible() for i in range(min(locator.count(), 20))):
                blockers.append({'selector': selector, 'frame': frame.url})
    return blockers
