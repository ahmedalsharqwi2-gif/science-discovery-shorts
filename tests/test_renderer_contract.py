import ast,json,re,unittest
from pathlib import Path
from professional_motion.speech_lexicon import recognized_key

class RendererContractTests(unittest.TestCase):
    def test_writer_catalog_is_implemented_by_the_real_renderer(self):
        root=Path(__file__).resolve().parents[1]/'professional_motion'
        tree=ast.parse((root/'requested_editorial.py').read_text())
        declared={n.targets[0].id:set(ast.literal_eval(n.value)) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('ASSETS','MOTIONS')}
        source=(root/'procedural_story.js').read_text()
        for name,allowed in declared.items():
            found=re.search(r'const '+name+r'=new Set\((\[[^\n]+?\])\)',source)
            self.assertIsNotNone(found,name)
            actual=set(ast.literal_eval(found[1]));self.assertFalse(allowed-actual,f'{name} promised but not implemented: {allowed-actual}')
    def test_numeric_values_and_real_names_are_not_treated_as_missing_speech(self):
        self.assertEqual(recognized_key('49'),recognized_key('تسعة وأربعين'))
        self.assertEqual(recognized_key('Hugging'),recognized_key('هاجينغ'))
        self.assertEqual(recognized_key('VLLM'),recognized_key('في إل إل إم'))
        self.assertNotEqual(recognized_key('49'),recognized_key('82'))
        self.assertNotEqual(recognized_key('نموذج'),recognized_key('خبراء'))
if __name__=='__main__':unittest.main()
