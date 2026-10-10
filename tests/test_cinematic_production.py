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
                        episode_budget_usd=.20, daily_budget_usd=.25, free_request_interval_seconds=0)
        (self.root/'config/cinematic_production.json').write_text(json.dumps(self.cfg))
        (self.root/'config/cinematic_sfx.json').write_text('{}')
        self.addCleanup(self.temp.cleanup)

    def budget(self, episode='one'):
        return cp.Budget(self.root/'state/budget.json', self.cfg, episode)

    def test_science_config_uses_three_minute_ceiling(self):
        self.assertEqual(cp.settings()['max_duration_seconds'], 180)

    def test_settings_reject_duration_above_three_minutes(self):
        cfg = dict(self.cfg, max_duration_seconds=180.01)
        (self.root/'config/cinematic_production.json').write_text(json.dumps(cfg))
        with self.assertRaisesRegex(ValueError, '180 seconds'):
            cp.settings(self.root)

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

    def test_transient_free_quota_retries_are_bounded_and_reserved(self):
        throttled=Reply()
        throttled.ok=False
        throttled.status_code=429
        good=Reply({'candidates':[{'content':{'parts':[{'text':'{"passed":true}'}]}}]})
        budget=self.budget()
        with patch.dict(os.environ,{'GEMINI_API_KEY':'fixture-free-key'}), patch.object(cp.requests,'post',side_effect=[throttled,good]) as post, patch.object(cp.time,'sleep'):
            result=cp.gemini_json([{'text':'Review'}],'free-model',budget,.02,'visual_review')
        self.assertTrue(result['passed'])
        self.assertEqual(post.call_count,2)
        self.assertEqual(budget.episode['free_calls'],2)
        self.assertEqual(budget.episode['estimated_usd'],0)

    def test_weighted_captions_preserve_arabic_and_no_timeline_drift(self):
        text='هذه مدينة قديمة وفيها طريق حجري ثم نصل إلى نهاية القصة'
        events,method=cp.captions(text, 9.1, None)
        self.assertEqual(method,'character_weighted_estimate')
        self.assertEqual(' '.join(e['text'] for e in events),text)
        self.assertAlmostEqual(events[-1]['end'],9.1)
        self.assertTrue(all(len(e['text'].split())<=4 for e in events))
        scenes=cp.plan_scenes(events,9.1,{'title':'مدينة','visual_keywords':['ancient stone city']},self.cfg)
        self.assertEqual(scenes[0]['start'],0)
        self.assertAlmostEqual(scenes[-1]['end'],9.1)
        self.assertTrue(all(s['kind']!='ai_video' for s in scenes))
        self.assertTrue(all('ancient stone city'==s['query'] for s in scenes))

    def test_existing_word_timeline_preserves_active_color_and_interval(self):
        source = self.root / 'word_timeline.ass'
        source.write_text(
            '[Events]\n'
            'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
            r'Dialogue: 0,0:00:00.00,0:00:01.25,Caption,,0,0,0,,هذا {\c&H000000FF&}نص{\c&H00FFFFFF&} عربي سليم' + '\n',
            encoding='utf-8',
        )
        events, method = cp.captions('هذا نص عربي سليم', 2.0, source)
        self.assertEqual(method, 'existing_audio_timeline')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['start'], 0.0)
        self.assertEqual(events[0]['end'], 1.25)
        self.assertIn(r'{\c&H000000FF&}نص', events[0]['ass_text'])
        output = self.root / 'rendered.ass'
        cp.write_captions(events, output, self.cfg)
        self.assertIn(r"\c&H000000FF&}نص", output.read_text(encoding='utf-8'))

    def test_full_cinematic_caption_path_keeps_first_arabic_word_on_right(self):
        from PIL import Image
        from scripts.assemble_video import write_ass_subtitles
        source = self.root / 'source.ass'
        output = self.root / 'cinematic.ass'
        frame = self.root / 'frame.png'
        narration = 'الشعاب المرجانية تحمي السواحل'
        write_ass_subtitles(narration, 4.0, source)
        events, method = cp.captions(narration, 4.0, source)
        self.assertEqual(method, 'existing_audio_timeline')
        cp.write_captions(events, output, cp.settings())
        subprocess.run([
            'ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
            'color=c=black:s=1080x1920:r=30:d=1', '-vf', f"subtitles='{output}'",
            '-frames:v', '1', str(frame),
        ], check=True)
        image = Image.open(frame).convert('RGB')
        red_x = [x for y in range(image.height) for x in range(image.width)
                 if (lambda p: p[0] > 150 and p[1] < 110 and p[2] < 110)(image.getpixel((x,y)))]
        self.assertTrue(red_x, 'active word was not rendered in red')
        self.assertGreater(sum(red_x) / len(red_x), image.width / 2)

    def test_scene_plan_collapses_repeated_four_word_highlight_events(self):
        words = 'الشعاب المرجانية تحمي السواحل'.split()
        events = []
        for active in range(4):
            start, end = active * .25, (active + 1) * .25
            for word in words:
                events.append({'start':start,'end':end,'text':word,
                               'ass_text':rf'{{\an5\pos(500,300)}}{word}'})
        lines = cp.scene_plan_events(events)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['text'], 'الشعاب المرجانية تحمي السواحل')
        self.assertEqual(lines[0]['start'], 0)
        self.assertEqual(lines[0]['end'], 1)

    def test_scene_plan_removes_overlapping_recognition_chunks(self):
        events = [
            {'start':0,'end':1,'text':'السحيقة تعتمد الحقيقة العلمية'},
            {'start':1,'end':2,'text':'السحيقة تعتمد الحقيقة العلمية المثبتة في ميكانيكا المائعات'},
            {'start':2,'end':3,'text':'المثبتة في ميكانيكا المائعات على مبدأ أرخميدس'},
        ]
        lines = cp.scene_plan_events(events)
        self.assertEqual([line['text'] for line in lines], [
            'السحيقة تعتمد الحقيقة العلمية',
            'المثبتة في ميكانيكا المائعات',
            'على مبدأ أرخميدس',
        ])

    def test_submarine_story_gets_a_topic_anchored_visual_query(self):
        episode={'title':'كيف تتحكم الغواصات في الصعود والهبوط داخل الأعماق؟'}
        scenes=cp.plan_scenes([{'start':0,'end':4,'text':'تتحكم الغواصات في الطفو وخزانات الاتزان'}],4,episode,self.cfg)
        self.assertIn('submarine',scenes[0]['query'])
        self.assertIn('ballast tanks',scenes[0]['query'])
        self.assertIn('buoyancy',scenes[0]['query'])
        pressure_episode={'title':'كيف تتحمل الغواصة ضغط الأعماق؟'}
        pressure_scene=cp.plan_scenes([{'start':0,'end':4,'text':'يتحمل هيكل الغواصة ضغط الماء'}],4,pressure_episode,self.cfg)
        self.assertIn('submarine',pressure_scene[0]['query'])
        self.assertIn('pressure hull',pressure_scene[0]['query'])

    def test_local_science_plan_generates_search_query_when_director_is_unavailable(self):
        text='هل سألت نفسك لماذا يقف طائر النحام على ساق واحدة في مياه ضحلة'
        episode={'title':'لماذا يقف النحام على ساق واحدة؟'}
        scenes=cp.plan_scenes([{'start':0,'end':4,'text':text}],4,episode,self.cfg)
        query=scenes[0]['query']
        self.assertIn('flamingo',query)
        self.assertIn('standing on one leg',query)
        self.assertIn('shallow water',query)
        with patch.object(cp,'gemini_json',side_effect=RuntimeError('quota')):
            cp.direct_scenes(scenes,episode,self.cfg,self.budget())
        self.assertEqual(scenes[0]['query'],query)

    def test_blank_director_query_does_not_erase_local_search_query(self):
        episode={'title':'لماذا يقف النحام على ساق واحدة؟'}
        scenes=cp.plan_scenes([{'start':0,'end':4,'text':'طائر النحام في ماء ضحل'}],4,episode,self.cfg)
        query=scenes[0]['query']
        director=[{'id':scenes[0]['id'],'description':'Flamingo in shallow water','query':'','motion':'zoom_in','sfx':'none'}]
        with patch.object(cp,'gemini_json',return_value=director):
            cp.direct_scenes(scenes,episode,self.cfg,self.budget())
        self.assertEqual(scenes[0]['query'],query)

    def test_science_director_query_cannot_drift_from_carrier_to_city(self):
        episode={'title':'كيف تطفو حاملة طائرات رغم وزنها الهائل؟'}
        scene=cp.plan_scenes([{'start':0,'end':4,'text':'تطفو حاملة طائرات فوق الماء'}],4,episode,self.cfg)
        director=[{'id':scene[0]['id'],'description':'A carrier floating at sea',
                   'query':'massive iron city floating on water','motion':'zoom_in','sfx':'water'}]
        with patch.object(cp,'gemini_json',return_value=director):
            cp.direct_scenes(scene,episode,self.cfg,self.budget())
        self.assertIn('aircraft carrier',scene[0]['query'])
        self.assertNotIn('city',scene[0]['query'])

    def test_reef_director_query_cannot_drift_to_unrelated_subject(self):
        episode={'title':'كيف تحمي الشعاب المرجانية السواحل؟'}
        scene=cp.plan_scenes([{'start':0,'end':4,'text':'الشعاب المرجانية تحمي السواحل'}],4,episode,self.cfg)
        director=[{'id':scene[0]['id'],'description':'Blood flow','query':'blood flow','motion':'zoom_in','sfx':'none'}]
        with patch.object(cp,'gemini_json',return_value=director):
            cp.direct_scenes(scene,episode,self.cfg,self.budget())
        self.assertIn('coral reef',scene[0]['query'])
        self.assertNotIn('blood',scene[0]['query'])

    def test_exhausted_free_quota_searches_stock_before_coral_fallback(self):
        scene = {'id':'scene_quota','start':0,'end':3,'motion':'zoom_in','kind':'image',
                 'query':'coral reef coastline','text':'الشعاب المرجانية تحمي السواحل'}
        cfg = dict(self.cfg, max_daily_free_calls=1)
        budget = cp.Budget(self.root/'state/quota-budget.json', cfg, 'episode-quota')
        self.assertTrue(budget.reserve('visual_review', .02))
        with (
            patch.dict(os.environ, {'CINEMATIC_IMAGE_FALLBACK_ENABLED':'false'}),
            patch.object(cp, 'candidates', return_value=iter([])) as stock_search,
            patch.object(cp, 'render_visual', side_effect=lambda source,out,*a,**k: out.write_bytes(b'reviewable-video')),
        ):
            video, record = cp.acquire(scene, {'title':'كيف تحمي الشعاب المرجانية السواحل؟'}, cfg, budget, self.root/'.cinematic_cache')
        stock_search.assert_called_once()
        self.assertTrue(video.exists())
        self.assertEqual(record['source'], 'local_coral_reef_illustration')
        self.assertTrue(record['quota_fallback'])
        self.assertEqual(record['review']['reviewer'], 'local-coral-reef-template')
        self.assertTrue(record['review']['passed'])

    def test_exhausted_free_quota_uses_submarine_fallback_without_provider_calls(self):
        scene={'id':'scene_submarine','start':0,'end':3,'motion':'zoom_in','kind':'image',
               'query':'submarine underwater ballast tanks buoyancy',
               'text':'تتحكم الغواصات في الصعود والهبوط بقوة الطفو'}
        episode={'title':'كيف تتحكم الغواصات في الصعود والهبوط داخل الأعماق؟',
                 'narration':'تتحكم الغواصات في الطفو عبر خزانات الاتزان.'}
        cfg=dict(self.cfg,max_daily_free_calls=1)
        budget=cp.Budget(self.root/'state/submarine-quota-budget.json',cfg,'episode-submarine')
        self.assertTrue(budget.reserve('visual_review',.02))
        with patch.dict(os.environ, {'CINEMATIC_IMAGE_FALLBACK_ENABLED':'false'}), \
             patch.object(cp,'candidates',return_value=iter([])) as stock_search, \
             patch.object(cp,'render_visual',side_effect=lambda source,out,*a,**k: out.write_bytes(b'rendered-submarine-video')):
            video,record=cp.acquire(scene,episode,cfg,budget,self.root/'.cinematic_cache')
        stock_search.assert_called_once()
        self.assertTrue(video.exists())
        self.assertEqual(record['source'],'local_submarine_science_illustration')
        self.assertTrue(record['quota_fallback'])
        self.assertEqual(record['review']['reviewer'],'local-submarine-science-template')
        self.assertTrue(record['review']['passed'])

    def test_exhausted_free_quota_uses_submarine_pressure_fallback(self):
        scene={'id':'scene_pressure','start':0,'end':3,'motion':'zoom_in','kind':'image',
               'query':'submarine deep sea pressure hull','text':'يتحمل هيكل الغواصة ضغط الماء في الأعماق'}
        episode={'title':'كيف تتحمل الغواصة ضغط الأعماق؟','narration':'يضغط الماء على الهيكل عند الأعماق.'}
        cfg=dict(self.cfg,max_daily_free_calls=1)
        budget=cp.Budget(self.root/'state/pressure-quota-budget.json',cfg,'episode-pressure')
        self.assertTrue(budget.reserve('visual_review',.02))
        with patch.dict(os.environ, {'CINEMATIC_IMAGE_FALLBACK_ENABLED':'false'}), \
             patch.object(cp,'candidates',return_value=iter([])) as stock_search, \
             patch.object(cp,'render_visual',side_effect=lambda source,out,*a,**k: out.write_bytes(b'rendered-pressure-submarine-video')):
            video,record=cp.acquire(scene,episode,cfg,budget,self.root/'.cinematic_cache')
        stock_search.assert_called_once()
        self.assertTrue(video.exists())
        self.assertEqual(record['source'],'local_submarine_science_illustration')
        self.assertTrue(record['review']['passed'])

    def test_exhausted_free_quota_refuses_generic_placeholder_for_other_topics(self):
        scene={'id':'scene_ship','start':0,'end':3,'motion':'zoom_in','kind':'image',
               'query':'steel ship structure','text':'تتشقق الهياكل المعدنية بسبب الإجهاد'}
        cfg=dict(self.cfg,max_daily_free_calls=1)
        budget=cp.Budget(self.root/'state/quota-budget.json',cfg,'episode-ship')
        self.assertTrue(budget.reserve('visual_review',.02))
        with patch.dict(os.environ, {'CINEMATIC_IMAGE_FALLBACK_ENABLED':'false'}), \
             patch.object(cp,'candidates',return_value=iter([])) as stock_search, \
             patch.object(cp,'render_visual',side_effect=AssertionError('generic fallback must not render')):
            with self.assertRaisesRegex(RuntimeError,'No inspected visual'):
                cp.acquire(scene,{'title':'هياكل السفن'},cfg,budget,self.root/'.cinematic_cache')
        stock_search.assert_called_once()
        report=json.loads((self.root/'state/cinematic_failures.json').read_text())
        self.assertTrue(any('no topic-specific local illustration' in item['error'].lower()
                            for item in report['attempts']))

    def test_quota_exhaustion_accepts_topic_anchored_pexels_video_after_local_checks(self):
        scene={'id':'scene_submarine','start':0,'end':3,'motion':'zoom_in','kind':'image',
               'query':'submarine underwater ballast tanks buoyancy','text':'تتحكم الغواصات في الطفو'}
        episode={'title':'كيف تتحكم الغواصات في الطفو؟','narration':scene['text']}
        cfg=dict(self.cfg,max_free_calls=10,max_daily_free_calls=1)
        budget=cp.Budget(self.root/'state/stock-budget.json',cfg,'episode-stock')
        self.assertTrue(budget.reserve('visual_review',.02))
        candidate={'url':'https://videos.pexels.com/video-files/123.mp4','image':False,
                   'source':'pexels_video','media_type':'video','asset_id':'pexels-123','pexels_id':'123',
                   'license':'Pexels','source_url':'https://www.pexels.com/video/submarine-123/',
                   'query_used':'submarine underwater ballast tanks buoyancy'}
        source_probe={'duration':5,'streams':[{'codec_type':'video','width':720,'height':1280}]}
        output_probe={'duration':3,'streams':[{'codec_type':'video','width':360,'height':640}]}
        def write_source(url,target):
            target.write_bytes(b'fixture-source-video')
        def render(source,out,*args,**kwargs):
            out.write_bytes(b'fixture-rendered-video')
        with patch.object(cp,'candidates',return_value=iter([candidate])) as search, \
             patch.object(cp,'download',side_effect=write_source), \
             patch.object(cp,'render_visual',side_effect=render), \
             patch.object(cp,'probe',side_effect=[source_probe,output_probe]), \
             patch.object(cp,'review_visual',side_effect=AssertionError('AI quota is exhausted')), \
             patch.object(cp,'apply_audio_review',side_effect=lambda video,review: review):
            video,record=cp.acquire(scene,episode,cfg,budget,self.root/'.cinematic_cache')
        search.assert_called_once()
        self.assertTrue(video.exists())
        self.assertEqual(record['source'],'pexels_video')
        self.assertEqual(record['media_type'],'video')
        self.assertEqual(record['asset_id'],'pexels-123')
        self.assertFalse(record['illustrative'])
        self.assertEqual(record['review']['reviewer'],'local-stock-source-technical-check')
        self.assertFalse(record['review']['audio_keep'])

    def test_image_scene_searches_video_before_still_photos(self):
        scene={'id':'scene_video_first','kind':'image','query':'submarine underwater ballast tanks buoyancy'}
        video_result={'videos':[{'id':321,'url':'https://www.pexels.com/video/submarine-321/',
            'duration':8,'video_files':[{'link':'https://videos.pexels.com/321.mp4','width':720,'height':1280}]}]}
        with patch.dict(os.environ,{'PEXELS_API_KEY':'fixture-key'}), \
             patch('scripts.cinematic_production.requests.get',return_value=Reply(video_result)) as request, \
             patch('scripts.commons_media.search_images',return_value=[]):
            candidate=next(cp.candidates(scene,self.cfg))
        self.assertEqual(candidate['media_type'],'video')
        self.assertEqual(candidate['source'],'pexels_video')
        self.assertIn('/videos/search',request.call_args.args[0])

    def test_empty_asset_search_saves_a_specific_no_candidates_report(self):
        scene=cp.plan_scenes([{'start':0,'end':4,'text':'طائر النحام في ماء ضحل'}],4,{'title':'النحام'},self.cfg)[0]
        with patch.dict(os.environ,{'PEXELS_API_KEY':'fixture-key'}),patch.object(cp,'candidates',return_value=iter([])):
            with self.assertRaisesRegex(RuntimeError,'detailed report saved'):
                cp.acquire(scene,{'title':'النحام','narration':scene['text']},self.cfg,self.budget(),self.root/'.cinematic_cache')
        report=json.loads((self.root/'state/cinematic_failures.json').read_text())
        self.assertEqual(report['scene_id'],'scene_001')
        self.assertEqual(report['primary_query'],scene['query'])
        self.assertTrue(report['pexels_key_configured'])
        self.assertEqual(report['attempts'][0]['error_type'],'NoCandidates')

    def test_buoyancy_scene_gets_a_local_vector_illustration_after_search_exhaustion(self):
        scene={'id':'scene_010','start':0,'end':3,'motion':'zoom_in',
               'query':'upward buoyant force physics diagram',
               'text':'يدفع الماء الجسم بقوة الطفو إلى الأعلى'}
        image=self.root/'buoyancy.png'
        self.assertTrue(cp._write_buoyancy_diagram(scene,image,self.cfg))
        from PIL import Image
        with Image.open(image) as rendered:
            self.assertEqual(rendered.size,(self.cfg['width'],self.cfg['height']))
            self.assertGreater(len(rendered.convert('RGB').getcolors(maxcolors=1000000) or []),10)

    def test_submarine_buoyancy_fallback_is_a_full_color_portrait_illustration(self):
        scene={'id':'scene_submarine','start':0,'end':3,'motion':'zoom_in',
               'query':'submarine underwater ballast tanks buoyancy',
               'text':'تتحكم الغواصات في الصعود والهبوط بقوة الطفو'}
        episode={'title':'كيف تتحكم الغواصات في الصعود والهبوط؟','narration':scene['text']}
        image=self.root/'submarine-buoyancy.png'
        self.assertTrue(cp._write_submarine_science_illustration(scene,image,self.cfg,episode))
        from PIL import Image
        with Image.open(image) as rendered:
            self.assertEqual(rendered.size,(self.cfg['width'],self.cfg['height']))
            self.assertGreater(len(rendered.convert('RGB').getcolors(maxcolors=1000000) or []),50)
        with (
            patch.object(cp,'candidates',return_value=iter([])),
            patch.object(cp,'render_visual',side_effect=lambda source,out,*a,**k: out.write_bytes(b'reviewable-video')),
            patch.object(cp,'review_visual',return_value={'passed':True,'reason':'literal buoyancy vector diagram','audio_keep':False,'sha256':'fixture'}),
            patch.object(cp,'apply_audio_review',side_effect=lambda video,review: review),
        ):
            video,record=cp.acquire(scene,{'title':'كيف تطفو السفينة؟'},self.cfg,self.budget(),self.root/'.cinematic_cache')
        self.assertTrue(video.exists())
        self.assertEqual(record['source'],'local_submarine_science_illustration')
        self.assertTrue(record['review']['passed'])

    def test_buoyancy_diagram_is_not_used_for_unrelated_or_non_science_scenes(self):
        scene={'query':'flower field','text':'flower field'}
        self.assertFalse(cp._write_buoyancy_diagram(scene,self.root/'no.png',self.cfg))
        self.assertFalse(cp._write_buoyancy_diagram(
            {'query':'buoyant force','text':'buoyant force'},self.root/'history.png',dict(self.cfg,profile='history')))
        self.assertTrue(cp._write_buoyancy_diagram(
            {'query':'massive iron city floating on water','text':'مدينة عائمة'},
            self.root/'carrier.png',self.cfg,{'title':'كيف تطفو حاملة طائرات؟'}))

    def test_failed_scene_report_preserves_source_and_reviewer_reason(self):
        scene={'id':'scene_001','start':0,'end':3,'motion':'zoom_in','kind':'image',
               'query':'flamingo in shallow water','text':'طائر النحام في الماء'}
        candidate={'url':'https://images.pexels.com/fixture.png','image':True,
                   'source':'fixture_photo','license':'fixture'}
        cache=self.root/'.cinematic_cache'
        cache.mkdir()
        with (
            patch.object(cp,'candidates',return_value=iter([candidate])),
            patch.object(cp,'download',side_effect=lambda url,path: path.write_bytes(b'image')),
            patch.object(cp,'render_visual',side_effect=lambda source,out,*a,**k: out.write_bytes(b'video')),
            patch.object(cp,'review_visual',side_effect=ValueError('Actual visual inspection rejected scene: unrelated image')),
        ):
            with self.assertRaisesRegex(RuntimeError,'No inspected visual'):
                cp.acquire(scene,{'title':'النحام'},self.cfg,self.budget(),cache)
        report=json.loads((self.root/'state/cinematic_failures.json').read_text())
        self.assertEqual(report['attempts'][0]['source'],'fixture_photo')
        self.assertIn('unrelated image',report['attempts'][0]['error'])

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
        self.assertIn(r'\c&H000000FF&',content)
        self.assertNotIn('محاكاة توضيحية', content)
        self.assertNotIn('مشاهد توضيحية', content)

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
        photo_counter={'value':0}
        def get(url,**kwargs):
            if url=='https://api.pexels.com/videos/search':
                return Reply({'videos':[]})
            if url=='https://api.pexels.com/v1/search':
                photo_counter['value']+=1
                index=photo_counter['value']
                return Reply({'photos':[{'id':index,'src':{'large2x':f'https://images.pexels.com/fixture-{index}.png'},'url':f'https://www.pexels.com/photo/fixture-{index}','photographer':'Fixture'}]})
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
