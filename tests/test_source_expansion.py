"""A short Egyptian draft grows without repeatedly replacing or shrinking it."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import source_episode as source


class SourceExpansionTests(unittest.TestCase):
    def test_only_foreign_words_are_repaired_without_rewriting_arabic(self):
        with patch.object(source,'ask',return_value={'replacements':[{'original':'hub','spoken':'المحور'}]}):
            self.assertEqual(source.spoken_foreign_words('الطرف أسرع من hub، وده مش ضعف ثابت.'),'الطرف أسرع من المحور، وده مش ضعف ثابت.')

    def test_short_draft_is_extended_before_editorial_review(self):
        original=' '.join(['ده الشرح اللي بنقوله عشان نفهم ليه المروحة مش بسيطة.']*20)
        extra=' '.join(['ودي كمان فكرة بتوضح اللي بيحصل عشان كده بنشرحها بهدوء.']*12)
        cwd=Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                with patch.object(source,'ask',side_effect=[{'narration':original},{'narration':extra},{'supported':True,'issues':[]}]) as ask:
                    _,text,record=source.create('propeller')
                self.assertGreaterEqual(len(text.split()),320)
                self.assertLessEqual(len(text.split()),400)
                self.assertEqual(ask.call_count,3)
                self.assertEqual(record['style_revision'],4)
                self.assertIn('ودي كمان فكرة',text)
            finally:
                os.chdir(cwd)
