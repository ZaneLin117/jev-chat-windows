"""Bocha 判断来源的离线接口契约检查。运行：python -m unittest tools.test_bocha_provider"""

import io
import json
import os
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from core import jev_client
from core.providers import BOCHA_JEV_BASE


class BochaProviderTests(unittest.TestCase):
    def test_judgment_preserves_typed_answers(self):
        seen = {}
        body = {
            "model": "bocha-jev-v1",
            "answers": {
                "literal_question": {"type": "noul", "noul": 0.8},
                "best_reply": {"type": "choice", "choice": "reply_b",
                               "probabilities": {"reply_a": 0.2, "reply_b": 0.8},
                               "confidence": 0.8},
            },
            "usage": {"input_tokens": 123, "output_tokens": 0},
        }

        def fake_urlopen(req, timeout):
            seen["url"] = req.full_url
            seen["method"] = req.get_method()
            seen["payload"] = json.loads(req.data)
            seen["auth"] = req.headers["Authorization"]
            return io.BytesIO(json.dumps(body).encode())

        questions = {"literal_question": {"type": "noul", "instructions": "Literal?"},
                     "best_reply": {"type": "choice", "instructions": "Best?",
                                    "criteria": {"reply_a": "A", "reply_b": "B"}}}
        with patch.dict(os.environ, {"JEV_API_KEY": "test-secret"}), \
             patch.object(urllib.request, "urlopen", fake_urlopen):
            result = jev_client.ask({"chat": ["你好"]}, questions, provider="bocha")
        self.assertEqual(seen["url"], BOCHA_JEV_BASE + "/v1/systemone")
        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["auth"], "Bearer test-secret")
        self.assertEqual(seen["payload"], {"model": "bocha-jev-v1",
                                           "state": {"chat": ["你好"]}, "questions": questions})
        self.assertEqual(result, body)

    def test_models_use_authorized_endpoint(self):
        def fake_urlopen(req, timeout):
            self.assertEqual(req.full_url, BOCHA_JEV_BASE + "/v1/models")
            self.assertEqual(req.get_method(), "GET")
            self.assertEqual(req.headers["Authorization"], "Bearer test-secret")
            return io.BytesIO(b'{"data":[{"id":"bocha-jev-v1"}]}')

        with patch.object(urllib.request, "urlopen", fake_urlopen):
            self.assertEqual(jev_client.list_models("bocha", "test-secret"), ["bocha-jev-v1"])

    def test_bad_key_is_not_retried_or_echoed(self):
        calls = []

        def fake_urlopen(req, timeout):
            calls.append(req.full_url)
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {},
                                         io.BytesIO(b'{"error":"test-secret"}'))

        with patch.dict(os.environ, {"JEV_API_KEY": "test-secret"}), \
             patch.object(urllib.request, "urlopen", fake_urlopen):
            with self.assertRaises(jev_client.JevError) as caught:
                jev_client.ask({}, {"q": {"type": "noul", "instructions": "?"}},
                               provider="bocha")
        self.assertEqual(len(calls), 1)
        self.assertEqual(caught.exception.status, 401)
        self.assertNotIn("test-secret", str(caught.exception))

    def test_unsaved_key_is_redacted_from_model_error(self):
        def fake_urlopen(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {},
                                         io.BytesIO(b'{"error":"test-secret"}'))

        with patch.object(urllib.request, "urlopen", fake_urlopen):
            with self.assertRaises(jev_client.JevError) as caught:
                jev_client.list_models("bocha", "test-secret")
        self.assertNotIn("test-secret", str(caught.exception))
        self.assertIn("[REDACTED]", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
