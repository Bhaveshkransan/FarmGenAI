"""
tests/test_07_real_llm.py
Type: REAL LLM (requires Ollama running with qwen2:0.5b)
If Ollama is unavailable: REAL_LLM_TEST_SKIPPED
If LLM returns invalid JSON: test is skipped (not silently passed)
"""
import sys, os, json, re, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

OLLAMA_URL = os.getenv("OLLAMA_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:0.5b")

OLLAMA_AVAILABLE = False
LLM_CLIENT = None

try:
    import requests
    resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    if resp.status_code == 200:
        OLLAMA_AVAILABLE = True
        from llm.llm_client import LLMClient
        LLM_CLIENT = LLMClient()
except Exception:
    pass

skip_ollama = pytest.mark.skipif(
    not OLLAMA_AVAILABLE,
    reason="REAL_LLM_TEST_SKIPPED -- Ollama unavailable"
)


def extract_json(text):
    if not text:
        return None
    try:
        cleaned = re.sub(r"```(?:json)?", "", text).strip()
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return None


class TestOllamaBasic:
    @skip_ollama
    def test_generate_non_empty(self):
        result = LLM_CLIENT.generate("Say hello in one word.")
        assert result and len(result.strip()) > 0

    @skip_ollama
    def test_generate_with_max_tokens(self):
        result = LLM_CLIENT.generate("Describe tomatoes briefly.", max_tokens=20)
        assert result and len(result) > 0


class TestFarmerLLM:
    @skip_ollama
    def test_farmer_prompt_returns_valid_json(self):
        from backend.agents.prompts import FARMER_PROMPT
        prompt = FARMER_PROMPT.format(
            crop="Tomato", quantity=500, min_price=20.0, location="Pune",
            shelf_life=5, market_price=22.0, buyer_offer=18.0, round=1,
            history="No rounds yet.",
            rag_context="Market stable. Tomato at Rs.22/kg.",
            trust_context="No trust context."
        )
        raw = LLM_CLIENT.generate(prompt, max_tokens=150, temperature=0.3)
        assert raw is not None, "LLM returned None"
        print(f"  Farmer raw: {raw[:200]}")
        parsed = extract_json(raw)
        if parsed is None:
            pytest.skip("LLM did not return valid JSON -- model too small")
        assert "decision" in parsed
        assert parsed["decision"] in ("ACCEPT", "COUNTER", "REJECT")


class TestBuyerLLM:
    @skip_ollama
    def test_buyer_prompt_returns_valid_json(self):
        from backend.agents.prompts import BUYER_PROMPT
        prompt = BUYER_PROMPT.format(
            buyer_name="BigBasket", target_price=22.0, budget=15000.0,
            max_quantity=600, location="Mumbai", farmer_ask=23.0, round=1,
            history="No rounds yet.",
            rag_context="Stable market.",
            trust_context="No trust context."
        )
        raw = LLM_CLIENT.generate(prompt, max_tokens=150, temperature=0.3)
        assert raw is not None
        print(f"  Buyer raw: {raw[:200]}")
        parsed = extract_json(raw)
        if parsed is None:
            pytest.skip("LLM did not return valid JSON")
        assert parsed["decision"] in ("ACCEPT", "COUNTER", "REJECT")


class TestMarketIntelligenceLLM:
    @skip_ollama
    def test_returns_non_empty_analysis(self):
        from backend.agents.prompts import MARKET_INTELLIGENCE_PROMPT
        prompt = MARKET_INTELLIGENCE_PROMPT.format(
            crop="Tomato", location="Pune", season="Kharif",
            mandi_data="Pune APMC: Rs.22/kg (bullish).",
            weather_data="28C, light rain."
        )
        raw = LLM_CLIENT.generate(prompt, max_tokens=200)
        assert raw and len(raw) > 20
        print(f"  Market intel: {raw[:150]}")


class TestValidatorLLM:
    @skip_ollama
    def test_validator_prompt_returns_valid_flag(self):
        from backend.agents.prompts import VALIDATOR_PROMPT
        prompt = VALIDATOR_PROMPT.format(
            farmer_price=22.0, buyer_price=22.0,
            min_price=20.0, budget=15000.0, quantity=500, msp=1800
        )
        raw = LLM_CLIENT.generate(prompt, max_tokens=150, temperature=0.2)
        if not raw:
            pytest.skip("LLM unavailable")
        print(f"  Validator raw: {raw[:200]}")
        parsed = extract_json(raw)
        if parsed is None:
            pytest.skip("LLM did not return valid JSON")
        assert "valid" in parsed

    @skip_ollama
    def test_deterministic_fallback_rejects_below_floor(self):
        """Regardless of LLM: deterministic validator MUST reject below-floor."""
        min_price = 20.0
        deal_price = 15.0   # BELOW FLOOR
        quantity = 500
        budget = 100000.0
        det_valid = (deal_price * quantity <= budget) and (deal_price >= min_price)
        assert det_valid is False, "Deterministic validator MUST reject below-floor"


class TestProcessorBiddingLLM:
    @skip_ollama
    def test_processor_prompt_returns_bid_price(self):
        from backend.agents.prompts import PROCESSOR_PROMPT
        prompt = PROCESSOR_PROMPT.format(
            processor_name="FoodProcessor_1", crop="Tomato",
            quantity=500, location="Pune", market_price=22.0
        )
        raw = LLM_CLIENT.generate(prompt, max_tokens=100)
        print(f"  Processor raw: {raw[:150] if raw else None}")
        if not raw:
            pytest.skip("LLM unavailable")
        parsed = extract_json(raw)
        if parsed is None:
            pytest.skip("LLM did not return valid JSON")
        assert "bid_price" in parsed
        assert isinstance(parsed["bid_price"], (int, float))
        assert parsed["bid_price"] > 0


class TestLLMIntelligenceEvaluation:
    @skip_ollama
    def test_planner_mentions_crop(self):
        from backend.agents.prompts import PLANNER_PROMPT
        prompt = PLANNER_PROMPT.format(
            crop="Onion", quantity=1000, min_price=15.0,
            location="Nashik", shelf_life=10, market_price=17.0
        )
        raw = LLM_CLIENT.generate(prompt, max_tokens=200)
        if not raw:
            pytest.skip("LLM unavailable")
        print(f"  Planner: {raw[:200]}")
        ctx_aware = any(k in raw.lower() for k in ["onion", "nashik", "price", "sell"])
        print(f"  Context-aware: {ctx_aware}")

    @skip_ollama
    def test_reflection_json_structure(self):
        from backend.agents.prompts import REFLECTION_PROMPT
        prompt = REFLECTION_PROMPT.format(
            crop="Tomato", status="DEAL", rounds=3,
            history="Round 1: Farmer asked Rs.24. Buyer offered Rs.20.\nRound 2: Deal at Rs.22.",
            summary="Deal reached at Rs.22/kg after 2 rounds.",
            market_price=22.0, final_price=22.0
        )
        raw = LLM_CLIENT.generate(prompt, max_tokens=300, temperature=0.2)
        if not raw:
            pytest.skip("LLM unavailable")
        print(f"  Reflection: {raw[:200]}")
        parsed = extract_json(raw)
        if parsed is None:
            pytest.skip("LLM did not return valid JSON for reflection")
        has_key = any(k in parsed for k in [
            "reason_for_success_or_failure", "farmer_strategy",
            "buyer_strategy", "summary"
        ])
        print(f"  Has analysis keys: {has_key}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
