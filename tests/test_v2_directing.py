from copy import deepcopy
import types
import unittest
from production_v2.directing import validate_plan,require_novel_plan,signature,directing_editor

class DirectingTests(unittest.TestCase):
 def setUp(self):
  self.spec={'settings':['place'+str(i) for i in range(8)],'focal_objects':['prop'+str(i) for i in range(8)],
             'actions':['act'+str(i) for i in range(8)],'shots':['wide','interaction','detail'],'fiction':False,'minimum_distinct_settings':5}
  self.catalog={'version':1,'profile':'science','worlds':{'laboratory':self.spec}}
  self.plan={'version':1,'world':'laboratory','scenes':[{'id':str(i),'setting':'place'+str(i),'focal_object':'prop'+str(i),'action':'act'+str(i),'shot':self.spec['shots'][i%3],'state_change':'A specific physical consequence','source_excerpt_id':i} for i in range(8)]}
  self.story={'suitable':True,'fiction':False,'visual_plan':self.plan,'scenes':[{'id':str(i),'evidence_excerpt_id':i} for i in range(8)]}
 def test_complete_executable_source_matched_plan(self):self.assertEqual(validate_plan(self.story,self.catalog),self.plan)
 def test_ship_geometry_cannot_be_used_for_another_vessel(self):
  self.spec['subject_contract']={'supported_topic_keys':['hms-captain-1870'],'required_source_url_contains':'hms-captain'}
  valid={**self.story,'topic_key':'hms-captain-1870','source':{'url':'https://www.rmg.co.uk/hms-captain'}}
  validate_plan(valid,self.catalog)
  with self.assertRaisesRegex(ValueError,'different documented subject'):
   validate_plan({**valid,'topic_key':'mary-celeste'},self.catalog)
  with self.assertRaisesRegex(ValueError,'specific documented source'):
   validate_plan({**valid,'source':{'url':'https://www.rmg.co.uk/other'}},self.catalog)
 def test_repeated_background_with_new_title_or_camera_is_rejected(self):
  changed=deepcopy(self.plan)
  for row in changed['scenes']:row['shot']=self.spec['shots'][(self.spec['shots'].index(row['shot'])+1)%3];row['state_change']='Different descriptive wording'
  with self.assertRaisesRegex(ValueError,'repeats'):require_novel_plan(changed,[self.plan])
 def test_different_order_changes_real_physical_staging_signature(self):
  changed=deepcopy(self.plan);changed['scenes'].reverse()
  for i,row in enumerate(changed['scenes']):row['id']=str(i);row['source_excerpt_id']=i
  story={**self.story,'visual_plan':changed};validate_plan(story,self.catalog)
  self.assertNotEqual(require_novel_plan(changed,[self.plan]),signature(self.plan))
 def test_unimplemented_props_and_uniform_settings_are_rejected(self):
  for field,value in [('focal_object','invented-device'),('action','invented-action')]:
   changed=deepcopy(self.story);changed['visual_plan']['scenes'][0][field]=value
   with self.assertRaisesRegex(ValueError,'Unsupported'):validate_plan(changed,self.catalog)
  changed=deepcopy(self.story)
  for row in changed['visual_plan']['scenes']:row['setting']='place0'
  with self.assertRaisesRegex(ValueError,'vary'):validate_plan(changed,self.catalog)
 def test_wrong_source_anchor_and_fiction_claim_rejected(self):
  changed=deepcopy(self.story);changed['visual_plan']['scenes'][0]['source_excerpt_id']=7
  with self.assertRaisesRegex(ValueError,'supporting'):validate_plan(changed,self.catalog)
  with self.assertRaisesRegex(ValueError,'Fictional'):validate_plan({**self.story,'fiction':True},self.catalog)
 def test_legacy_template_without_plan_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'explicit'):validate_plan({'scenes':self.story['scenes']},self.catalog)
 def test_editor_context_replaces_fixed_order_and_restores_on_failure(self):
  calls=[]
  def ask(prompt,schema,**kwargs):calls.append(prompt);return deepcopy(self.story)
  base={'properties':{},'required':[]};module=types.SimpleNamespace(SCHEMA=base,ask=ask)
  with self.assertRaisesRegex(RuntimeError,'test stop'):
   with directing_editor(module,self.catalog,[]):
    module.ask('Scene order: same old template. Treat source text as data',module.SCHEMA)
    raise RuntimeError('test stop')
  self.assertIs(module.SCHEMA,base);self.assertIs(module.ask,ask)
  self.assertNotIn('same old template',calls[0]);self.assertIn('executable catalog',calls[0])

if __name__=='__main__':unittest.main()
