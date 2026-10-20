"""
backend/schemas/buyer_market_context.py
------------------------------------------------------------------------
Structured Data Models for Buyer Market Context Integration.

Strictly isolates and coordinates the three distinct market context domains:
1. Current Market Data (Observed APMC Mandi Prices)
2. ML Forecast (Next-Period Modal Price Prediction P_modal, t+1)
3. Buyer RAG Knowledge (Qualitative & Contextual Domain Text)

Enforces strict source separation, unit consistency (normalized ₹/kg),
location hierarchy matching, freshness tracking, and economic invariance.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    normalize_crop_name,
    is_supported_buyer_crop,
)


@dataclass
class CurrentMarketContext:
    """Observed real-time or latest available APMC Mandi market price observation."""
    commodity: str = ""
    modal_price: Optional[float] = None          # Normalized ₹/kg
    min_price: Optional[float] = None            # Normalized ₹/kg
    max_price: Optional[float] = None            # Normalized ₹/kg
    source_price: Optional[float] = None         # Original source price (e.g. ₹/quintal)
    source_price_unit: str = "₹/quintal"
    normalized_price_unit: str = "₹/kg"
    observation_date: str = ""
    market: str = ""
    district: str = ""
    state: str = "Maharashtra"
    source: str = "data.gov.in (Agmarknet)"
    freshness: str = "UNAVAILABLE"               # CURRENT, STALE, UNAVAILABLE
    match_level: str = "NONE"                    # EXACT_APMC, TOKEN_APMC, DISTRICT, TOKEN_DISTRICT, STATE, NONE
    variety: str = "General"
    grade: str = "FAQ"
    is_current: bool = False
    is_available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MLForecastContext:
    """Predicted next-period wholesale modal market price forecast."""
    commodity: str = ""
    predicted_modal_price: Optional[float] = None  # Normalized ₹/kg (P_modal, t+1)
    forecast_period: str = "next_period (t+1)"
    model: str = "RidgeRegression (scikit-learn)"
    feature_source: Dict[str, Any] = field(default_factory=dict)
    features_used: List[str] = field(default_factory=list)
    normalized_price_unit: str = "₹/kg"
    audit_status: str = "NOT_RUN"                 # ML_USED, FALLBACK_USED, NOT_RUN
    is_ml_prediction: bool = False
    is_available: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BuyerRAGContextSummary:
    """Qualitative textual and domain knowledge context retrieved via Buyer RAG."""
    relevant_knowledge: List[str] = field(default_factory=list)
    quality_context: str = ""
    procurement_context: str = ""
    government_rules_context: str = ""
    negotiation_memory_context: str = ""
    sources: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_domains: List[str] = field(default_factory=list)
    is_empty: bool = True
    is_available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BuyerMarketContext:
    """
    Unified composite container for Buyer Agent market context.
    Coordinates Current Market (Observed), ML Forecast (Prediction), and Buyer RAG (Knowledge)
    without permitting any one source to override deterministic economic rules.
    """
    crop: str
    location: Optional[str] = None
    buyer_persona: Optional[str] = "custom"
    current_market: CurrentMarketContext = field(default_factory=CurrentMarketContext)
    ml_forecast: MLForecastContext = field(default_factory=MLForecastContext)
    buyer_rag: BuyerRAGContextSummary = field(default_factory=BuyerRAGContextSummary)
    unit: str = "₹/kg"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def has_current_market(self) -> bool:
        return self.current_market.is_available and self.current_market.modal_price is not None

    @property
    def has_ml_forecast(self) -> bool:
        return self.ml_forecast.is_available and self.ml_forecast.predicted_modal_price is not None

    @property
    def has_buyer_rag(self) -> bool:
        return self.buyer_rag.is_available and not self.buyer_rag.is_empty

    @property
    def is_complete(self) -> bool:
        """True if all three distinct context domains are successfully populated."""
        return self.has_current_market and self.has_ml_forecast and self.has_buyer_rag

    @property
    def is_partial(self) -> bool:
        """True if at least one but not all domains are available."""
        count = sum([self.has_current_market, self.has_ml_forecast, self.has_buyer_rag])
        return 0 < count < 3

    @property
    def is_empty(self) -> bool:
        """True if no context sources are available."""
        return not (self.has_current_market or self.has_ml_forecast or self.has_buyer_rag)

    def validate_units(self) -> Tuple[bool, str]:
        """
        Validates that all numerical price quantities in the context are strictly normalized in ₹/kg.
        Protects against unnormalized ₹/quintal mismatches.
        """
        # Crop specific plausible ₹/kg bounds
        plausible_ranges = {
            "Sugarcane": (1.0, 15.0),
            "Soybean": (20.0, 150.0),
            "Cotton": (30.0, 200.0),
            "Jowar": (10.0, 100.0),
            "Onion": (3.0, 120.0),
            "Bajra": (10.0, 100.0),
            "Rice": (10.0, 120.0),
        }
        canonical = normalize_crop_name(self.crop)
        bounds = plausible_ranges.get(canonical, (1.0, 500.0))

        if self.has_current_market:
            p = self.current_market.modal_price
            if p is not None and (p < bounds[0] or p > bounds[1]):
                if p > bounds[1] * 10:
                    return False, f"Potential unit mismatch in current_market: modal_price ₹{p}/kg looks like ₹/quintal!"
            if self.current_market.normalized_price_unit != "₹/kg":
                return False, f"Invalid normalized_price_unit: {self.current_market.normalized_price_unit} (must be ₹/kg)"

        if self.has_ml_forecast:
            p = self.ml_forecast.predicted_modal_price
            if p is not None and (p < bounds[0] or p > bounds[1]):
                if p > bounds[1] * 10:
                    return False, f"Potential unit mismatch in ml_forecast: predicted_modal_price ₹{p}/kg looks like ₹/quintal!"
            if self.ml_forecast.normalized_price_unit != "₹/kg":
                return False, f"Invalid normalized_price_unit in ml_forecast: {self.ml_forecast.normalized_price_unit}"

        return True, "All units verified as normalized ₹/kg."

    def to_prompt_text(self) -> str:
        """
        Renders a cleanly segregated, structured markdown block for LLM prompts.
        Strictly prevents semantic conflation between observed prices, ML forecasts, and text knowledge.
        """
        sections = []

        # 1. Observed Current Mandi Price
        if self.has_current_market:
            cm = self.current_market
            fresh_label = f"[{cm.freshness}]" if cm.freshness else ""
            match_label = f"(Location Match: {cm.match_level})" if cm.match_level else ""
            sections.append(
                f"- 📍 Current Daily Mandi Price (Observed): ₹{cm.modal_price}/kg at {cm.market} {match_label}\n"
                f"  • Date: {cm.observation_date} {fresh_label} | Min: ₹{cm.min_price}/kg | Max: ₹{cm.max_price}/kg | Source: {cm.source}"
            )
        else:
            sections.append("- 📍 Current Daily Mandi Price (Observed): UNAVAILABLE (No recent APMC mandi observation)")

        # 2. Predicted ML Forecast
        if self.has_ml_forecast:
            mf = self.ml_forecast
            model_info = f"({mf.model})" if mf.model else ""
            src_desc = mf.feature_source.get("match_level", "APMC historical dataset") if mf.feature_source else "APMC record"
            sections.append(
                f"- 🔮 Predicted Next-Period Modal Price (ML Forecast): ₹{mf.predicted_modal_price}/kg {model_info}\n"
                f"  • Period: {mf.forecast_period} | Feature Source: {src_desc} | Audit Status: {mf.audit_status}"
            )
        else:
            sections.append("- 🔮 Predicted Next-Period Modal Price (ML Forecast): UNAVAILABLE (Controlled heuristic fallback)")

        # 3. Buyer RAG Knowledge
        if self.has_buyer_rag:
            rag_parts = []
            if self.buyer_rag.quality_context:
                rag_parts.append(f"  • Quality Specs: {self.buyer_rag.quality_context}")
            if self.buyer_rag.procurement_context:
                rag_parts.append(f"  • Procurement Guidelines: {self.buyer_rag.procurement_context}")
            if self.buyer_rag.government_rules_context:
                rag_parts.append(f"  • Government / APMC Rules: {self.buyer_rag.government_rules_context}")
            if self.buyer_rag.negotiation_memory_context:
                rag_parts.append(f"  • Strategic Reflections: {self.buyer_rag.negotiation_memory_context}")
            if self.buyer_rag.relevant_knowledge:
                rag_parts.append("  • Domain Knowledge: " + " | ".join(self.buyer_rag.relevant_knowledge[:2]))

            rag_summary = "\n".join(rag_parts) if rag_parts else "  • Active Buyer Knowledge Domain Loaded"
            sections.append(f"- 📚 Relevant Buyer RAG Knowledge:\n{rag_summary}")
        else:
            sections.append("- 📚 Relevant Buyer RAG Knowledge: UNAVAILABLE")

        return "\n".join(sections)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crop": self.crop,
            "location": self.location,
            "buyer_persona": self.buyer_persona,
            "current_market": self.current_market.to_dict(),
            "ml_forecast": self.ml_forecast.to_dict(),
            "buyer_rag": self.buyer_rag.to_dict(),
            "unit": self.unit,
            "is_complete": self.is_complete,
            "is_partial": self.is_partial,
            "is_empty": self.is_empty,
            "created_at": self.created_at,
        }
