from unittest.mock import Mock,patch
import pytest
from remotion_factory import hook_first as module
from visual_contract import load_template

def test_hook_is_requested_and_retained_before_any_title_or_scene_job():
 profile=load_template()['channel'];state={'episodes':{'slot':{}}};saved={}
 hook={'hook_line':'رفعت 3 حدود جديدة','source_terms':[],'evidence_quote':'supported source evidence'}
 def mutate(fn):fn(state)
 def ask(*args,**kwargs):
  assert state['episodes']['slot']['hook_request_started']
  assert not state['episodes']['slot'].get('draft_document')
  return {'supported':True,'issues':[]} if kwargs.get('review') else hook
 def write(slot,kind,value):saved.update(value);assert kind=='hook';return {'path':'hook','sha256':'measured-test-hash'}
 with patch.dict('os.environ',{'GITHUB_RUN_ID':'123'}),patch.object(module,'local',return_value=state),patch.object(module,'mutate',side_effect=mutate),patch.object(module,'document_write',side_effect=write):
  out=module.first_hook('slot',profile,{},'supported source evidence',ask)
  assert next(iter(out))=='hook_line'
  assert state['episodes']['slot']['hook_document']['path']=='hook'
  assert saved['hook_line']==hook['hook_line']

def test_uncertain_hook_request_cannot_be_repeated():
 state={'episodes':{'slot':{'hook_request_started':True}}};ask=Mock()
 with patch.object(module,'local',return_value=state):
  with pytest.raises(ValueError,match='Unacknowledged'):module.first_hook('slot',load_template()['channel'],{},'source',ask)
 ask.assert_not_called()
