import unittest
from news.editor import canonical,date,validate
class NewsIntegrityTests(unittest.TestCase):
 def test_unofficial_source_is_rejected(self):
  with self.assertRaises(ValueError):canonical('https://example.com/fake-news')
 def test_links_drop_tracking_not_identity(self):
  self.assertEqual(canonical('https://huggingface.co/blog/new?utm=x#f'),'https://huggingface.co/blog/new')
 def test_date_has_timezone(self):self.assertIsNotNone(date('2026-10-20T09:00:00Z').tzinfo)
 def test_spoken_digits_are_rejected(self):
  p={'scenes':[{'title':'خبر','kind':'cards','labels':['حقيقة'],'narration':('كلام مصري '*14)+' 123'} for _ in range(6)]}
  with self.assertRaisesRegex(ValueError,'numbers'):validate(p,{'article':'مصدر'})
if __name__=='__main__':unittest.main()
