from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_visual_fx_is_offline_and_unbranded():
    fx=(ROOT/'professional_motion/visual_fx.js').read_text()
    assert 'applyVisualFX' in fx
    assert 'Manus' not in fx
    assert 'http://' not in fx and 'https://' not in fx
def test_scene_calls_visual_fx_after_overlay():
    s=(ROOT/'professional_motion/scene.js').read_text()
    assert 'window.applyVisualFX' in s
    assert 'window.__fxTime=time' in s
