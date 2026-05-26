"""
Integration tests: ClaudeHookService with LLMRouter backend.
Verifies the service preserves its interface while routing through the tiered model system.
Run with: pytest app/tests/test_hook_service_integration.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.claude_hook_service import ClaudeHookService, GeneratedHook


@pytest.fixture
def service_with_keys(monkeypatch):
    """Service instance with API keys set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    return ClaudeHookService()


class TestHookServiceInterface:
    """Verify the public interface is preserved for backward compatibility."""

    def test_service_has_generate_hooks(self, service_with_keys):
        assert hasattr(service_with_keys, "generate_hooks")
        assert callable(service_with_keys.generate_hooks)

    def test_service_has_generate_caption_from_hook(self, service_with_keys):
        assert hasattr(service_with_keys, "generate_caption_from_hook")
        assert callable(service_with_keys.generate_caption_from_hook)

    def test_service_exposes_last_model_used(self, service_with_keys):
        assert hasattr(service_with_keys, "last_model_used")
        assert service_with_keys.last_model_used == ""

    def test_service_exposes_last_cost_usd(self, service_with_keys):
        assert hasattr(service_with_keys, "last_cost_usd")
        assert service_with_keys.last_cost_usd == 0.0

    def test_generated_hook_dataclass(self):
        hook = GeneratedHook(
            hook_text="Test hook",
            archetype="question",
            confidence=0.85,
            rationale="Creates curiosity",
            estimated_retention=0.72,
            variant_index=0
        )
        assert hook.hook_text == "Test hook"
        assert hook.archetype == "question"
        assert hook.confidence == 0.85


class TestHookServiceFallback:
    """Verify fallback generation works when no API keys are set."""

    def test_fallback_generation_no_keys(self):
        svc = ClaudeHookService()  # No keys in clean env
        hooks = svc._fallback_generation("This is a test transcript.", num_variants=3)
        assert len(hooks) == 3
        assert all(isinstance(h, GeneratedHook) for h in hooks)
        assert all(h.hook_text for h in hooks)

    def test_fallback_generation_empty_transcript(self):
        svc = ClaudeHookService()
        hooks = svc._fallback_generation("", num_variants=2)
        assert len(hooks) == 2

    def test_fallback_generation_limits_to_num_variants(self):
        svc = ClaudeHookService()
        hooks = svc._fallback_generation("Test.", num_variants=1)
        assert len(hooks) == 1

    def test_fallback_caption(self):
        svc = ClaudeHookService()
        hook = GeneratedHook("Test hook", "question", 0.8, "rationale", 0.7, 0)
        caption, hashtags = svc._fallback_caption(hook, "Transcript text", "tiktok", 100)
        assert isinstance(caption, str)
        assert len(caption) > 0
        assert isinstance(hashtags, list)


class TestHookServiceJsonExtraction:
    """Verify JSON parsing from LLM responses."""

    def test_extract_json_markdown_code_block(self, service_with_keys):
        text = '```json\n{"hooks": [{"hook_text": "test"}]}\n```'
        result = service_with_keys._extract_json(text)
        assert result["hooks"][0]["hook_text"] == "test"

    def test_extract_json_plain_code_block(self, service_with_keys):
        text = '```\n{"hooks": [{"hook_text": "test2"}]}\n```'
        result = service_with_keys._extract_json(text)
        assert result["hooks"][0]["hook_text"] == "test2"

    def test_extract_json_raw(self, service_with_keys):
        text = '{"hooks": [{"hook_text": "test3"}]}'
        result = service_with_keys._extract_json(text)
        assert result["hooks"][0]["hook_text"] == "test3"
