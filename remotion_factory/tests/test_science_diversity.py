import copy,unittest
from remotion_factory.science_topics import balanced,domain
class ScientificBreadth(unittest.TestCase):
 def test_a_space_streak_prefers_an_available_different_science(self):
  rows=[{'title':'NASA planet discovery'},{'title':'How soap removes oil'}];history=[{'title':'NASA black hole'},{'title':'New galaxy observation'}]
  self.assertEqual(balanced(rows,history)[0]['science_domain'],'chemistry')
 def test_one_available_domain_still_produces_instead_of_waiting_for_a_quota(self):
  self.assertEqual(len(balanced([{'title':'NASA discovery'}],[{'title':'NASA discovery'}])),1)
 def test_rotation_does_not_change_the_reserved_subject_identity_or_mutate_input(self):
  rows=[{'title':'Plant biology','canonical_subject':'original-plant-subject'}];before=copy.deepcopy(rows);result=balanced(rows,[]);self.assertEqual(rows,before);self.assertEqual(result[0]['canonical_subject'],'original-plant-subject')

 def test_legacy_string_sources_and_null_selection_remain_readable(self):
  self.assertEqual(domain({'title':'Old topic','source':'https://www.nasa.gov/','source_selection':None}),'astronomy')
