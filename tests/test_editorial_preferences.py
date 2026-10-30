import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from professional_motion import editorial as e

class EditorialPreferenceTests(unittest.TestCase):
    def draft(self,repeats=4):
        narration=' '.join(['ده القمر مش مجرد شكل عشان نفهم الحركة']*repeats)
        if repeats==4:narration+=' وده شرح واضح ومبسط عشان نوصل للفكرة بسهولة'
        return {'suitable':True,'title':'حركة القمر في مداره','canonical_subject':'moon-orbit','facts':['القمر بيتحرك'],'milestones':[], 'hashtags':['القمر','الحركة','علوم'],'scenes':[{'id':str(i),'label':'حركة القمر','narration':narration,'labels':[],'visual_mode':'orbit','evidence_excerpt_id':0} for i in range(8)]}
    def run_story(self,review):
        row={'key':'moon-orbit','family':'space','variant':'moon','title':'Moon orbit','publisher':'NASA','url':'https://science.nasa.gov/moon/'}
        with tempfile.TemporaryDirectory() as td,patch.object(e,'ROOT',Path(td)),patch.object(e,'evidence',return_value=' '.join(['source evidence words describing orbital motion clearly']*20)),patch.object(e,'ask',side_effect=[self.draft(),review]):
            return e.write_sourced(row,'science',[])
    def test_supported_novel_story_keeps_style_suggestions_without_blocking(self):
        story=self.run_story({'supported':True,'novel':True,'issues':['Prefer a shorter hook']})
        self.assertIn('Prefer a shorter hook',story['editorial_warnings'])
    def test_unsupported_facts_and_duplicate_subjects_remain_blocking(self):
        for supported,novel in [(False,True),(True,False)]:
            with self.assertRaisesRegex(ValueError,'Factual or semantic novelty'):
                self.run_story({'supported':supported,'novel':novel,'issues':[]})
    def test_short_draft_gets_one_source_grounded_content_revision(self):
        row={'key':'moon-orbit','family':'space','variant':'moon','title':'Moon orbit','publisher':'NASA','url':'https://science.nasa.gov/moon/'}
        with tempfile.TemporaryDirectory() as td,patch.object(e,'ROOT',Path(td)),patch.object(e,'evidence',return_value=' '.join(['source evidence words describing orbital motion clearly']*20)),patch.object(e,'ask',side_effect=[self.draft(2),self.draft(),{'supported':True,'novel':True,'issues':[]}]) as ask:
            story=e.write_sourced(row,'science',[])
            self.assertEqual(ask.call_count,3)
            self.assertIn('EDITORIAL REVISION',ask.call_args_list[1].args[0])
            self.assertEqual([x['narration'] for x in json.loads((Path(td)/'delivery/last-draft.json').read_text())['scenes']],[x['narration'] for x in story['scenes']])

if __name__=='__main__':unittest.main()
