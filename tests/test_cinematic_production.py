"""Real FFmpeg integration with network-only fixtures; no live/billed API calls."""
import base64
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import cinematic_production as cp


class Reply:
    ok = True
    status_code = 200
    def __init__(self, value=None, raw=b''):
        self.value, self.raw = value, raw
    def json(self):
        return self.value
    def raise_for_status(self):
        pass
    def iter_content(self, size):
        yield self.raw
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class CinematicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'config').mkdir()
        self.cfg = cp.settings()
        self.cfg.update(width=360, height=640, fps=30, scene_seconds=3,
                        episode_budget_usd=.20, daily_budget_usd=.25)
        (self.root/'config/cinematic_production.json').write_text(json.dumps(self.cfg))
        (self.root/'config/cinematic_sfx.json').write_text('{}')
        self.addCleanup(self.temp.cleanup)

    def budget(self, episode='one'):
        return cp.Budget(self.root/'state/budget.json', self.cfg, episode)

    def test_free_lock_blocks_paid_even_if_paid_flags_accidentally_enabled(self):
        self.cfg.update(paid_enabled=True, video_enabled=True)
        budget = self.budget()
        with patch.object(cp.requests, 'post') as post:
            self.assertFalse(budget.reserve('image:some-model', .01))
            with self.assertRaises(RuntimeError):
                cp.generate_image('a scene', self.root/'image.png', self.cfg, budget, 'image-model')
            with self.assertRaises(RuntimeError):
                cp.generate_video(self.root/'image.png', self.root/'video.mp4', {}, self.cfg, budget)
            post.assert_not_called()
        self.assertEqual(budget.episode['estimated_usd'], 0)

    def test_free_quota_is_persisted_for_retry_and_daily_limit(self):
        self.cfg.update(max_free_calls=2, max_daily_free_calls=3)
        one=self.budget()
        self.assertTrue(one.reserve('director', .02))
        self.assertTrue(one.reserve('visual_review', .02))
        self.assertFalse(self.budget().reserve('visual_review', .02))
        two=self.budget('two')
        self.assertTrue(two.reserve('director', .02))
        self.assertFalse(self.budget('two').reserve('visual_review', .02))
        self.assertEqual(two.row['estimated_usd'], 0)

    def test_future_paid_reservations_include_failed_attempts(self):
        self.cfg.update(free_only=False, paid_enabled=True)
        self.assertTrue(self.budget().reserve('image', .08))
        self.assertTrue(self.budget().reserve('image_retry', .08))
        self.assertFalse(self.budget().reserve('image_retry', .08))
        self.assertTrue(self.budget('two').reserve('image', .08))
        self.assertFalse(self.budget('two').reserve('image_retry', .08))
        self.assertEqual(self.budget().row['estimated_usd'], .24)

    def test_weighted_captions_preserve_arabic_and_no_timeline_drift(self):
        text='هذه مدينة قديمة وفيها طريق حجري ثم نصل إلى نهاية القصة'
        events,method=cp.captions(text, 9.1, None)
        self.assertEqual(method,'character_weighted_estimate')
        self.assertEqual(' '.join(e['text'] for e in events),text)
        self.assertAlmostEqual(events[-1]['end'],9.1)
        self.assertTrue(all(len(e['text'].split())<=6 for e in events))
        scenes=cp.plan_scenes(events,9.1,{'title':'مدينة','visual_keywords':['ancient stone city']},self.cfg)
        self.assertEqual(scenes[0]['start'],0)
        self.assertAlmostEqual(scenes[-1]['end'],9.1)
        self.assertTrue(all(s['kind']!='ai_video' for s in scenes))
        self.assertTrue(all('ancient stone city'==s['query'] for s in scenes))

    def test_no_approval_without_real_review_response(self):
        with patch.object(cp,'run',return_value=''), patch.object(cp.Path,'read_bytes',return_value=b'video'), patch.object(cp,'gemini_json',return_value={'passed':False,'reason':'wrong period'}):
            with self.assertRaises(ValueError):
                cp.review_visual(self.root/'test.mp4',{'start':0,'end':2,'text':'قصة'}, {}, self.cfg,self.budget())

    def test_safe_caption_lane_and_red_keyword(self):
        path=self.root/'captions.ass'
        cp.write_captions([{'start':0,'end':2,'text':'حضارة قديمة'}],path,self.cfg)
        content=path.read_text()
        self.assertIn(',8,90,120,300,1',content)
        self.assertIn('حضارة',content)
        self.assertIn(r'\c&H003539E5&',content)
        self.assertIn('محاكاة توضيحية' if self.cfg['profile']=='science' else 'مشاهد توضيحية',content)

    def test_duration_relative_motion_reaches_end_not_fixed_1500_frames(self):
        short=cp.motion_filter('pan_right',3,360,640)
        long=cp.motion_filter('pan_right',10,360,640)
        self.assertIn('on/89',short)
        self.assertIn('on/299',long)

    def test_actual_ffmpeg_free_pipeline_cache_and_final_duration(self):
        image=self.root/'fixture.png'
        audio=self.root/'voice.wav'
        subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=size=360x640:rate=1','-frames:v','1',str(image)],check=True)
        subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','sine=frequency=300:sample_rate=48000','-t','6.7',str(audio)],check=True)
        narration='هذه مدينة حجرية قديمة نستكشف تفاصيلها بهدوء ثم نرى الطريق القديم عبر المدينة'
        episode={'title':'مدينة قديمة','visual_keywords':['ancient stone city']}
        posted=[]
        def post(url,headers,json,timeout):
            posted.append(url)
            self.assertNotIn('image:generateContent',url)
            self.assertNotIn('predictLongRunning',url)
            prompt=json['contents'][0]['parts'][0]['text']
            if prompt.startswith('You are a cinematic director'):
                scenes=__import__('json').loads(prompt.split(' Scene data: ')[1])
                result=[{'id':s['id'],'description':'Ancient stone city','query':'ancient stone city','motion':'pan_right','sfx':'none'} for s in scenes]
            else:
                self.assertEqual(json['contents'][0]['parts'][1]['inlineData']['mimeType'],'video/mp4')
                result={'passed':True,'reason':'Network fixture only, not an actual editorial assessment','audio_keep':False}
            return Reply({'candidates':[{'content':{'parts':[{'text':__import__('json').dumps(result)}]}}]})
        def get(url,**kwargs):
            if url=='https://api.pexels.com/v1/search':
                return Reply({'photos':[{'src':{'large2x':'https://images.pexels.com/fixture.png'},'url':'https://www.pexels.com/photo/fixture','photographer':'Fixture'}]})
            if 'commons.wikimedia.org' in url:
                return Reply({'query':{'pages':{}}})
            return Reply(raw=image.read_bytes())
        env={'GEMINI_API_KEY':'fixture-free-key','PEXELS_API_KEY':'fixture-pexels-key','BACKGROUND_MUSIC_ENABLED':'false'}
        with patch.dict(os.environ,env),patch.object(cp.requests,'post',side_effect=post),patch.object(cp.requests,'get',side_effect=get):
            result=cp.build(audio,narration,self.root/'output/final.mp4',episode,root=self.root)
            first_calls=len(posted)
            rerun=cp.build(audio,narration,self.root/'output/final.mp4',episode,root=self.root)
        self.assertTrue(result['passed'])
        self.assertEqual(result['quality']['width'],360)
        self.assertEqual(result['quality']['height'],640)
        self.assertAlmostEqual(result['quality']['duration'],6.7,delta=.15)
        self.assertEqual(result['estimated_episode_usd'],0)
        self.assertEqual(first_calls,len(posted))
        self.assertEqual(rerun['cached_scenes'],rerun['scene_count'])
        self.assertEqual(result['actual_sources'],{'pexels_photo':result['scene_count']})
        manifest=json.loads((self.root/'state/cinematic_scene_manifest.json').read_text())
        self.assertTrue(all(r['audio_decision']=='VOICE ONLY' for r in manifest))
        # A cache mutation must invalidate approval, without trusting its JSON label.
        Path(manifest[0]['file']).write_bytes(b'corrupted')
        with patch.object(cp,'candidates',return_value=iter([])):
            with self.assertRaises(RuntimeError):
                cp.acquire(json.loads((self.root/'state/cinematic_storyboard.json').read_text())['scenes'][0],{'title':'مدينة قديمة','narration':narration,'visual_keywords':['ancient stone city']},self.cfg,self.budget(),self.root/'.cinematic_cache')

if __name__=='__main__':
    unittest.main()
