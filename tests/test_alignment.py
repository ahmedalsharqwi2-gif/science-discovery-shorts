import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('alignment',Path(__file__).parents[1]/'pipeline/forced_align.py')
alignment=importlib.util.module_from_spec(spec)
spec.loader.exec_module(alignment)

class AlignmentTests(unittest.TestCase):
    def test_orthography_does_not_replace_original_words(self):
        cfg={'minCharacterSimilarity':.85,'minWordCoverage':.65}
        alignment.verify_speech('المعلومة دي واضحة','المعلومه دي واضحه',cfg)
        result=alignment.measured_original_words('المعلومة دي واضحة',[{'word':'المعلومة','start':0,'end':.5},{'word':'دي','start':.5,'end':.8},{'word':'واضحة','start':.8,'end':1.3}],1.3)
        self.assertEqual([w['text'] for w in result],['المعلومة','دي','واضحة'])
    def test_other_speech_or_missing_numerals_fail(self):
        cfg={'minCharacterSimilarity':.85,'minWordCoverage':.65}
        for original,heard in [('المجرة بتبعد 12 سنة ضوئية','النهارده الجو جميل في القاهرة'),('المسافة 12 سنة ضوئية','المسافة 13 سنة ضوئية')]:
            with self.assertRaisesRegex(alignment.AlignmentError,'SPEECH_MISMATCH'):alignment.verify_speech(original,heard,cfg)
    def test_subwords_merge_actual_spans(self):
        result=alignment.measured_original_words('بالضوء',[{'word':'بال','start':.1,'end':.2},{'word':'ضوء','start':.2,'end':.7}],1)
        self.assertEqual(result,[{'text':'بالضوء','start':.1,'end':.7}])
    def test_unsplittable_or_zero_duration_is_rejected(self):
        with self.assertRaisesRegex(alignment.AlignmentError,'WORD_BOUNDARY_UNRESOLVED'):alignment.measured_original_words('في المجرة',[{'word':'في المجرة','start':.1,'end':1}],1)
        with self.assertRaisesRegex(alignment.AlignmentError,'INVALID_MEASURED_SPAN'):alignment.measured_original_words('مجرة',[{'word':'مجرة','start':1,'end':1}],2)
    def test_small_overshoot_past_duration_clamps_but_large_overshoot_fails(self):
        result=alignment.measured_original_words('مجرة',[{'word':'مجرة','start':.8,'end':2.4}],2)
        assert result[0]['end']==2
        with self.assertRaisesRegex(alignment.AlignmentError,'INVALID_MEASURED_SPAN'):alignment.measured_original_words('مجرة',[{'word':'مجرة','start':.8,'end':2.6}],2)

if __name__=='__main__':unittest.main()
