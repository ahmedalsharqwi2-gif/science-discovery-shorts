import pytest
from PIL import Image,ImageDraw
from visual_contract import assert_in_safe_zone,load_template,validate_scene_boxes
from scripts.verify_safe_area import pixel_boxes

def test_bottom_1248_passes():assert_in_safe_zone('caption',(190,1100,780,1248))
@pytest.mark.parametrize('box',[(190,1400,780,1560),(100,500,600,550),(190,900,850,1000)])
def test_obscured_text_fails(box):
 with pytest.raises(ValueError):assert_in_safe_zone('caption',box)
def test_chrome_is_not_load_bearing_text():
 assert_in_safe_zone('brand',(190,140,780,175),kind='chrome')
 with pytest.raises(ValueError):assert_in_safe_zone('title',(190,140,780,175),kind='text')
def test_pixel_mask_cannot_lie_using_a_safe_declared_box():
 t=load_template();im=Image.new('RGB',(1080,1920));d=ImageDraw.Draw(im);d.rectangle((100,900,750,1000),fill=t['layout']['mask_colors']['caption'])
 measured=pixel_boxes(im,t)['caption'];assert measured[0]==100
 with pytest.raises(ValueError):assert_in_safe_zone('caption',measured)
def test_focal_collision_and_too_small_subject_fail():
 with pytest.raises(ValueError):validate_scene_boxes((190,340,800,500),None,(300,480,750,1000),scale=.9)
 with pytest.raises(ValueError):validate_scene_boxes((190,340,800,500),None,(300,520,750,1000),scale=.65)

def test_platform_overlay_can_reject_a_pixel_inside_rounded_template_bounds():
 from scripts.verify_safe_area import validate_platform_boxes
 with pytest.raises(ValueError,match='shorts'):validate_platform_boxes({'title':(889,500,890,550)})
