from __future__ import annotations

import unittest

from bom_ai_engine.langchain_client import DEFAULT_PROVIDER, parse_model_spec


class LangChainClientTests(unittest.TestCase):
    def test_parse_gemini_model_without_prefix(self) -> None:
        config = parse_model_spec("gemini-2.5-flash")
        self.assertEqual(config.provider, DEFAULT_PROVIDER)
        self.assertEqual(config.model, "gemini-2.5-flash")

    def test_parse_gemini_model_with_prefix(self) -> None:
        config = parse_model_spec("google_genai:gemini-2.5-flash")
        self.assertEqual(config.provider, DEFAULT_PROVIDER)
        self.assertEqual(config.model, "gemini-2.5-flash")

    def test_reject_non_gemini_provider(self) -> None:
        with self.assertRaises(ValueError):
            parse_model_spec("openai:gpt-5")


if __name__ == "__main__":
    unittest.main()
