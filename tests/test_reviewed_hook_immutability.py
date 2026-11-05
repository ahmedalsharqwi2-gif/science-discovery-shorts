from unittest.mock import Mock
import pytest
from remotion_factory.editorial_recovery import checked_draft

def run(draft,corrected):
 state={'episodes':{'slot':{}}}
 def mutate(fn):fn(state)
 def validate(story,*args):
  if story['length']>10:raise ValueError('shorten existing prose')
  assert story['visual_template_version']==1
  assert story['hook_review']=={'supported':True}
 return checked_draft('slot',draft,'science','source',{},validate,Mock(return_value=corrected),{},state['episodes']['slot'],mutate,Mock(return_value={'path':'correction','sha256':'fixture'}))

def draft():return {'canonical_subject':'same-topic','length':20,'hook_line':'مش كل ضوء أبيض','hook_evidence_quote':'same quote','hook_source_terms':['ضوء'],'hook_review':{'supported':True},'visual_template_version':1}
def test_repair_cannot_change_the_separately_reviewed_hook():
 old=draft()
 with pytest.raises(ValueError,match='failed validation'):run(old,{**old,'length':5,'hook_line':'مفيش معلومة مؤكدة'})
def test_repair_cannot_drop_the_version_or_review_proof():
 old=draft();corrected={'canonical_subject':'same-topic','length':5,'hook_line':old['hook_line']};out=run(old,corrected)
 assert out['visual_template_version']==1 and out['hook_review']==old['hook_review']
def test_repair_cannot_downgrade_the_version():
 old=draft()
 with pytest.raises(ValueError,match='failed validation'):run(old,{**old,'length':5,'visual_template_version':0})
