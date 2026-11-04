import unittest
from remotion_factory.evidence_excerpt import narrow_excerpts,literal_excerpt
class LiteralExcerptNormalization(unittest.TestCase):
 def test_long_literal_excerpt_is_narrowed_without_touching_narration(self):
  quote=' '.join('word'+str(i) for i in range(30));draft={'scenes':[{'narration':'نفس الكلام الأصلي بلا أي تعديل','evidence_quote':quote}]}
  result=narrow_excerpts(draft,quote)
  self.assertLessEqual(len(result['scenes'][0]['evidence_quote'].split()),18)
  self.assertIn(result['scenes'][0]['evidence_quote'],quote)
  self.assertEqual(result['scenes'][0]['narration'],draft['scenes'][0]['narration'])
  self.assertEqual(draft['scenes'][0]['evidence_quote'],quote)
 def test_nonexistent_evidence_is_not_replaced_with_unrelated_source(self):
  quote='an entirely invented unsupported scientific claim'
  self.assertEqual(literal_excerpt(quote,'a different actual source paragraph with other words'),quote)
 def test_valid_literal_short_quote_is_unchanged(self):
  self.assertEqual(literal_excerpt('the actual original source words','prefix the actual original source words suffix'),'the actual original source words')
