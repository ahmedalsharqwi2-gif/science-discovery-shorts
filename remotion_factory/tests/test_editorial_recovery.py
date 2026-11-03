"""Exercise durable correction and its mandatory independent-review handoff."""
import copy
import unittest
from unittest.mock import Mock
from remotion_factory.editorial_recovery import checked_draft


class DraftRecovery(unittest.TestCase):
    def setUp(self):
        self.state = {'episodes': {'slot': {}}}
        self.draft = {'canonical_subject': 'retained-original-topic', 'words': 500}
        self.fixed = {**self.draft, 'words': 290}
        self.ask = Mock(return_value=self.fixed)
        self.write = Mock(return_value={'path': 'retained-correction', 'sha256': 'hash'})

    @staticmethod
    def validate(draft, profile, source):
        if not 240 <= draft['words'] <= 370:
            raise ValueError('Draft word budget fails')

    def mutate(self, callback):
        callback(self.state)

    def run_recovery(self, draft=None):
        return checked_draft('slot', draft or self.draft, 'science', 'Source facts',
                             {'title': 'Retained topic'}, self.validate, self.ask, {},
                             copy.deepcopy(self.state['episodes']['slot']),
                             self.mutate, self.write)

    def test_valid_draft_never_spends_a_correction_request(self):
        self.assertEqual(self.run_recovery(self.fixed), self.fixed)
        self.ask.assert_not_called()

    def test_intent_is_durable_before_request_and_valid_response_is_retained(self):
        def response(*args):
            self.assertEqual(self.state['episodes']['slot']['draft_repair']['phase'], 'requested')
            return self.fixed
        self.ask.side_effect = response
        self.assertEqual(self.run_recovery(), self.fixed)
        self.assertEqual(self.state['episodes']['slot']['draft_repair']['phase'], 'validated')
        self.assertEqual(self.state['episodes']['slot']['draft_document']['path'], 'retained-correction')
        self.run_recovery(self.fixed)
        self.assertEqual(self.ask.call_count, 1)

    def test_timeout_never_repeats_an_uncertain_correction(self):
        self.ask.side_effect = TimeoutError('Unknown provider result')
        with self.assertRaises(TimeoutError): self.run_recovery()
        with self.assertRaisesRegex(ValueError, 'no second repair'): self.run_recovery()
        self.assertEqual(self.ask.call_count, 1)

    def test_rejected_correction_is_retained_and_never_repeated(self):
        self.ask.return_value = self.draft
        with self.assertRaisesRegex(ValueError, 'failed validation'): self.run_recovery()
        self.write.assert_called_once()
        self.assertEqual(self.state['episodes']['slot']['draft_repair']['phase'], 'rejected')
        with self.assertRaisesRegex(ValueError, 'no second repair'): self.run_recovery()
        self.assertEqual(self.ask.call_count, 1)

    def test_correction_cannot_switch_to_a_different_topic(self):
        self.ask.return_value = {**self.fixed, 'canonical_subject': 'some-other-topic'}
        with self.assertRaisesRegex(ValueError, 'failed validation'): self.run_recovery()
        self.assertNotIn('draft_document', self.state['episodes']['slot'])



class AuthorIntegration(unittest.TestCase):
    def test_repaired_script_still_receives_the_original_independent_review(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from remotion_factory import author as module
        scene={'label':'تفسير واضح','narration':' '.join(['كلمة']*55),'labels':['فكرة','تفسير'],'diagram':'flow','evidence_quote':'a short supported source quote'}
        bad={'title':'عنوان الحلقة','cover_text':'الفكرة واضحة','canonical_subject':'retained-original-topic','hashtags':['علم','تاريخ','معلومة'],'scenes':[copy.deepcopy(scene) for _ in range(8)]}
        good=copy.deepcopy(bad)
        for scene in good['scenes']:scene['narration']=' '.join(['كلمة']*34)
        state={'episodes':{'slot':{'raw_draft':bad,'source_selection':{'title':'موضوع الحلقة'},'source_text':'a short supported source quote','status':'draft_retained'}}}
        def mutate(fn):fn(state)
        review={'supported':True,'engaging':True,'novel':True,'visuals_match':True,'issues':[]}
        with tempfile.TemporaryDirectory() as folder,patch.object(module,'local',side_effect=lambda:state),patch.object(module,'mutate',side_effect=mutate),patch.object(module,'used',return_value=[]),patch.object(module,'document_write',return_value={'path':'retained','sha256':'hash'}),patch.object(module,'ask_once',side_effect=[good,review]) as ask,patch.object(module,'Path',side_effect=lambda value:Path(folder)/value):
            result=module.author({'slot':'slot','profile':'history'}, {})
        self.assertEqual(result['canonical_subject'],bad['canonical_subject'])
        self.assertEqual(ask.call_count,2)
        self.assertTrue(ask.call_args.kwargs.get('review',ask.call_args.args[2] if len(ask.call_args.args)>2 else False))
        self.assertTrue(state['episodes']['slot']['editorial_review']['passed'])

if __name__ == '__main__': unittest.main()
