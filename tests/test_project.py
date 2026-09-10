import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch

from competitor_screenshots.config import ROOT, load_catalog, load_settings, select_targets
from competitor_screenshots.environment import configure_environment


class ConfigurationTests(unittest.TestCase):
    def test_same_day_report_keeps_other_pages_and_replaces_retries(self):
        from competitor_screenshots.report import prepare_daily_report, replace_result
        with tempfile.TemporaryDirectory() as folder:
            daily = Path(folder) / '2026-09-10'
            daily.mkdir()
            first = dict(id='first', page='homepage', status='captured')
            other = dict(id='other', page='homepage', status='captured')
            report = prepare_daily_report(daily, [first, other], 'first run')
            replace_result(report, first)
            replace_result(report, other)
            (daily / 'manifest.json').write_text(json.dumps(report), encoding='utf-8')
            report = prepare_daily_report(daily, [first], 'second run')
            replace_result(report, {**first, 'status': 'blocked'})
            self.assertEqual(report['date'], '2026-09-10')
            self.assertEqual(report['targetCount'], 2)
            self.assertEqual(report['lastRun']['targetCount'], 1)
            self.assertEqual({r['id']: r['status'] for r in report['results']}, {'first': 'blocked', 'other': 'captured'})

    def test_catalog_and_filters(self):
        catalog = load_catalog()
        self.assertEqual(len(catalog), 29)
        targets = select_targets(catalog)
        self.assertEqual(len(targets), 32)
        self.assertEqual(len({t['url'] for t in targets}), 32)
        for category, count in [('flowers', 16), ('Plants', 9), ('Greetz NL', 7)]:
            self.assertEqual(len(select_targets(catalog, category=category)), count)
        self.assertEqual(len(select_targets(catalog, page='homepage')), 29)
        self.assertEqual(len(select_targets(catalog, competitor='moonpig')), 2)
        with self.assertRaises(ValueError):
            select_targets(catalog, category='missing')

    def test_dotenv_output_and_cli_precedence(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            env_file = Path(folder) / '.env'
            destination = Path(folder) / 'Different screenshot folder'
            env_file.write_text(f'SCREENSHOT_OUTPUT_DIR="{destination.as_posix()}"\nCOOKIE_CONSENT=reject\n', encoding='utf-8')
            settings = load_settings(env_file=env_file)
            self.assertEqual(Path(settings['output']), destination.resolve())
            self.assertEqual(settings['consent'], 'reject')
            self.assertEqual(load_settings(output='override', consent='accept', env_file=env_file)['output'], str(ROOT / 'override'))
            self.assertEqual(load_settings(consent='accept', env_file=env_file)['consent'], 'accept')

    def test_base_environment_is_refused(self):
        with patch.dict(os.environ, {'CONDA_DEFAULT_ENV': 'base'}):
            with self.assertRaisesRegex(RuntimeError, 'Activate'):
                configure_environment()


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.path == '/fail':
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b'Service unavailable')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        blocker = '<div role="dialog"><p>Persistent popup without a close button</p></div>' if self.path == '/blocked' else ''
        self.wfile.write(f'''<!doctype html><html><head><title>Fixture shop</title><style>
            body {{margin:0}} section {{height:1600px;background:#dcfce7}}
            [role=dialog] {{position:fixed;inset:20px;background:white;z-index:100}}
            </style></head><body>
            <div role="dialog"><p>Cookies</p><button onclick="this.parentElement.remove()">Accept all</button></div>
            <section>Homepage fixture with enough text to represent real content. Scroll down to load the final section of this shop. All products here are local test data.</section>
            {blocker}
            <script>let loaded=false;addEventListener('scroll',()=>{{if(!loaded && scrollY>600){{loaded=true;setTimeout(()=>{{
              document.body.insertAdjacentHTML('beforeend','<section>Lazy content and footer</section><div role="dialog"><p>Newsletter</p><button onclick="this.parentElement.remove()">No thanks</button></div>');
            }},40)}}}});</script></body></html>'''.encode())


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_environment()
        from playwright.sync_api import sync_playwright
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), FixtureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.settings = dict(viewport=dict(width=800, height=600), consent='accept', settle=100,
                            timeout=10000, max_scrolls=30, scroll_delay=100)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def capture(self, folder, endpoint=''):
        from competitor_screenshots.capture import capture_target
        return capture_target(self.browser, dict(category='Flowers', name='Fixture', id='fixture', page='homepage',
                              url=self.url + endpoint), self.settings, {}, Path(folder))

    def test_full_page_lazy_content_and_popup_dismissal(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.capture(folder)
            self.assertEqual(result['status'], 'captured', result)
            self.assertTrue(any(a.startswith('accept:') for a in result['actions']))
            self.assertTrue(any(a.startswith('close:') for a in result['actions']))
            self.assertTrue(result['scroll']['reachedBottom'])
            png = (Path(folder) / result['screenshot']).read_bytes()
            width, height = struct.unpack('>II', png[16:24])
            self.assertEqual(width, 800)
            self.assertGreaterEqual(height, 3200)

    def test_unclosed_popup_never_saved_as_clean(self):
        with tempfile.TemporaryDirectory() as folder:
            stale = Path(folder) / 'flowers/fixture/homepage.png'
            stale.parent.mkdir(parents=True)
            stale.write_bytes(b'previous capture')
            result = self.capture(folder, '/blocked')
            self.assertEqual(result['status'], 'blocked', result)
            self.assertNotIn('screenshot', result)
            self.assertTrue((Path(folder) / result['diagnostic']).exists())
            self.assertFalse((Path(folder) / 'flowers/fixture/homepage.png').exists())

    def test_http_failure_has_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.capture(folder, '/fail')
            self.assertEqual(result['status'], 'failed')
            self.assertIn('503', result['error'])
            self.assertIn('diagnostic', result)

    def test_dutch_iframe_and_consent_choice(self):
        from competitor_screenshots.popups import dismiss_popups
        page = self.browser.new_page()
        try:
            page.set_content('<iframe srcdoc="<button onclick=\'this.remove()\'>Alles accepteren</button>"></iframe>')
            page.frames[1].wait_for_load_state()
            actions = []
            dismiss_popups(page, {}, 'accept', actions)
            self.assertTrue(actions)
            page.set_content('<button onclick="this.remove()">Accept all</button><button>Shop now</button>')
            dismiss_popups(page, {}, 'reject', [])
            self.assertEqual(page.get_by_role('button').count(), 2)
        finally:
            page.close()

    def test_nonsemantic_overlay_and_scroll_limit(self):
        from competitor_screenshots.popups import find_blockers
        from competitor_screenshots.capture import scroll_page
        page = self.browser.new_page()
        try:
            page.set_content('<div id="newsletter-popup" style="position:fixed;width:500px;height:400px"><button>Subscribe</button></div>')
            self.assertTrue(find_blockers(page, {}))
            page.set_content('<div style="height:10000px">Long page</div>')
            self.assertFalse(scroll_page(page, {**self.settings, 'max_scrolls': 1})['reachedBottom'])
        finally:
            page.close()

    def test_hidden_and_offscreen_dialogs_are_not_blockers(self):
        from competitor_screenshots.popups import find_blockers
        page = self.browser.new_page()
        try:
            page.set_content('''<div style="opacity:0"><div role="dialog" style="width:400px;height:400px">Hidden</div></div>
                <div role="dialog" style="position:fixed;left:110vw;width:400px;height:400px">Offscreen</div>
                <div id="modalContainer" style="position:fixed;inset:0;z-index:100;pointer-events:none"></div>''')
            self.assertEqual(find_blockers(page, {}), [])
            page.set_content('<div style="position:fixed;inset:0;z-index:100;pointer-events:none;background:rgba(0,0,0,.5)"></div>')
            self.assertTrue(find_blockers(page, {}), 'A painted backdrop still blocks capture')
        finally:
            page.close()


if __name__ == '__main__':
    unittest.main()
