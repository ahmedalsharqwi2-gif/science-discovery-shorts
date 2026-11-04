import unittest
from unittest.mock import patch
from remotion_factory import author
class LegacyTopicIdentity(unittest.TestCase):
 def test_source_url_survives_old_and_new_ledger_shapes(self):
  urls,topics=author.prior_identifiers([{'source':'https://example.org/legacy','canonical_subject':'old-topic'},{'source':{'url':'https://example.org/new'},'canonical_subject':'new-topic'},{'source':None},'legacy narrative'])
  self.assertEqual(urls,{'https://example.org/legacy','https://example.org/new'})
  self.assertEqual(topics,{'old-topic','new-topic'})
 def test_legacy_story_text_does_not_replace_the_identity_record(self):
  row={'story':'old narration text','source':'https://example.org/old','canonical_subject':'retain-me'}
  with patch.object(author,'local',return_value={'episodes':{'old':row}}),patch.object(author.Path,'exists',return_value=False):
   rows=author.used()
  self.assertEqual(author.prior_identifiers(rows),({'https://example.org/old'},{'retain-me'}))
