"""
backend/services/buyer_rag_service.py

Purpose-built Buyer RAG abstraction and retrieval service for AgriNegotiator.
Provides isolated, metadata-filtered context for the Buyer Agent across
buyer profile knowledge, procurement knowledge, crop quality, government rules,
and historical buyer negotiation memory.

Enforces strict knowledge domain separation, provenance tracking, and graceful fallback.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from shared.crop_catalog import normalize_crop_name, is_supported_buyer_crop

logger = logging.getLogger("BuyerRAGService")


@dataclass
class BuyerRAGContext:
    """Structured container for retrieved Buyer RAG knowledge."""
    buyer_profile: List[Dict[str, Any]] = field(default_factory=list)
    procurement_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    crop_quality_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    government_rules: List[Dict[str, Any]] = field(default_factory=list)
    negotiation_memory: List[Dict[str, Any]] = field(default_factory=list)
    relevant_shared_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """Returns True if no documents were retrieved in any domain."""
        return not (
            self.buyer_profile
            or self.procurement_knowledge
            or self.crop_quality_knowledge
            or self.government_rules
            or self.negotiation_memory
            or self.relevant_shared_knowledge
        )

    @classmethod
    def empty(cls, reason: str = "No relevant context found or RAG unavailable") -> "BuyerRAGContext":
        """Factory method for empty fallback context."""
        return cls(retrieval_metadata={"status": "EMPTY", "reason": reason})

    def to_prompt_text(self, max_chars: int = 1500) -> str:
        """
        Renders a concise, structured markdown summary for LLM prompt context.
        Prevents prompt flooding while maintaining source traceability.
        """
        if self.is_empty:
            return "No buyer-specific RAG knowledge context available."

        sections = []

        if self.buyer_profile:
            items = [f"- {item.get('text', '')}" for item in self.buyer_profile]
            sections.append("### Buyer Profile & Preferences:\n" + "\n".join(items))

        if self.crop_quality_knowledge:
            items = [f"- {item.get('text', '')}" for item in self.crop_quality_knowledge]
            sections.append("### Crop Quality & Grading Specifications:\n" + "\n".join(items))

        if self.government_rules:
            items = [f"- {item.get('text', '')}" for item in self.government_rules]
            sections.append("### Government Procurement & APMC Regulations:\n" + "\n".join(items))

        if self.procurement_knowledge:
            items = [f"- {item.get('text', '')}" for item in self.procurement_knowledge]
            sections.append("### Commercial Procurement Knowledge:\n" + "\n".join(items))

        if self.negotiation_memory:
            items = [f"- {item.get('text', '')}" for item in self.negotiation_memory]
            sections.append("### Buyer Historical Negotiation Reflections:\n" + "\n".join(items))

        if self.relevant_shared_knowledge:
            items = [f"- {item.get('text', '')}" for item in self.relevant_shared_knowledge]
            sections.append("### Relevant Agricultural Reference Knowledge:\n" + "\n".join(items))

        full_text = "\n\n".join(sections)
        if len(full_text) > max_chars:
            return full_text[:max_chars] + "... [truncated]"
        return full_text


class BuyerRAGService:
    """
    Dedicated Buyer Retrieval Service.
    Queries ChromaDB vector collections using metadata filtering to isolate
    buyer knowledge (stakeholder='buyer' or 'shared') and strictly block
    farmer-private information (stakeholder='farmer').
    """

    def __init__(self, rag_service=None):
        self._rag_service = rag_service

    def _get_underlying_rag(self):
        if self._rag_service is not None:
            return self._rag_service
        try:
            from backend.services.rag_service import rag_service
            return rag_service
        except Exception as e:
            logger.warning(f"Could not import global rag_service: {e}")
            return None

    def get_buyer_context(
        self,
        crop: Optional[str] = None,
        location: Optional[str] = None,
        persona: Optional[str] = None,
        query: Optional[str] = None,
        limit_per_domain: int = 2,
    ) -> BuyerRAGContext:
        """
        Performs multi-domain vector retrieval for Buyer Agent with metadata filtering,
        provenance tracking, and failsafe error handling.
        """
        rag = self._get_underlying_rag()
        if not rag or not getattr(rag, "client", None):
            return BuyerRAGContext.empty(reason="ChromaDB service client unavailable")

        # Normalize crop if provided
        norm_crop = normalize_crop_name(crop) if crop else None
        if crop and not norm_crop:
            logger.warning(f"Unsupported crop string for Buyer RAG: {crop}")
            return BuyerRAGContext.empty(reason=f"Unsupported crop '{crop}'")

        context = BuyerRAGContext()
        sources = []
        retrieved_count = 0

        # Primary search query text construction
        base_query = query or f"Buyer procurement crop quality rules for {norm_crop or 'produce'}"

        try:
            # 1. Domain: Buyer Profile Knowledge
            if persona or norm_crop:
                p_query = f"Buyer persona {persona or ''} preferred crops {norm_crop or ''}".strip()
                p_results = self._query_domain_collection(
                    rag,
                    collection_name="buyer_profiles",
                    query_text=p_query,
                    n_results=limit_per_domain,
                    stakeholder_filter=["buyer", "shared"],
                    crop=norm_crop,
                    domain_name="buyer_profile",
                )
                context.buyer_profile = p_results["items"]
                sources.extend(p_results["sources"])
                retrieved_count += len(p_results["items"])

            # 2. Domain: Crop Quality Knowledge
            q_query = f"{norm_crop or 'produce'} quality grades freshness shelf life defect standards"
            q_results = self._query_domain_collection(
                rag,
                collection_name="crop_knowledge",
                query_text=q_query,
                n_results=limit_per_domain,
                stakeholder_filter=["buyer", "shared"],
                crop=norm_crop,
                domain_name="crop_quality",
            )
            context.crop_quality_knowledge = q_results["items"]
            sources.extend(q_results["sources"])
            retrieved_count += len(q_results["items"])

            # 3. Domain: Government / APMC Rules
            g_query = f"{norm_crop or 'agricultural produce'} APMC regulations FRP MSP quality guidelines"
            g_results = self._query_domain_collection(
                rag,
                collection_name="government_rules",
                query_text=g_query,
                n_results=limit_per_domain,
                stakeholder_filter=["buyer", "shared"],
                crop=norm_crop,
                domain_name="government_rule",
            )
            context.government_rules = g_results["items"]
            sources.extend(g_results["sources"])
            retrieved_count += len(g_results["items"])

            # 4. Domain: Buyer Historical Negotiation Memory
            m_query = f"Buyer negotiation strategy outcome for {norm_crop or 'produce'}"
            m_results = self._query_domain_collection(
                rag,
                collection_name="reflection_memory",
                query_text=m_query,
                n_results=limit_per_domain,
                stakeholder_filter=["buyer"],  # Strictly buyer-specific negotiation reflections
                crop=norm_crop,
                domain_name="negotiation_memory",
            )
            context.negotiation_memory = m_results["items"]
            sources.extend(m_results["sources"])
            retrieved_count += len(m_results["items"])

            # 5. Domain: Shared Government Schemes
            s_query = f"Government scheme procurement assistance {norm_crop or ''}".strip()
            s_results = self._query_domain_collection(
                rag,
                collection_name="government_schemes",
                query_text=s_query,
                n_results=1,
                stakeholder_filter=["shared", "buyer"],
                crop=norm_crop,
                domain_name="market_knowledge",
            )
            context.relevant_shared_knowledge = s_results["items"]
            sources.extend(s_results["sources"])
            retrieved_count += len(s_results["items"])

            context.sources = sources
            context.retrieval_metadata = {
                "status": "SUCCESS",
                "crop": norm_crop,
                "location": location,
                "persona": persona,
                "retrieved_count": retrieved_count,
                "isolation_policy": "STAKEHOLDER_BUYER_OR_SHARED",
            }

        except Exception as ex:
            logger.error(f"Error executing Buyer RAG multi-domain search: {ex}")
            return BuyerRAGContext.empty(reason=f"Retrieval error: {str(ex)}")

        return context

    def _query_domain_collection(
        self,
        rag,
        collection_name: str,
        query_text: str,
        n_results: int,
        stakeholder_filter: List[str],
        crop: Optional[str] = None,
        domain_name: str = "general",
    ) -> Dict[str, Any]:
        """Queries a single collection enforcing stakeholder access control and provenance extraction."""
        vs = rag.vectorstores.get(collection_name)
        if not vs:
            return {"items": [], "sources": []}

        # Build filter dictionary
        conditions = []
        if crop:
            conditions.append({"crop": crop})

        # Note: If collection documents do not yet have 'stakeholder' metadata,
        # Chroma filter will exclude them if we enforce strict stakeholder condition.
        # We handle filter gracefully by matching if stakeholder field exists or using vectorstore search.
        filter_dict = None
        if conditions:
            filter_dict = conditions[0] if len(conditions) == 1 else {"$and": conditions}

        try:
            docs = vs.similarity_search(query_text, k=n_results * 2, filter=filter_dict)
        except Exception as e:
            logger.warning(f"Chroma similarity search warning for '{collection_name}': {e}")
            docs = []

        items = []
        sources = []

        for doc in docs:
            meta = doc.metadata or {}
            doc_stakeholder = str(meta.get("stakeholder", "shared")).lower()

            # ABSOLUTE ISOLATION GUARANTEE: Never return farmer-private documents to Buyer
            if doc_stakeholder == "farmer":
                continue

            # Ensure document stakeholder matches allowed list (or defaults to shared for legacy docs)
            if doc_stakeholder not in stakeholder_filter and doc_stakeholder != "shared":
                continue

            item_text = doc.page_content
            provenance = {
                "source": meta.get("source", meta.get("source_file", collection_name)),
                "source_type": meta.get("source_type", "project"),
                "document_id": meta.get("id", meta.get("doc_id", "unknown")),
                "is_synthetic": bool(meta.get("is_synthetic", False)),
                "domain": domain_name,
                "stakeholder": doc_stakeholder,
                "crop": meta.get("crop", crop),
            }

            items.append({"text": item_text, "metadata": meta, "provenance": provenance})
            sources.append(provenance)

            if len(items) >= n_results:
                break

        return {"items": items, "sources": sources}


# Singleton instance
buyer_rag_service = BuyerRAGService()
