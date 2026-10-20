"""
backend/services/buyer_market_context_service.py
------------------------------------------------------------------------
Service for constructing and orchestrating unified BuyerMarketContext objects.

Coordinates:
1. Current Mandi Service (Priority 4) -> CurrentMarketContext
2. Buyer Pricing / ML Prediction Service (Priority 2) -> MLForecastContext
3. Buyer RAG Retrieval Service (Priority 3) -> BuyerRAGContextSummary

Gracefully handles any combination of available or unavailable sub-services:
- Current market only
- ML forecast only
- RAG only
- Partial combinations
- All unavailable (pure deterministic fallback)
"""

import logging
from typing import Optional, Dict, Any

from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    normalize_crop_name,
    is_supported_buyer_crop,
    validate_buyer_crop,
)
from backend.schemas.buyer_market_context import (
    BuyerMarketContext,
    CurrentMarketContext,
    MLForecastContext,
    BuyerRAGContextSummary,
)

logger = logging.getLogger("BuyerMarketContextService")


class BuyerMarketContextService:
    """
    Orchestration service for resolving and assembling complete BuyerMarketContext.
    """

    def __init__(
        self,
        current_mandi_service=None,
        pricing_service=None,
        buyer_rag_service=None,
    ):
        self._current_mandi_service = current_mandi_service
        self._pricing_service = pricing_service
        self._buyer_rag_service = buyer_rag_service

    def _get_mandi_service(self):
        if self._current_mandi_service is None:
            try:
                from backend.services.current_mandi_service import current_mandi_service
                self._current_mandi_service = current_mandi_service
            except Exception as e:
                logger.debug(f"CurrentMandiService unavailable: {e}")
                self._current_mandi_service = None
        return self._current_mandi_service

    def _get_pricing_service(self):
        if self._pricing_service is None:
            try:
                from backend.services.buyer_pricing_service import get_buyer_pricing_service
                self._pricing_service = get_buyer_pricing_service()
            except Exception as e:
                logger.debug(f"BuyerPricePredictionService unavailable: {e}")
                self._pricing_service = None
        return self._pricing_service

    def _get_rag_service(self):
        if self._buyer_rag_service is None:
            try:
                from backend.services.buyer_rag_service import buyer_rag_service
                self._buyer_rag_service = buyer_rag_service
            except Exception as e:
                logger.debug(f"BuyerRAGService unavailable: {e}")
                self._buyer_rag_service = None
        return self._buyer_rag_service

    def build_market_context(
        self,
        crop: str,
        location: Optional[str] = None,
        persona: Optional[str] = "custom",
        context: Optional[Dict[str, Any]] = None,
    ) -> BuyerMarketContext:
        """
        Assembles a comprehensive BuyerMarketContext across all three domains.
        Guarantees non-blocking execution: failures in any domain yield safe empty domain containers.
        """
        norm_crop = normalize_crop_name(crop) or crop
        loc = location or "Maharashtra"

        # 1. Resolve Current Mandi Data
        cm_ctx = CurrentMarketContext(commodity=norm_crop, state="Maharashtra")
        if context and "current_mandi_data" in context and isinstance(context["current_mandi_data"], dict):
            m_data = context["current_mandi_data"]
            if m_data.get("success", False) or m_data.get("modal_price_kg"):
                cm_ctx = CurrentMarketContext(
                    commodity=m_data.get("commodity", norm_crop),
                    modal_price=m_data.get("modal_price_kg"),
                    min_price=m_data.get("min_price_kg"),
                    max_price=m_data.get("max_price_kg"),
                    source_price=m_data.get("source_price"),
                    source_price_unit=m_data.get("source_price_unit", "₹/quintal"),
                    normalized_price_unit=m_data.get("normalized_price_unit", "₹/kg"),
                    observation_date=m_data.get("observation_date", ""),
                    market=m_data.get("apmc", m_data.get("market", "APMC Mandi")),
                    district=m_data.get("district", ""),
                    state=m_data.get("state", "Maharashtra"),
                    source=m_data.get("source", "data.gov.in (Agmarknet)"),
                    freshness=m_data.get("freshness", "CURRENT"),
                    match_level=m_data.get("match_level", "DISTRICT"),
                    variety=m_data.get("variety", "General"),
                    grade=m_data.get("grade", "FAQ"),
                    is_current=(m_data.get("freshness") == "CURRENT"),
                    is_available=(m_data.get("modal_price_kg") is not None and m_data.get("modal_price_kg") > 0),
                )
        else:
            mandi_svc = self._get_mandi_service()
            if mandi_svc and is_supported_buyer_crop(norm_crop):
                try:
                    m_data = mandi_svc.get_current_market_price(norm_crop, loc)
                    if m_data and m_data.get("success", False):
                        cm_ctx = CurrentMarketContext(
                            commodity=m_data.get("commodity", norm_crop),
                            modal_price=m_data.get("modal_price_kg"),
                            min_price=m_data.get("min_price_kg"),
                            max_price=m_data.get("max_price_kg"),
                            source_price=m_data.get("source_price"),
                            source_price_unit=m_data.get("source_price_unit", "₹/quintal"),
                            normalized_price_unit=m_data.get("normalized_price_unit", "₹/kg"),
                            observation_date=m_data.get("observation_date", ""),
                            market=m_data.get("apmc", "APMC Mandi"),
                            district=m_data.get("district", ""),
                            state=m_data.get("state", "Maharashtra"),
                            source=m_data.get("source", "data.gov.in (Agmarknet)"),
                            freshness=m_data.get("freshness", "CURRENT"),
                            match_level=m_data.get("match_level", "DISTRICT"),
                            variety=m_data.get("variety", "General"),
                            grade=m_data.get("grade", "FAQ"),
                            is_current=(m_data.get("freshness") == "CURRENT"),
                            is_available=(m_data.get("modal_price_kg") is not None and m_data.get("modal_price_kg") > 0),
                        )
                except Exception as e:
                    logger.debug(f"Current mandi lookup failed: {e}")

        # 2. Resolve ML Forecast
        ml_ctx = MLForecastContext(commodity=norm_crop)
        pricing_svc = self._get_pricing_service()
        if pricing_svc and is_supported_buyer_crop(norm_crop):
            try:
                features = None
                meta = None
                if context and isinstance(context.get("market_features"), dict):
                    features = context["market_features"]
                    meta = context.get("feature_source", {})
                else:
                    features, meta = pricing_svc.get_market_features(norm_crop, loc)

                if features:
                    pred_res = pricing_svc.predict_modal_price(
                        norm_crop, features, location=loc, feature_source=meta
                    )
                    if pred_res and pred_res.get("audit_status") == "ML_USED":
                        ml_ctx = MLForecastContext(
                            commodity=norm_crop,
                            predicted_modal_price=float(pred_res["predicted_modal_price"]),
                            forecast_period="next_period (t+1)",
                            model=pred_res.get("model", "RidgeRegression (scikit-learn)"),
                            feature_source=pred_res.get("feature_source", meta or {}),
                            features_used=pred_res.get("features_used", []),
                            normalized_price_unit="₹/kg",
                            audit_status="ML_USED",
                            is_ml_prediction=True,
                            is_available=True,
                        )
            except Exception as e:
                logger.debug(f"ML forecast lookup failed: {e}")

        # 3. Resolve Buyer RAG Knowledge
        rag_summary = BuyerRAGContextSummary()
        if context and "buyer_rag_context" in context:
            b_rag = context["buyer_rag_context"]
            if hasattr(b_rag, "to_prompt_text"):
                rag_summary = BuyerRAGContextSummary(
                    relevant_knowledge=[d.get("text", "") for d in getattr(b_rag, "relevant_shared_knowledge", []) if d.get("text")],
                    quality_context="; ".join([d.get("text", "") for d in getattr(b_rag, "crop_quality_knowledge", []) if d.get("text")]),
                    procurement_context="; ".join([d.get("text", "") for d in getattr(b_rag, "procurement_knowledge", []) if d.get("text")]),
                    government_rules_context="; ".join([d.get("text", "") for d in getattr(b_rag, "government_rules", []) if d.get("text")]),
                    negotiation_memory_context="; ".join([d.get("text", "") for d in getattr(b_rag, "negotiation_memory", []) if d.get("text")]),
                    sources=getattr(b_rag, "sources", []),
                    knowledge_domains=list(getattr(b_rag, "retrieval_metadata", {}).get("domains_searched", [])),
                    is_empty=b_rag.is_empty,
                    is_available=not b_rag.is_empty,
                )
        else:
            rag_svc = self._get_rag_service()
            if rag_svc and is_supported_buyer_crop(norm_crop):
                try:
                    b_rag = rag_svc.get_buyer_context(crop=norm_crop, location=loc, persona=persona)
                    if b_rag and not b_rag.is_empty:
                        rag_summary = BuyerRAGContextSummary(
                            relevant_knowledge=[d.get("text", "") for d in b_rag.relevant_shared_knowledge if d.get("text")],
                            quality_context="; ".join([d.get("text", "") for d in b_rag.crop_quality_knowledge if d.get("text")]),
                            procurement_context="; ".join([d.get("text", "") for d in b_rag.procurement_knowledge if d.get("text")]),
                            government_rules_context="; ".join([d.get("text", "") for d in b_rag.government_rules if d.get("text")]),
                            negotiation_memory_context="; ".join([d.get("text", "") for d in b_rag.negotiation_memory if d.get("text")]),
                            sources=b_rag.sources,
                            knowledge_domains=list(b_rag.retrieval_metadata.get("domains_searched", [])),
                            is_empty=b_rag.is_empty,
                            is_available=True,
                        )
                except Exception as e:
                    logger.debug(f"Buyer RAG lookup failed: {e}")

        # Construct composite context
        market_ctx = BuyerMarketContext(
            crop=norm_crop,
            location=loc,
            buyer_persona=persona,
            current_market=cm_ctx,
            ml_forecast=ml_ctx,
            buyer_rag=rag_summary,
            unit="₹/kg",
        )

        return market_ctx


# Singleton instance
buyer_market_context_service = BuyerMarketContextService()
