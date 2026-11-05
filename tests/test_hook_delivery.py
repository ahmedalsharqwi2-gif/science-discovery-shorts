import pytest
from scripts.verify_hook import verify

def ass(path,start,text):
 path.write_text('[Events]\nDialogue: 0,'+start+',0:00:02.00,Default,,0,0,0,,'+text+'\n');return path

def test_exact_frame_zero_hook_passes(tmp_path):assert verify(ass(tmp_path/'c.ass','0:00:00.00','مش كل ضوء أبيض'),'مش كل ضوء أبيض')['passed']
@pytest.mark.parametrize('start,text',[('0:00:00.10','مش كل ضوء أبيض'),('0:00:00.00','مقدمة مختلفة')])
def test_wrong_time_or_text_fail(tmp_path,start,text):
 with pytest.raises(ValueError):verify(ass(tmp_path/'c.ass',start,text),'مش كل ضوء أبيض')
