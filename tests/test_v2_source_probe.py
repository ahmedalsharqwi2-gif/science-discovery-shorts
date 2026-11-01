import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from production_v2.source_probe import scope,quotations,probe,run,request_urls

class OfficialSourceProbeTests(unittest.TestCase):
 def response(self,status=200,html=None,**headers):
  response=Mock(status_code=status,headers={'Content-Type':'text/html',**headers})
  response.iter_content.return_value=[(html or '<html><title>Official Colosseum</title><main>'+('Documented amphitheatre arches and piers form the historic site. '*15)+'</main></html>').encode()]
  return response
 def test_official_authority_scope_is_strict(self):
  self.assertEqual(scope('https://science.nasa.gov/topic/'),'nasa.gov')
  self.assertEqual(scope('https://www.colosseo.it/en/area/the-colosseum/'),'colosseo.it')
  for url in ['http://whc.unesco.org/en/list/1303/','https://whc.unesco.org.evil.test/article','https://nasa.gov.evil.test/','https://user:pass@colosseo.it/','https://whc.unesco.org/?api_key=secret']:
   with self.assertRaises(ValueError):scope(url)
 def test_get_only_tls_verified_and_no_geometry_inferred(self):
  session=Mock();session.get.return_value=self.response()
  result=probe('https://colosseo.it/en/area/the-colosseum/',session=session)
  self.assertTrue(result['verified']);self.assertEqual(result['http_status'],200)
  self.assertIsNone(result['geometry_inference']);self.assertNotIn('tier_count',result)
  self.assertEqual(len(result['evidence_sha256']),64)
  self.assertTrue(session.get.call_args.kwargs['verify']);self.assertFalse(session.get.call_args.kwargs['allow_redirects'])
  self.assertNotIn('Authorization',session.get.call_args.kwargs['headers'])
  session.post.assert_not_called();session.put.assert_not_called();session.delete.assert_not_called()
 def test_redirects_must_stay_same_official_authority(self):
  session=Mock();session.get.return_value=self.response(302,Location='https://science.nasa.gov/article/')
  with self.assertRaises(ValueError):probe('https://whc.unesco.org/en/list/1303/',session=session)
  self.assertEqual(session.get.call_count,1)
 def test_legitimate_nasa_subdomain_redirect_preserved(self):
  session=Mock();session.get.side_effect=[self.response(301,Location='https://science.nasa.gov/topic/'),self.response()]
  result=probe('https://www.nasa.gov/topic/',session=session)
  self.assertEqual(result['final_url'],'https://science.nasa.gov/topic/')
  self.assertTrue(result['verified'])
 def test_404_keeps_actual_status_and_does_not_invent_replacement(self):
  session=Mock();session.get.return_value=self.response(404)
  result=probe('https://colosseo.it/missing/',session=session)
  self.assertFalse(result['verified']);self.assertEqual(result['http_status'],404)
  self.assertNotIn('excerpts',result);self.assertEqual(session.get.call_count,1)
 def test_quotes_are_bounded_to_six_disjoint_fifteen_word_excerpts(self):
  text=' '.join('arch' if i%20==0 else 'word'+str(i) for i in range(500))
  quotes=quotations(text)
  self.assertEqual(len(quotes),6);self.assertTrue(all(len(q.split())==15 for q in quotes))
  self.assertEqual(sum(len(q.split()) for q in quotes),90)
  self.assertEqual(len({word for quote in quotes for word in quote.split() if word!='arch'}),84)
 def test_canonical_is_recorded_only_in_scope(self):
  html='<html><title>Pontcysyllte</title><link rel="canonical" href="https://whc.unesco.org/en/list/1303/"><main>'+('The canal and iron trough are supported by piers. '*12)+'</main></html>'
  session=Mock();session.get.return_value=self.response(html=html)
  result=probe('https://whc.unesco.org/en/list/1303/',session=session)
  self.assertEqual(result['canonical_url'],'https://whc.unesco.org/en/list/1303/')
  self.assertIsNone(result['geometry_inference'])
 def test_request_limits_and_wrong_profile_reject_before_network(self):
  with tempfile.TemporaryDirectory() as folder:
   request=Path(folder)/'request.json';request.write_text(json.dumps({'profile':'news','urls':['https://whc.unesco.org/en/list/1303/']}))
   with self.assertRaises(ValueError):request_urls(request,'history')
   request.write_text(json.dumps(['https://colosseo.it/']*13))
   with self.assertRaises(ValueError):request_urls(request,'history')
 def test_alias_pages_do_not_double_the_source_quotation_budget(self):
  with tempfile.TemporaryDirectory() as folder:
   request=Path(folder)/'request.json';request.write_text(json.dumps(['https://colosseo.it/one/','https://colosseo.it/two/']))
   session=Mock();session.get.side_effect=[self.response(),self.response()];store=Mock();store.save.return_value='c'*40
   env={'GITHUB_REPOSITORY':'ahmedalsharqwi2-gif/documented-history-stories','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40}
   with patch.dict(os.environ,env,clear=True):report=run('history',request,session=session,store=store)
   self.assertLessEqual(sum(row['quoted_words'] for row in report['sources']),90)
   self.assertEqual(report['sources'][1]['excerpts'],[])
   self.assertTrue(report['sources'][1]['duplicate_source_evidence'])
 def test_ci_report_is_public_evidence_only_and_does_not_call_models(self):
  with tempfile.TemporaryDirectory() as folder:
   request=Path(folder)/'request.json';request.write_text(json.dumps({'profile':'history','urls':['https://whc.unesco.org/en/list/1303/']}))
   session=Mock();session.get.return_value=self.response();store=Mock();store.save.return_value='c'*40
   env={'GITHUB_REPOSITORY':'ahmedalsharqwi2-gif/documented-history-stories','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40,'GITHUB_TOKEN':'secret-not-for-source'}
   with patch.dict(os.environ,env,clear=True):report=run('history',request,session=session,store=store)
   self.assertTrue(report['all_requested_pages_verified']);self.assertTrue(report['no_provider_calls'])
   self.assertNotIn('secret-not-for-source',json.dumps(report));store.save.assert_called_once()

if __name__=='__main__':unittest.main()
