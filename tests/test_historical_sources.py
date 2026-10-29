import json,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import Mock,patch
import requests
from professional_motion import historical_sources as h

def xml(*rows):
    return ('<query>'+''.join('<row><id_number>'+str(i)+'</id_number><category>Cultural</category><site>'+title+'</site><short_description><![CDATA['+desc+']]></short_description></row>' for i,title,desc in rows)+'</query>').encode()

class OfficialHistoricalSourcesTests(unittest.TestCase):
    def test_verified_starters_match_their_actual_structures(self):
        rows=json.loads((h.ROOT/'catalog.json').read_text())['history']
        by_url={r['url']:r for r in rows}
        self.assertEqual(by_url[h.canonical_site(311)]['visual_contract']['tier_count'],2)
        self.assertEqual(by_url[h.canonical_site(344)]['visual_contract']['tier_count'],3)
        self.assertEqual(by_url[h.canonical_site(164)]['visual_contract']['tier_count'],2)
        giza=by_url[h.canonical_site(86)]['visual_contract']
        self.assertNotIn('arch',giza['allowed_modes']);self.assertIn('dome_ribs',giza['forbidden_features'])
        self.assertFalse(any('smarthistory.org' in r['url'] for r in rows))
    def test_xml_never_invents_tier_counts_for_unknown_monuments(self):
        desc='A Roman aqueduct supplies this historic city and is a remarkable survival. '*3
        self.assertEqual(h.parse_candidates(xml((99991,'Historic City',desc))),[])
        self.assertEqual(h.parse_candidates(xml((99991,'Historic City',desc+' The nearby church has two levels.'))),[])
        rows=h.parse_candidates(xml((99991,'Historic City',desc+' The aqueduct has two tiers.')))
        self.assertEqual(rows[0]['visual_contract']['tier_count'],2)
    def test_unsupported_stepped_pyramids_and_generic_domes_are_omitted(self):
        desc='A remarkable architectural monument and important historical survival. '*3
        self.assertEqual(h.parse_candidates(xml((99992,'Maya stepped pyramids',desc),(99993,'Great dome',desc))),[])
    def test_external_xml_url_is_not_trusted_as_a_destination(self):
        body=xml(('311','Segovia','A historic aqueduct and its surrounding city. '*5)).replace(b'</row>',b'<http_url>https://attacker.example/</http_url></row>')
        self.assertEqual(h.parse_candidates(body)[0]['url'],'https://whc.unesco.org/en/list/311/')
        for bad in ['../311','311?redirect=x','https://example.com','0','-4']:
            with self.assertRaises(ValueError):h.canonical_site(bad)
    def test_feed_failure_keeps_verified_topics_and_date_order_is_stable(self):
        fetch=Mock(side_effect=requests.ConnectionError('unavailable'))
        rows=h.candidates(fetch=fetch)
        self.assertEqual(len(rows),4)
        reply=Mock(content=xml((99991,'Two-level Aqueduct','A historic aqueduct and important ancient route. '*4+' This structure has two levels.')))
        reply.raise_for_status.return_value=None
        now=datetime(2026,10,29,tzinfo=timezone.utc)
        self.assertEqual(h.candidates(now,Mock(return_value=reply)),h.candidates(now,Mock(return_value=reply)))


class SourcePipelineIntegrationTests(unittest.TestCase):
    def test_history_candidates_use_verified_official_bank(self):
        from professional_motion import editorial as e
        sentinel=[{'key':'official-site'}]
        with patch.object(h,'candidates',return_value=sentinel) as provider,patch.object(e.requests,'get',side_effect=AssertionError('legacy feed must not run')):
            self.assertEqual(e.candidates('history'),sentinel);provider.assert_called_once_with()
    def test_pyramid_contract_rejects_arch_scene_before_generation(self):
        from professional_motion import editorial as e
        row={'family':'architecture','variant':'pyramid','visual_contract':h.visual_contract('86','','')}
        scene={'label':'حجر الهرم','narration':' '.join(['ده']*30),'visual_mode':'arch','labels':[]}
        with self.assertRaisesRegex(ValueError,'structure contract'):
            e.validate({'suitable':True,'title':'حجر الهرم','scenes':[dict(scene) for _ in range(8)]},'history',row)
    def test_structure_contract_survives_into_render_story(self):
        from professional_motion import editorial as e
        row={'key':'giza','family':'architecture','variant':'pyramid','url':h.canonical_site(86),'publisher':'UNESCO','visual_contract':h.visual_contract('86','','')}
        narration=' '.join(('ده مش حجر عشان اللي جوه الهرم').split()*5)
        scene={'label':'حجر الهرم','narration':narration,'visual_mode':'section','labels':[]}
        story={'suitable':True,'title':'حجر الهرم','scenes':[dict(scene) for _ in range(8)],'hashtags':['الهرم','حجر','تاريخ']}
        result=e.validate(story,'history',row)
        self.assertEqual(result['visual_contract'],row['visual_contract'])
        self.assertIsNot(result['visual_contract'],row['visual_contract'])

if __name__=='__main__':unittest.main()
