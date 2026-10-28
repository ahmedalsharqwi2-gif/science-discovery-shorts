import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import ImageChops
from motion_factory.editor import KINDS, preview_plan, validate
from motion_factory.renderer import MotionRenderer
from motion_factory.produce import preflight


class MotionFactoryTests(unittest.TestCase):
    def renderer(self,profile):
        plan=preview_plan(profile)
        timing={'duration':12,'words':[], 'scenes':[dict(s,start=i*2,end=(i+1)*2) for i,s in enumerate(plan['scenes'])]}
        return MotionRenderer(plan,timing,preview=True)

    def test_every_profile_renders_every_explanatory_scene_and_moves(self):
        for profile in KINDS:
            renderer=self.renderer(profile)
            for i in range(6):
                with self.subTest(profile=profile,scene=i):
                    a,b=renderer.frame(i*2+.2),renderer.frame(i*2+.9)
                    self.assertEqual(a.size,(1080,1920))
                    self.assertIsNotNone(ImageChops.difference(a,b).getbbox())

    def test_real_encoded_mp4_has_correct_geometry_and_decodes(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'preview.mp4'
            renderer=self.renderer('science');renderer.duration=1
            renderer.encode(path,width=360,fps=15)
            meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))
            stream=meta['streams'][0]
            self.assertEqual((stream['width'],stream['height']),(360,640))
            self.assertAlmostEqual(float(stream['duration']),1,places=1)
            subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)

    def test_missing_repository_secrets_stop_before_generation(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'Actions secret'):preflight()

    def test_cue_outside_narration_is_rejected(self):
        plan=preview_plan('science')
        for s in plan['scenes']:s.update(narration=' '.join(['كلمة']*35),cue='غير موجودة')
        with self.assertRaisesRegex(ValueError,'verbatim'):validate(plan,'science')

    def test_unknown_diagram_fails_instead_of_unrelated_fallback(self):
        renderer=self.renderer('science');renderer.scenes[0]['kind']='unknown'
        with self.assertRaisesRegex(ValueError,'Unsupported scene'):renderer.frame(.5)

    def test_single_workflow_has_no_publication_or_cloudflare(self):
        import yaml
        root=Path(__file__).resolve().parents[1]
        doc=yaml.safe_load((root/'.github/workflows/motion-production.yml').read_text())
        job=doc['jobs']['produce']
        self.assertEqual(job['permissions'],{'contents':'read'})
        commands='\n'.join(s.get('run','') for s in job['steps'])
        self.assertIn('python -m motion_factory.produce',commands)
        self.assertNotIn('film_factory.publish',commands)
        self.assertNotIn('CLOUDFLARE',json.dumps(doc))
        self.assertNotIn('schedule',doc['on'])


if __name__=='__main__':unittest.main()
