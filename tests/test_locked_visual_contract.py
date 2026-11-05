import json,pytest
from visual_contract import *
def test_template_identity():
 t=load_template();assert t['locked'] and type(t['version']) is int
 assert t['safe_zone']['caption_y_bottom']==1248
 assert t['safe_zone']['art_stage']['min_scale_vs_reference']==.85
def test_missing_and_unknown(tmp_path):
 with pytest.raises(FileNotFoundError):load_template(tmp_path/'missing.json')
 t=load_template();t['version']=900;p=tmp_path/'unknown.json';p.write_text(json.dumps(t))
 with pytest.raises(ValueError):load_template(p)
 t=load_template();t.pop('safe_zone');p.write_text(json.dumps(t))
 with pytest.raises(ValueError):load_template(p)
def test_bounds_and_lower_band():
 assert_in_safe_zone('caption',(190,1120,780,1248))
 for b in [(190,1400,780,1560),(100,300,500,400),(190,900,850,970)]:
  with pytest.raises(ValueError):assert_in_safe_zone('caption',b)
 assert_in_safe_zone('mark',(190,140,400,180),kind='chrome')
 with pytest.raises(ValueError):assert_in_safe_zone('mark',(190,140,400,180),kind='text')
def test_focal_collision_and_scale():
 with pytest.raises(ValueError):validate_scene_boxes((190,300,600,400),None,(250,350,700,800),scale=1)
 with pytest.raises(ValueError):validate_scene_boxes(None,None,(200,520,700,1000),scale=.65)
def test_accent():
 assert validate_accent('3 حقائق عن الماء','الماء')=='الماء'
 for x in ([],['الماء','حقائق']):
  with pytest.raises(ValueError):validate_accent('3 حقائق عن الماء','الماء',colored_words=x)
 with pytest.raises(ValueError):validate_accent('الماء والماء','')
@pytest.mark.parametrize('opening',BANNED_OPENINGS)
def test_banned(opening):
 with pytest.raises(ValueError):validate_hook(opening+' 3 حقائق',max_words=14,profile='science')
def test_hook_requires_fact():
 assert validate_hook('3 حاجات بتغيّر لون السما',max_words=14,profile='science')
 with pytest.raises(ValueError):validate_hook('كلام جميل ومهم',max_words=14,profile='science')
 with pytest.raises(ValueError):validate_hook('3 '+ 'كلمة '*20,max_words=14,profile='science')
def test_evidence_review_is_not_invented():
 with pytest.raises(ValueError):require_source_support('3 حاجات','quote','other text',{'supported':True})
