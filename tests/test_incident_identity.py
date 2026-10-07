import tempfile
import unittest
from pathlib import Path
from scripts.topic_history import TopicHistory, find_duplicate

class IncidentIdentityTests(unittest.TestCase):
    def test_incident_identity_survives_restart_and_reworded_title(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            episode = {"title": "الليلة التي تغير فيها كل شيء", "verification_report": {"case_name": "حادثة ماري سيليست", "location": "المحيط الأطلسي"}}
            TopicHistory(path).reserve(episode)
            candidate = {"title": "رحلة لم تصل إلى نهايتها", "verification_report": {"case_name": "حادثة ماري سيليست"}}
            self.assertIsNotNone(find_duplicate(candidate, TopicHistory(path).entries))

    def test_same_place_different_incident_is_allowed(self):
        prior = [{"title": "ثوران فيزوف", "historical_verification_report": {"event_name": "ثوران فيزوف", "location": "إيطاليا"}}]
        new = {"title": "حريق روما", "historical_verification_report": {"event_name": "حريق روما", "location": "إيطاليا"}}
        self.assertIsNone(find_duplicate(new, prior))

    def test_legacy_titles_still_block_duplicates(self):
        self.assertIsNotNone(find_duplicate({"title": "اختفاء بعثة فرانكلين"}, [{"title": "اختفاء بعثة فرانكلين"}]))
