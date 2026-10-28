import tempfile
import unittest
import wave
from pathlib import Path
import numpy as np
from professional_motion.alignment import measured_timing
from professional_motion.score import build


class ProfessionalProofTests(unittest.TestCase):
    def fixture(self):
        words=['البحر','جميل','الماء','أزرق','جلد','لون','ضوء','صبغة','خلية','عصب']
        story={'scenes':[{'id':'a','narration':' '.join(words[:5])},{'id':'b','narration':' '.join(words[5:])}]}
        actual=[{'text':w,'start':i*.5,'end':i*.5+.4} for i,w in enumerate(words)]
        return story,actual

    def test_complementary_exact_anchors_are_retained(self):
        story,actual=self.fixture()
        result=measured_timing(story,5,[('medium',actual[:8]),('small',actual[7:])])
        self.assertEqual(result['coverage'],1)
        self.assertEqual(result['scenes'][1]['start'],2.5)
        self.assertEqual(result['caption_groups'][0]['start'],0)
        self.assertEqual(result['scenes'][-1]['end'],5)

    def test_missing_speech_is_not_hidden_by_invented_timing(self):
        story,actual=self.fixture()
        with self.assertRaisesRegex(ValueError,'Insufficient'):
            measured_timing(story,5,[('medium',actual[:5])])

    def test_conflicting_model_anchors_are_rejected(self):
        story,actual=self.fixture();actual[5]['start']=.1
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            measured_timing(story,5,[('medium',actual)])

    def test_composed_stems_are_stereo_full_length_and_not_clipped(self):
        with tempfile.TemporaryDirectory() as folder:
            build(4,[0,2],folder)
            for name in ('score.wav','sfx.wav'):
                with wave.open(str(Path(folder)/name)) as w:
                    self.assertEqual((w.getframerate(),w.getnchannels(),w.getnframes()),(48000,2,192000))
                    values=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
                    self.assertGreater(np.std(values),10)
                    self.assertLess(np.max(np.abs(values.astype(np.int32))),32760)


if __name__=='__main__':unittest.main()
