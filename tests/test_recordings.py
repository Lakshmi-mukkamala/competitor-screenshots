import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from competitor_screenshots.config import ROOT
from competitor_screenshots.recordings import load_recording, parse_recording, recording_filename, replay_clicks


class RecordingTests(unittest.TestCase):
    def test_all_filenames_and_page_mapping(self):
        mapping = json.loads((ROOT / 'config/cookie-recordings.json').read_text())['files']
        filenames = [name for value in mapping.values() for name in (value.values() if isinstance(value, dict) else [value])]
        self.assertEqual(len(set(filenames)), 44)
        self.assertEqual(recording_filename(dict(url='https://www.moonpig.com/uk/', page='homepage'), mapping), 'Moonpig_Home_Homepage_moonpig_com.json')
        self.assertEqual(recording_filename(dict(url='https://www.greetz.nl/', page='flowers-and-plants'), mapping), 'Greetz_Flowers_Homepage_greetz_nl.json')

    def test_only_clicks_and_consent_matching(self):
        data = {'steps': [{'type': 'navigate', 'url': 'https://example.com'}, {'type': 'click', 'selectors': [['aria/Accept'], ['#accept'], ['xpath///*[@id="accept"]']]}, {'type': 'change', 'value': 'ignored'}]}
        self.assertEqual(parse_recording(data, 'accept')[1], [['#accept', 'xpath=//*[@id="accept"]']])
        self.assertEqual(parse_recording(data, 'reject'), ({}, []))
        with self.assertRaises(ValueError):
            parse_recording({'cookies': []}, 'accept')

    def test_local_loading_and_missing_file_fallback(self):
        target = dict(url='https://www.arenaflowers.com/', page='homepage')
        with tempfile.TemporaryDirectory() as folder:
            settings = dict(cookie_recordings_dir=folder, consent='accept')
            warnings = []
            self.assertEqual(load_recording(target, settings, warnings), ({}, []))
            self.assertEqual(len(warnings), 1)
            Path(folder, 'Arena_Flowers_Homepage_arenaflowers_com.json').write_text(json.dumps({'acceptSelectors': ['#accept']}))
            self.assertEqual(load_recording(target, settings, [])[0]['acceptSelectors'], ['#accept'])

    def test_alternatives_clicked_once_and_resume(self):
        from unittest.mock import Mock
        frame = Mock()
        frame.is_detached.return_value = False
        page = Mock(frames=[frame])
        clicks = [['#first', '#alternative'], ['#later']]
        with patch('competitor_screenshots.popups.click_visible', side_effect=[True, False]) as click:
            replay_clicks(page, clicks, [])
            self.assertEqual(click.call_count, 2)
            self.assertEqual(clicks, [['#later']])
        with patch('competitor_screenshots.popups.click_visible', return_value=True):
            replay_clicks(page, clicks, [])
            self.assertEqual(clicks, [])
