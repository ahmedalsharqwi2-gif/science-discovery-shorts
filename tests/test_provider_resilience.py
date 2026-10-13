import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("resilient_preflight", Path(__file__).resolve().parents[1] / "scripts/model_preflight.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class ProviderResilienceTests(unittest.TestCase):
    def discover(self, replies):
        policy = {"providers": {"gemini": {"preferred_models": ["working-model"]}}}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "GEMINI_MODEL": "working-model"}, clear=True), patch.object(preflight, "request_json", side_effect=replies) as call:
            result = preflight.discover_gemini(policy)
        return result, call

    def test_no_generation_probe_consumes_quota(self):
        result, call = self.discover([(200, {"models": [{"name": "models/working-model", "supportedGenerationMethods": ["generateContent"]}]}), (200, {"supportedGenerationMethods": ["generateContent"]})])
        self.assertEqual(result, ("working-model", []))
        self.assertEqual(call.call_count, 2)
        self.assertFalse(any(":generateContent" in str(c) for c in call.call_args_list))

    def test_transient_detail_failure_keeps_live_catalog_candidate(self):
        for status in (429, 500, 503):
            with self.subTest(status=status):
                result, _ = self.discover([(200, {"models": [{"name": "models/working-model", "supportedGenerationMethods": ["generateContent"]}]}), (status, {})])
                self.assertEqual(result, ("working-model", []))

    def test_invalid_or_forbidden_model_remains_excluded(self):
        for status in (401, 403, 404):
            result, _ = self.discover([(200, {"models": [{"name": "models/working-model", "supportedGenerationMethods": ["generateContent"]}]}), (status, {})])
            self.assertEqual(result, ("", []))

    def test_failed_catalog_never_invents_a_candidate(self):
        result, call = self.discover([(503, {})])
        self.assertEqual(result, ("", []))
        self.assertEqual(call.call_count, 1)

    def test_account_denial_stops_redundant_probes(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(preflight, "request_json", side_effect=[(403, {}), (403, {"error": {"code": "organization_restricted"}})]) as call:
            result = preflight.discover_openai_provider("Fallback LLM", "https://example.test/chat/completions", "test", ["one", "two"], (), "")
        self.assertEqual(result, ("", []))
        self.assertEqual(call.call_count, 2)

    def test_model_specific_denial_can_try_another_model(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(preflight, "request_json", side_effect=[(403, {}), (403, {"error": {"code": "model_permission_denied"}}), (200, {})]):
            result = preflight.discover_openai_provider("Fallback LLM", "https://example.test/chat/completions", "test", ["one", "two"], (), "")
        self.assertEqual(result, ("two", []))
