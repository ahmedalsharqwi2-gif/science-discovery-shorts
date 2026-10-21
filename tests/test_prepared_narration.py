import ast
import json
import logging
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


class PreparedNarrationTests(unittest.TestCase):
    def setUp(self):
        # Execute the real orchestration method without importing optional
        # TTS/rendering dependencies or contacting a provider.
        path = Path(__file__).resolve().parents[1] / 'main.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'AutoPublishPipeline')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
        history = Mock()
        scope = {'os': os, 'json': json, 'Path': Path, 'Optional': __import__('typing').Optional,
                 'log': logging.getLogger('checkpoint-test'), 'TopicHistory': Mock(return_value=history)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), scope)
        self.run = scope['run']
        self.history = history
        report = SimpleNamespace(overall_score=1.0, is_acceptable=True)
        self.pipeline = SimpleNamespace(content_generator=Mock(), voice_generator=Mock(),
                                        quality_checker=Mock(), topic_history_path=Path('topic_history.json'))
        self.pipeline.quality_checker.check_text.return_value = ('نص كامل صالح للاختبار.', report)
        self.pipeline.voice_generator.generate.return_value = (Path('output/narration.mp3'), False)

    def execute(self, payload=None, topic=None):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path.cwd()
            try:
                os.chdir(tmp)
                checkpoint = Path('state/prepared_narration.json')
                if payload is not None:
                    checkpoint.parent.mkdir()
                    checkpoint.write_text(json.dumps(payload), encoding='utf-8')
                with patch.dict(os.environ, {'FACT_CHECK_ENABLED': 'false'}):
                    result = self.run(self.pipeline, topic=topic)
                saved = json.loads(checkpoint.read_text()) if checkpoint.exists() else None
                return result, saved
            finally:
                os.chdir(old)

    def test_restored_text_works_with_generation_providers_unavailable(self):
        self.pipeline.content_generator.generate_topic.side_effect = RuntimeError('provider unavailable')
        self.pipeline.content_generator.generate_narration.side_effect = RuntimeError('provider unavailable')
        self.execute({'schema_version': 1, 'title': 'موضوع جديد', 'narration': 'نص سابق كامل.'})
        self.pipeline.content_generator.generate_topic.assert_not_called()
        self.pipeline.content_generator.generate_narration.assert_not_called()
        self.history.check_unique.assert_called_once_with({'title': 'موضوع جديد'})
        self.pipeline.quality_checker.check_text.assert_called_once_with('نص سابق كامل.')
        self.pipeline.voice_generator.generate.assert_called_once()

    def test_fresh_text_survives_a_voice_failure(self):
        self.pipeline.content_generator.generate_topic.return_value = 'موضوع جديد'
        self.pipeline.content_generator.generate_narration.return_value = 'النص الجديد.'
        result, saved = self.execute()
        self.assertFalse(result)
        self.assertEqual(saved, {'schema_version': 1, 'title': 'موضوع جديد', 'narration': 'نص كامل صالح للاختبار.', 'audio_rejected': True})

    def test_audio_failure_preserves_valid_script_for_independent_verification(self):
        import sys
        scripts = str(Path(__file__).resolve().parents[1] / 'scripts')
        with patch.object(sys, 'path', [scripts] + sys.path):
            from check_prepared_text import usable_checkpoint
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'text.json'
            path.write_text(json.dumps({'title': 'موضوع', 'narration': 'نص كامل.', 'audio_rejected': True}))
            self.assertTrue(usable_checkpoint(path, Path(tmp) / 'history.json'))
            self.assertTrue(path.exists())

    def test_corrupt_checkpoint_does_not_publish_or_silently_change_topic(self):
        result, _ = self.execute({'schema_version': 1, 'title': 'موضوع', 'narration': ''})
        self.assertFalse(result)
        self.pipeline.voice_generator.generate.assert_not_called()
        self.pipeline.content_generator.generate_topic.assert_not_called()

    def test_explicit_topic_cannot_reuse_another_topics_text(self):
        result, _ = self.execute({'schema_version': 1, 'title': 'موضوع سابق', 'narration': 'نص سابق.'}, topic='موضوع مختلف')
        self.assertFalse(result)
        self.pipeline.voice_generator.generate.assert_not_called()
