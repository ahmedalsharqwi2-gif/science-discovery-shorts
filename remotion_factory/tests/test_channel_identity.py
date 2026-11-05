import copy,hashlib,json,tempfile,unittest,wave
from pathlib import Path
from remotion_factory.identity import IDENTITIES,VERSION,SHOTS,identity,inferred_object,scene_plan,schema_for,validate_director
from remotion_factory.visual_assets import choose
from remotion_factory.score import build
class ChannelIdentities(unittest.TestCase):
 def story(self,p):return {'profile':p,'title':'same retained story','canonical_subject':'same-retained-topic','source':{},'scenes':[{'id':str(i),'narration':'الماء والصابون','label':'نفس النص','labels':['الماء','الصابون'],'visual':{}} for i in range(8)]}
 def test_visual_planning_does_not_rewrite_retained_script(self):
  from visual_contract import load_template
  s=self.story(load_template()['channel']);before=copy.deepcopy(s);p=scene_plan(s);self.assertEqual(s,before);self.assertEqual(p['version'],VERSION);self.assertEqual(len(p['scenes']),8)
 def test_profiles_have_distinct_visual_and_sound_direction(self):
  from visual_contract import load_template
  t=load_template();self.assertEqual(identity(t['channel'])['name'],t['display_name'])
  for p in IDENTITIES:
   if p!=t['channel']:
    with self.assertRaisesRegex(ValueError,'Cross-channel'):identity(p)
 def test_bacteria_never_default_to_an_animal_cell_with_a_nucleus(self):
  s=self.story('science');s['scenes'][0]['narration']='كيف تقاوم البكتيريا المضادات؟';self.assertEqual(inferred_object(s['scenes'][0],s),'bacterium')
 def test_old_acknowledged_draft_is_not_rejected_for_missing_new_metadata(self):validate_director({'scenes':[]},'science')
 def test_fabricated_media_url_is_rejected_before_voice(self):
  s={'director_version':VERSION,'scenes':[{'shot_type':'macro','hero_object':'cell','object_motion':'spin','visual_rationale':'A visible explanatory cell mechanism','image_query':'https://evil.test/image'}]}
  with self.assertRaisesRegex(ValueError,'not executable'):validate_director(s,'science')
 def test_unrelated_and_unclearly_licensed_images_are_not_selected(self):
  item={'title':'File:Random cat.jpg','imageinfo':[{'mime':'image/jpeg','url':'https://upload.wikimedia.org/a.jpg','extmetadata':{'LicenseShortName':{'value':'Public domain'},'ImageDescription':{'value':'A random cat'}}}]}
  self.assertIsNone(choose('Mary Celeste', [item]));item['title']='File:Mary Celeste.jpg';item['imageinfo'][0]['extmetadata']['LicenseShortName']['value']='Copyright';self.assertIsNone(choose('Mary Celeste',[item]))
 def test_two_character_story_needs_a_cause_attempt_and_consequence(self):
  s={'director_version':VERSION,'scenes':[{'shot_type':'impact','hero_object':'sphere','object_motion':'float','visual_rationale':'Two characters discover floating objects','image_query':'','cause':'','attempt':'a','consequence':'b'}]}
  with self.assertRaisesRegex(ValueError,'causal'):validate_director(s,'stickman')
 def test_audio_rejects_cross_channel_profiles_and_never_synthesizes_missing_assets(self):
  from visual_contract import load_template
  p=load_template()['channel']
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)/p;build(2,[0,1],root,p,episode_key='retained-topic',scene_kinds=['molecule','ship'])
   report=json.loads((root/'score.json').read_text());self.assertFalse(report['synthetic_substitutes']);self.assertEqual(report['cues'],[])
   with wave.open(str(root/'sfx.wav')) as w:self.assertFalse(any(w.readframes(w.getnframes())))
   for other in IDENTITIES:
    if other!=p:
     with self.assertRaisesRegex(ValueError,'Cross-channel'):build(2,[0],Path(folder)/other,other)
 def test_same_episode_sound_is_repeatable_without_any_provider_request(self):
  with tempfile.TemporaryDirectory() as folder:
   from visual_contract import load_template
   p=load_template()['channel'];a,b=Path(folder)/'a',Path(folder)/'b';build(2,[0,1],a,p,episode_key='exact-same-episode');build(2,[0,1],b,p,episode_key='exact-same-episode');self.assertEqual((a/'score.wav').read_bytes(),(b/'score.wav').read_bytes())

 def test_archival_credits_keep_the_author_license_and_source_without_repeating_scenes(self):
  from remotion_factory.asset_credits import format_credits
  source={'artist':'Actual photographer','license':'CC BY-SA 4.0','attribution_url':'https://commons.wikimedia.org/?curid=123'}
  text=format_credits([source,source]);self.assertIn('Actual photographer',text);self.assertIn('CC BY-SA 4.0',text);self.assertEqual(text.count('curid=123'),1)
 def test_egyptian_monuments_are_not_drawn_as_a_greek_temple(self):
  s=self.story('history');s['canonical_subject']='abu-simbel-relocation-1960s';s['scenes'][0]['narration']='تفكيك أجزاء المعبد ونقلها';self.assertEqual(inferred_object(s['scenes'][0],s),'egypt_temple')
 def test_a_scene_does_not_inherit_every_object_from_the_episode_title(self):
  s=self.story('science');s['canonical_subject']='soap-surfactants-micelles-and-rinsing';s['scenes'][0]['narration']='الجزيء له ذيل ورأس';self.assertEqual(inferred_object(s['scenes'][0],s),'surfactant')

 def test_stickman_dialogue_is_not_forced_into_a_three_dimensional_object_catalog(self):
  schema=schema_for({'properties':{'scenes':{'items':{'properties':{},'required':[]}}},'required':[]},'stickman')
  required=schema['properties']['scenes']['items']['required'];self.assertIn('cause',required);self.assertIn('consequence',required);self.assertNotIn('hero_object',required);self.assertNotIn('image_query',required)
