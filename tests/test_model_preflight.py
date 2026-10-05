import json
import os
import unittest
from unittest.mock import patch
from pathlib import Path


class ModelPolicyTests(unittest.TestCase):
    def test_model_detail_cannot_override_failed_generation_probe(self):
        from scripts import model_preflight as preflight
        policy = {"providers": {"gemini": {"preferred_models": ["old"]}}}
        catalog = {"models": [{"name": "models/old", "supportedGenerationMethods": ["generateContent"]}]}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}, clear=True), \
             patch.object(preflight, "request_json", side_effect=[
                 (200, catalog), (200, {"supportedGenerationMethods": ["generateContent"]}),
                 (404, {})]) as request:
            self.assertEqual(preflight.discover_gemini(policy), ("", []))
        self.assertIn(":generateContent", request.call_args.args[0])

    def test_policy_has_one_shared_schema_and_provider_order(self):
        policy = json.loads(Path("config/model_policy.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["schema_version"], 1)
        self.assertEqual(list(policy["providers"]), ["gemini", "fallback", "openrouter"])
        for provider in policy["providers"].values():
            self.assertTrue(provider["preferred_models"])
            self.assertIn(503, provider["retry_statuses"])


    def test_select_never_returns_unlisted_or_stale_default(self):
        from scripts.model_preflight import select
        self.assertEqual(select(["old-model"], [], [], "old-model"), ("", []))
        self.assertEqual(select(["old-model"], [], ["new-model"], "old-model"), ("new-model", []))

    def test_preflight_is_importable_without_third_party_dependencies(self):
        import scripts.model_preflight as preflight
        self.assertEqual(preflight.DEFAULT_GEMINI, "gemini-2.5-flash")


if __name__ == "__main__":
    unittest.main()
