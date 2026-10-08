import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import pexels_video as media


class VisualSubjectTests(unittest.TestCase):
    def test_cats_take_priority_over_water(self):
        queries = media.visual_queries('لماذا تخاف القطط من الماء؟')
        self.assertTrue(all('cat' in query for query in queries))
        self.assertFalse(any('ocean' in query for query in queries))

    def test_submarine_takes_priority_over_sea(self):
        self.assertTrue(all('submarine' in query for query in media.visual_queries('كيف تتحرك الغواصات في أعماق البحر؟')))

    def test_polar_topic_is_not_a_cat(self):
        self.assertFalse(any('cat' in query for query in media.visual_queries('القطب الشمالي والمناخ')))

    def test_more_than_six_clips_and_no_repeated_concat_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'video.mp4'
            urls = [f'https://example.org/{i}.mp4' for i in range(15)]
            def touch_download(url, path):
                path.write_bytes(b'video')
            def touch_normalize(source, destination, duration, decision='VOICE ONLY'):
                destination.write_bytes(b'video')
            def concat(command, **kwargs):
                Path(command[-1]).write_bytes(b'video')
            previous = os.getcwd()
            os.chdir(directory)
            try:
                with patch.object(media, 'resolve_visual_queries', return_value=['cat']), patch.object(media, 'search_portrait_videos', return_value=urls), patch.object(media, '_download', side_effect=touch_download) as download, patch.object(media, '_normalize_clip', side_effect=touch_normalize), patch.object(media, 'review_clip', return_value={'audio_decision': 'VOICE ONLY'}), patch.object(media.subprocess, 'run', side_effect=concat):
                    self.assertTrue(media.build_pexels_track('key', 'cats', 59, target))
                    self.assertEqual(download.call_count, 10)
                    entries = (Path(directory) / 'pexels_clips/concat.txt').read_text().splitlines()
                    self.assertEqual(len(entries), 10)
                    self.assertEqual(len(set(entries)), 10)
                    self.assertTrue(Path('state/science_visual_history.json').exists())
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
