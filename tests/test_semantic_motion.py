import json
from pathlib import Path
import tempfile
import unittest
from scripts.semantic_motion import plan_motion_scenes, load_word_timeline
from scripts.forced_caption_alignment import merge_waveform_alignments


class SemanticMotionTests(unittest.TestCase):
    def test_complementary_measurements_recover_without_inventing_times(self):
        a=[{'text':'ده','start':.1,'end':.5},{'text':'شرح','start':.8,'end':.8}]
        b=[{'text':'ده','start':.1,'end':.1},{'text':'شرح','start':.8,'end':1.3}]
        self.assertEqual(merge_waveform_alignments([a,b],['ده','شرح'],2),[a[0],b[1]])
        with self.assertRaisesRegex(RuntimeError,'No measured'):
            merge_waveform_alignments([a,a],['ده','شرح'],2)

    def test_pressure_cue_waits_for_its_actual_spoken_word(self):
        words = [{'text':'الحركة','offset':0.,'duration':.5},
                 {'text':'بتعمل','offset':.7,'duration':.5},
                 {'text':'فرق','offset':1.4,'duration':.5},
                 {'text':'ضغط.','offset':2.1,'duration':.5}]
        scenes = plan_motion_scenes(words,4.)
        self.assertEqual(scenes[0]['motion_beats'][-1],{'at':2.1,'concept':'pressure'})
        self.assertEqual(' '.join(s['text'] for s in scenes),'الحركة بتعمل فرق ضغط.')
        self.assertEqual(scenes[-1]['end'],4.)

    def test_different_narration_cannot_reuse_old_word_timing(self):
        with tempfile.TemporaryDirectory() as folder:
            ass = Path(folder)/'captions.ass'
            ass.with_suffix('.words.json').write_text(json.dumps({'narration':'نص قديم','duration':4,'words':[]}))
            with self.assertRaisesRegex(RuntimeError,'another narration'):
                load_word_timeline(ass,'نص جديد',4)

    def test_every_word_is_preserved_across_scene_boundaries(self):
        text='شفرة المروحة بتلف. طرف الشفرة أسرع عشان المسار أكبر. الضغط بيتغير. فيه خسائر عند الأطراف.'
        words=[{'text':w,'offset':i*.8,'duration':.6} for i,w in enumerate(text.split())]
        duration=len(words)*.8
        scenes=plan_motion_scenes(words,duration)
        self.assertEqual(' '.join(s['text'] for s in scenes),text)
        self.assertEqual(scenes[0]['start'],0)
        for left,right in zip(scenes,scenes[1:]):self.assertEqual(left['end'],right['start'])
        concepts={b['concept'] for s in scenes for b in s['motion_beats']}
        self.assertIn('pressure',concepts)
        self.assertIn('losses',concepts)
