import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from remotion_factory.packaging import metadata, clean_title, sha, verify
from remotion_factory.publish import submit_one


class PublicationPackage(unittest.TestCase):
 def test_serialized_or_truncated_titles_stop_before_generation(self):
  for value in ('[', '{', ['علم'], {'title':'علم'}, 'عنوان '+('طويل '*30), 'عنوان [من مصفوفة]'):
   with self.subTest(value=value), self.assertRaises(ValueError):clean_title(value)

 def test_retained_title_keeps_its_meaning_and_new_cover_is_short(self):
  story={'profile':'science','title':'اسرار الكون | إزاي الصوت بينتقل في الهوا؟'}
  result=metadata(story,'story-digest')
  self.assertEqual(result['title'],'إزاي الصوت بينتقل في الهوا؟')
  self.assertEqual(result['cover_text'],result['title'])
  story['cover_text']='الصوت بيوصل إزاي؟'
  self.assertEqual(metadata(story,'story-digest')['cover_offset_ms'],200)
  story['cover_text']=' '.join(['كلمة']*8)
  with self.assertRaises(ValueError):metadata(story,'story-digest')

 def make_proof(self,root):
  package=metadata({'profile':'science','title':'إزاي الصوت بينتقل؟','cover_text':'الصوت بيوصل إزاي؟'},'script-sha')
  (root/'publication.json').write_text(json.dumps(package,ensure_ascii=False))
  Image.new('RGB',(1080,1920),'navy').save(root/'cover.png')
  return {'profile':'science','story_sha256':'script-sha','publication':package,'renderer':{'publication_sha256':sha(root/'publication.json'),'cover_sha256':sha(root/'cover.png')}}

 def test_recovered_cover_must_match_the_exact_story_and_bytes(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);report=self.make_proof(root)
   self.assertEqual(verify(root,report)['title'],'إزاي الصوت بينتقل؟')
   report['story_sha256']='another-story'
   with self.assertRaisesRegex(ValueError,'another episode'):verify(root,report)
   report['story_sha256']='script-sha'
   Image.new('RGB',(1080,1920),'red').save(root/'cover.png')
   with self.assertRaisesRegex(ValueError,'Cover image changed'):verify(root,report)

 def test_packaged_movie_cannot_drop_proof_but_legacy_movie_is_unchanged(self):
  self.assertIsNone(verify(Path('.'),{'renderer':{}}))
  with self.assertRaisesRegex(ValueError,'proof missing'):verify(Path('.'),{'renderer':{'publication_sha256':'expected'}})

 @patch('remotion_factory.publish.lookup')
 @patch('remotion_factory.publish.query')
 @patch('remotion_factory.publish.queued',return_value=[])
 def test_only_instagram_gets_supported_cover_frame_and_retry_sends_once(self,queued,query,lookup):
  due='2026-11-05T15:00:00Z';url='https://example.org/complete.mp4'
  package=metadata({'profile':'science','title':'إزاي الصوت بينتقل؟'},'script-sha')
  for service in ('youtube','facebook','instagram'):
   with self.subTest(service=service):
    query.reset_mock();query.return_value={'createPost':{'post':{'id':'accepted'}}}
    lookup.return_value={'id':'accepted','channelId':'owned','status':'scheduled','dueAt':due,'assets':[{'source':url}]}
    record={};saved=[]
    submit_one(service,{'channel':'owned'},due,url,package['title'],'وصف الحلقة',record,lambda:saved.append(dict(record)),package)
    payload=query.call_args.args[1]['input']
    asset=payload['assets'][0]['video']
    self.assertEqual(asset.get('metadata'),{'thumbnailOffset':200} if service=='instagram' else None)
    if service=='youtube':self.assertEqual(payload['metadata']['youtube']['title'],package['title'])
    self.assertEqual(saved[0]['phase'],'intent');self.assertEqual(record['phase'],'verified')
    submit_one(service,{'channel':'owned'},due,url,package['title'],'وصف الحلقة',record,lambda:None,package)
    self.assertEqual(query.call_count,1)


if __name__=='__main__':unittest.main()
