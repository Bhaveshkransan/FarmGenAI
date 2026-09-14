"""
llm/llm_client.py — Unified LLM interface for AgriNegotiator.

Supports:
  1. Ollama (Local) — Primary (Qwen 3 8B / Llama 3.1 8B via http://localhost:11434)
  2. Gemini (Cloud Fallback) — Backup via GEMINI_API_KEY
  3. Deterministic Fallback — Safe math logic when LLMs are offline

LangChain Integration:
  Use get_langchain_llm() inside LangGraph nodes to get a fully bound
  ChatOllama or ChatGoogleGenerativeAI compatible with .invoke()/.stream().
"""

import json
import os
import re
import time
import requests
import logging
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

logger = logging.getLogger("LLMClient")

OLLAMA_URL: str = os.getenv("OLLAMA_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama").lower()
ENABLE_LLM: bool = os.getenv("ENABLE_LLM", "true").lower() in {"1", "true", "yes"}


class LLMClient:
    """Unified LLM client supporting Cloud Gemini (Zero-setup) and Ollama (Local)."""

    def __init__(self):
        self.enabled = ENABLE_LLM
        self.provider = LLM_PROVIDER
        self.ollama_url = OLLAMA_URL
        self.ollama_model = OLLAMA_MODEL
        self.gemini_key = GEMINI_API_KEY

    def _generate_gemini(self, prompt: str) -> str | None:
        if not self.gemini_key:
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            g_model = genai.GenerativeModel("gemini-2.0-flash")
            res = g_model.generate_content(prompt)
            if res and res.text:
                return res.text.strip()
        except Exception as e:
            try:
                # Fallback to gemini-1.5-flash if 2.0 isn't available
                g_model = genai.GenerativeModel("gemini-1.5-flash")
                res = g_model.generate_content(prompt)
                if res and res.text:
                    return res.text.strip()
            except Exception:
                logger.warning(f"Gemini generation failed: {e}")
        return None

    def _generate_ollama(self, prompt: str, model: str = None, temperature: float = 0.7, max_tokens: int = 120) -> str | None:
        try:
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": model or self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": min(max_tokens, 120),
                }
            }
            # 12s timeout allows fast generation while avoiding hangs on CPU
            response = requests.post(url, json=payload, timeout=12)
            if response.status_code == 200:
                text = response.json().get("response", "")
                if text and len(text.strip()) > 0:
                    return text.strip()
        except Exception:
            pass
        return None

    def generate(self, prompt: str, model: str = None, temperature: float = 0.7, max_tokens: int = 120) -> str | None:
        """
        Generate text completion with local Ollama routing.
        """
        if not self.enabled:
            return None

        # Prioritize local Ollama (qwen2.5:1.5b)
        res = self._generate_ollama(prompt, model, temperature, max_tokens)
        if res:
            return res

        return None

    # Backward compatibility aliases
    def generate_response(self, prompt: str, **kwargs) -> str | None:
        return self.generate(prompt, **kwargs)

    def get_completion(self, prompt: str, **kwargs) -> str | None:
        return self.generate(prompt, **kwargs)

    # ------------------------------------------------------------------ #
    #  Structured negotiation reasoning                                   #
    # ------------------------------------------------------------------ #

    def negotiation_reasoning(
        self, role: str, offered_price: float, target_price: float,
        market_price: float, quantity: float
    ) -> dict:
        """
        Ask the LLM for ACCEPT / COUNTER / REJECT decision.
        Returns dict with keys: decision, counter_price, reason.
        Falls back to deterministic logic when LLM is unavailable.
        """
        prompt = f"""
You are an AI agent in an agricultural market negotiation.
Role: {role}
Current offer price: ₹{offered_price}/kg
Target price: ₹{target_price}/kg
Market price: ₹{market_price}/kg
Quantity: {quantity} kg

Decide what to do next.
Possible decisions: ACCEPT, COUNTER, REJECT

Respond STRICTLY in JSON:
{{"decision": "ACCEPT|COUNTER|REJECT", "counter_price": <number|null>, "reason": "Strategic reasoning for this move."}}
"""
        raw = self.generate(prompt, temperature=0.3, max_tokens=150)

        if raw:
            try:
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                if m:
                    return json.loads(m.group())
            except Exception:
                pass

        # Deterministic fallback
        if role == "Buyer":
            if offered_price <= target_price:
                return {"decision": "ACCEPT", "counter_price": None, "reason": "Price meets target."}
            gap = offered_price - target_price
            counter = round(offered_price - gap * 0.4, 2)
        else:  # Farmer
            if offered_price >= target_price:
                return {"decision": "ACCEPT", "counter_price": None, "reason": "Price meets target."}
            gap = target_price - offered_price
            counter = round(offered_price + gap * 0.4, 2)

        return {"decision": "COUNTER", "counter_price": counter, "reason": "Fallback mathematical counter."}

    # ------------------------------------------------------------------ #
    #  Analysis helpers                                                   #
    # ------------------------------------------------------------------ #

    def analyze_strategy(self, negotiation_history) -> str | None:
        prompt = f"Analyze this agricultural negotiation:\n{negotiation_history}\n1. Is deal fair? 2. Bargaining power? 3. Best next move?"
        return self.generate(prompt, temperature=0.4, max_tokens=200)

    def market_analysis(self, demand_level, supply_level, market_price) -> str | None:
        prompt = f"Agricultural market: demand={demand_level}, supply={supply_level}, price=₹{market_price}/kg. Provide brief analysis."
        return self.generate(prompt, temperature=0.5, max_tokens=150)

    def safe_request(self, prompt: str, retries: int = 2) -> str | None:
        for _ in range(retries):
            result = self.generate(prompt)
            if result:
                return result
            time.sleep(0.5)
        return None

    def explain_scenarios(self, scenarios_data: list, best_scenario_type: str) -> str:
        """Explain why the selected scenario is optimal."""
        try:
            summary_data = [
                {
                    "type": s["scenario_type"],
                    "price": s["final_price"],
                    "score": s["score"],
                    "status": s["status"]
                }
                for s in scenarios_data
            ]
            prompt = f"Analyze these agricultural scenarios and explain why '{best_scenario_type}' is the better choice for the farmer:\n{json.dumps(summary_data, indent=2)}\nProvide a 2-sentence summary."
            explanation = self.generate(prompt, temperature=0.5, max_tokens=150)
            if explanation and len(explanation.strip()) > 10:
                return explanation.strip()
        except Exception:
            pass

        # Deterministic narrative fallback
        if best_scenario_type == "direct-sale":
            return "Direct sale provides maximum net revenue by eliminating storage fees and maintaining peak produce freshness."
        elif best_scenario_type == "storage":
            return "Cold storage is optimal as it protects against current low market prices while waiting for high-demand windows."
        elif best_scenario_type == "processing":
            return "Value-added processing is the best risk-reduction strategy, guaranteeing zero waste despite lower market prices."
        return "This scenario maximizes overall value by balancing price satisfaction and logistics efficiency."

    def get_langchain_llm(self, temperature: float = 0.4):
        """
        Returns a LangChain-compatible chat model for use in LangGraph nodes.
        Priority: Gemini (Cloud, if provider is gemini) or ChatOllama (Local) → Fallback
        """
        # Strict Ollama mode
        if self.provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=self.ollama_model,
                    base_url=self.ollama_url,
                    temperature=temperature,
                )
            except Exception:
                pass
            return None

        # If Gemini is configured as provider
        if self.provider == "gemini" and self.gemini_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=self.gemini_key,
                    temperature=temperature,
                )
            except Exception:
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    return ChatGoogleGenerativeAI(
                        model="gemini-1.5-flash",
                        google_api_key=self.gemini_key,
                        temperature=temperature,
                    )
                except Exception:
                    pass

        # 1. Try Ollama (Local Primary)
        try:
            from langchain_ollama import ChatOllama
            llm = ChatOllama(
                model=self.ollama_model,
                base_url=self.ollama_url,
                temperature=temperature,
            )
            return llm
        except Exception:
            pass

        return None


# Singleton instance
client: LLMClient = LLMClient()


def get_langchain_llm(temperature: float = 0.4):
    """Module-level shortcut for LangGraph nodes."""
    return client.get_langchain_llm(temperature=temperature)

