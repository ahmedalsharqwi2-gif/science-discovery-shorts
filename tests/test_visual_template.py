import json,pytest
from visual_contract import load_template
EXPECTED={'bg': '#e5f2ed', 'ink': '#153e40', 'accent': '#179ca6', 'secondary': '#d9a441'}
def test_palette_is_the_exact_owner_approved_palette():
 t=load_template();assert type(t['version']) is int;assert t['palette']==EXPECTED
@pytest.mark.parametrize('change',['missing','version','malformed','safe_zone'])
def test_template_errors_are_fatal(tmp_path,change):
 p=tmp_path/'template.json';t=load_template()
 if change=='version':t['version']=999
 if change=='safe_zone':t.pop('safe_zone')
 if change!='missing':p.write_text('{bad' if change=='malformed' else json.dumps(t))
 with pytest.raises((ValueError,FileNotFoundError)):load_template(p)
