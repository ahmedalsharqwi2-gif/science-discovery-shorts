import pytest
from visual_contract import load_template
from remotion_factory.packaging import locked_public_title

def test_locked_title_prefix_is_idempotent_and_keeps_exact_brand():
 t=load_template();title='ليه الضوء بيغيّر اتجاهه؟';value=locked_public_title(title,t['channel']);assert value==t['public_title_prefix']+title;assert locked_public_title(value,t['channel'])==value

def test_long_title_is_rejected_not_truncated():
 with pytest.raises(ValueError):locked_public_title('كلمة '*40,load_template()['channel'])
