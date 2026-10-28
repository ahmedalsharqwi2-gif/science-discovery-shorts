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

    def test_daily_workflow_only_publishes_after_release_gate(self):
        import yaml
        root=Path(__file__).resolve().parents[1]
        doc=yaml.safe_load((root/'.github/workflows/professional-daily.yml').read_text())
        steps=doc['jobs']['produce']['steps']
        publish=next(s for s in steps if s.get('name')=='Schedule approved daily film for exactly 17:00 Cairo')
        self.assertIn("steps.decision.outputs.publish == 'true'",publish['if'])
        self.assertIn('professional_motion.cli publish',publish['run'])
        self.assertNotIn('CLOUDFLARE',json.dumps(doc))
        self.assertEqual(doc['on']['workflow_dispatch']['inputs']['mode']['default'],'review')

    def test_long_scenes_pass_diagram_gate_without_relying_on_scene_cuts(self):
        import io
        from motion_factory.quality import audit
        for profile in KINDS:
            plan=preview_plan(profile)
            timing={'duration':96,'words':[], 'scenes':[dict(s,start=i*16,end=(i+1)*16) for i,s in enumerate(plan['scenes'])]}
            renderer=MotionRenderer(plan,timing)
            def output(command):
                if command[0]=='ffprobe':
                    return json.dumps({'streams':[{'codec_type':'video','width':1080,'height':1920}], 'format':{'duration':'96'}}).encode()
                at=float(command[command.index('-ss')+1]);buf=io.BytesIO()
                renderer.frame(at).save(buf,format='PNG');return buf.getvalue()
            with self.subTest(profile=profile),tempfile.TemporaryDirectory() as folder,patch('motion_factory.quality.subprocess.check_output',side_effect=output):
                self.assertTrue(audit('fixture.mp4',timing['scenes'],str(Path(folder)/'audit.json'))['passed'])

    def test_diagram_gate_rejects_a_real_encoded_frozen_diagram(self):
        from motion_factory.quality import audit
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);image=root/'still.png';video=root/'still.mp4'
            self.renderer('history').frame(.5).save(image)
            subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-i',str(image),'-t','10','-r','2','-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True)
            with self.assertRaisesRegex(ValueError,'frozen explanatory'):
                audit(video,[{'start':0,'end':10}],str(root/'audit.json'))


if __name__=='__main__':unittest.main()
