import os
# Set environment variables before imports to disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"

"""
backend/services/rag_service.py

ChromaDB RAG vector search engine for regional mandi prices
and past agent negotiation strategy logs.
"""

import json
import logging
from sentence_transformers import SentenceTransformer
import chromadb
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma
from config.settings import CHROMA_URL, EMBEDDING_MODEL
from typing import List, Dict, Any

class AwaitableDict(dict):
    def __await__(self):
        async def _identity():
            return self
        return _identity().__await__()

class AwaitableNone:
    def __await__(self):
        async def _identity():
            return None
        return _identity().__await__()

# Set up logging and mute verbose external libraries
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGService")
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

# Using dynamic embedding model, falling back to all-MiniLM-L6-v2 for fast local testing
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

COLLECTION_NAMES = [
    "crop_knowledge",
    "historical_negotiations",
    "government_rules",
    "government_schemes",
    "market_prices",
    "weather_knowledge",
    "warehouse_knowledge",
    "transport_knowledge",
    "farmer_profiles",
    "buyer_profiles",
    "reflection_memory",
    "trust_memory",
    "learning_memory",
    "recommendations",
]

class SentenceTransformerEmbeddings(Embeddings):
    """LangChain wrapper for SentenceTransformer embedding models."""

    def __init__(self, model: SentenceTransformer):
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()


class RAGService:
    """Vector database service utilizing ChromaDB and SentenceTransformers."""
    
    def __init__(self):
        logger.info(f"Loading SentenceTransformer model '{EMBEDDING_MODEL}'...")
        try:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception as e:
            logger.warning(f"Failed to load {EMBEDDING_MODEL}. Falling back to default: {e}")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        self.langchain_embeddings = SentenceTransformerEmbeddings(self.embedding_model)
        self.client = None
        self.collections: dict = {}
        self.vectorstores: dict = {}
        self.mandi_collection = None
        self.strategies_collection = None

        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self._init_client())
            else:
                asyncio.run(self._init_client())
        except RuntimeError:
            try:
                asyncio.run(self._init_client())
            except Exception as e:
                logger.warning(f"ChromaDB client initialization deferred: {e}")

    async def _init_client(self):
        """Initialize Chroma client with failsafe fallbacks."""
        try:
            # Parse CHROMA_URL from settings
            host = "localhost"
            port = 8001
            if CHROMA_URL and "://" in CHROMA_URL:
                parts = CHROMA_URL.split("://")[1].split(":")
                host = parts[0]
                if len(parts) > 1:
                    port = int(parts[1])
            self.client = chromadb.HttpClient(host=host, port=port)
            self.client.heartbeat()
            logger.info(f"Connected to external ChromaDB server at {host}:{port}")
        except Exception as e:
            logger.warning(f"External ChromaDB HTTP client failed: {e}. Falling back to local PersistentClient.")
            try:
                self.client = chromadb.PersistentClient(path="./node_storage/chroma_db_v2")
                logger.info("Connected to local PersistentClient for ChromaDB.")
            except Exception as ex:
                logger.error(f"Persistent local client failed: {ex}. Using EphemeralClient.")
                self.client = chromadb.EphemeralClient()

        # Initialize all collections
        for name in COLLECTION_NAMES:
            try:
                col = self.client.get_or_create_collection(
                    name=name,
                    metadata={"description": f"AgriNegotiator {name} vector store (bge-m3)"}
                )
                self.collections[name] = col
                
                # Wrap with LangChain Chroma vector store integration
                self.vectorstores[name] = Chroma(
                    client=self.client,
                    collection_name=name,
                    embedding_function=self.langchain_embeddings
                )
            except Exception as ex_col:
                logger.error(f"Error creating collection '{name}': {ex_col}")

        # Aliases for backward compatibility
        self.mandi_collection = self.collections.get("market_prices")
        self.strategies_collection = self.collections.get("reflection_memory")
        self.mandi_pricing_index = self.collections.get("market_prices")
        self.strategies_index = self.collections.get("reflection_memory")
        
        # Bind vector store properties/fields for backward compatibility with tests
        self.vector_store_crop_knowledge = self.collections.get("crop_knowledge")
        self.vector_store_mandi = self.collections.get("market_prices")
        
        # Verify and rebuild mismatched collections on startup
        try:
            self.verify_and_rebuild_dimensions()
        except Exception as e_verify:
            logger.warning(f"Could not verify collection dimensions on startup: {e_verify}")
        
        logger.info(f"Initialized {len(self.collections)} ChromaDB collections.")

    def verify_and_rebuild_dimensions(self):
        """Check all collections for dimension mismatch against active model. Drop and recreate if mismatched."""
        expected_dim = self.embedding_model.get_sentence_embedding_dimension()
        for name in COLLECTION_NAMES:
            vs = self.vectorstores.get(name)
            if vs:
                col = vs._collection
                try:
                    if col.count() > 0:
                        peek_res = col.peek(limit=1)
                        if peek_res and peek_res.get("embeddings") is not None and len(peek_res["embeddings"]) > 0:
                            dim = len(peek_res["embeddings"][0])
                            if dim != expected_dim:
                                logger.warning(f"Collection '{name}' dimension mismatch: {dim} vs expected {expected_dim}. Clearing collection.")
                                self._clear_collection(name)
                except Exception as e:
                    logger.error(f"Error checking dimension of collection '{name}': {e}")

    def _build_where_filter(self, crop: str = None, district: str = None, date: str = None, where_dict: dict = None, collection_name: str = None) -> dict:
        """Helper to build a composite metadata filter dictionary compatible with ChromaDB / LangChain."""
        conditions = []
        if crop:
            import sys
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
            from shared.crop_master import get_crop_by_name
            canonical = get_crop_by_name(crop)
            if canonical:
                if collection_name == "reflection_memory":
                    conditions.append({"crop": canonical["ml_mapping"]})
                else:
                    conditions.append({"crop": canonical["rag_mapping"]})
            else:
                logger.error(f"RAG query received invalid crop: {crop}. Aborting query.")
                raise ValueError(f"Unsupported crop: {crop}")
        if district:
            conditions.append({"district": district.strip().capitalize()})
        if date:
            conditions.append({"date": date})
        if where_dict:
            for k, v in where_dict.items():
                conditions.append({k: v})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _clear_collection(self, name: str):
        """Helper to safely drop and recreate a collection to avoid dimension mismatch errors."""
        logger.info(f"Clearing collection '{name}'...")
        try:
            self.client.delete_collection(name)
        except Exception as e:
            logger.warning(f"Could not delete collection {name}: {e}")
        
        try:
            col = self.client.get_or_create_collection(
                name=name,
                metadata={"description": f"AgriNegotiator {name} vector store"}
            )
            self.collections[name] = col
            self.vectorstores[name] = Chroma(
                client=self.client,
                collection_name=name,
                embedding_function=self.langchain_embeddings
            )
        except Exception as e:
            logger.error(f"Error recreating collection '{name}': {e}")

    def embed_text(self, text: str) -> list:
        """Encode text to vector space."""
        return self.embedding_model.encode(text).tolist()

    def add_document(self, collection_name: str, doc_id: str, text: str, metadata: dict):
        """Insert document into named vector collection using LangChain vector store."""
        vs = self.vectorstores.get(collection_name)
        if not vs:
            return
        meta = dict(metadata)
        meta["id"] = doc_id
        vs.add_texts(texts=[text], metadatas=[meta], ids=[doc_id])

    def query_collection(self, collection_name: str, query_text: str, n_results: int = 3, where_dict: dict = None) -> dict:
        """Search a specific vector collection by semantic similarity using LangChain Chroma."""
        vs = self.vectorstores.get(collection_name)
        if not vs:
            return {}
        
        # Query using LangChain similarity search
        docs = vs.similarity_search(query_text, k=n_results, filter=where_dict)
        
        # Format back to raw-compatible Chroma output dict format
        documents = [doc.page_content for doc in docs]
        metadatas = [doc.metadata for doc in docs]
        ids = [doc.metadata.get("id", f"id_{i}") for i, doc in enumerate(docs)]
        
        return {
            "documents": [documents],
            "metadatas": [metadatas],
            "ids": [ids]
        }

    # Legacy helper wrappers made sync/async compatible
    def add_mandi_record(self, record_id: str, text: str, metadata: dict):
        self.add_document("market_prices", record_id, text, metadata)
        return AwaitableNone()

    def query_mandi_records(self, query_text: str, n_results: int = 3, crop: str = None, district: str = None, date: str = None, where_dict: dict = None) -> dict:
        filter_dict = self._build_where_filter(crop=crop, district=district, date=date, where_dict=where_dict, collection_name="market_prices")
        res = self.query_collection("market_prices", query_text, n_results, filter_dict)
        return AwaitableDict(res)

    def add_strategy_log(self, log_id: str, text: str, metadata: dict):
        self.add_document("reflection_memory", log_id, text, metadata)
        return AwaitableNone()

    def query_strategies(self, query_text: str, n_results: int = 3, crop: str = None, district: str = None, date: str = None, where_dict: dict = None) -> dict:
        filter_dict = self._build_where_filter(crop=crop, district=district, date=date, where_dict=where_dict, collection_name="reflection_memory")
        res = self.query_collection("reflection_memory", query_text, n_results, filter_dict)
        return AwaitableDict(res)

    def query_crop_knowledge(self, query_text: str, crop: str = None, district: str = None, date: str = None, n_results: int = 3, where_dict: dict = None) -> List[Dict[str, Any]]:
        """Search crop guidelines with optional metadata filtering."""
        vs = self.vectorstores.get("crop_knowledge")
        if not vs:
            return []
        
        filter_dict = self._build_where_filter(crop=crop, district=district, date=date, where_dict=where_dict, collection_name="crop_knowledge")
        docs = vs.similarity_search(query_text, k=n_results, filter=filter_dict)
        
        formatted = []
        for doc in docs:
            formatted.append({"text": doc.page_content, "metadata": doc.metadata})
        return formatted

    def query_government_schemes(self, query_text: str, crop: str = None, district: str = None, date: str = None, n_results: int = 3, where_dict: dict = None) -> List[Dict[str, Any]]:
        """Search government scheme guidelines."""
        vs = self.vectorstores.get("government_schemes")
        if not vs:
            return []
        
        filter_dict = self._build_where_filter(crop=crop, district=district, date=date, where_dict=where_dict, collection_name="government_schemes")
        docs = vs.similarity_search(query_text, k=n_results, filter=filter_dict)
        
        formatted = []
        for doc in docs:
            formatted.append({"text": doc.page_content, "metadata": doc.metadata})
        return formatted

    def ingest_knowledge_base(self):
        """Parse PDFs and Markdown files from datasets and index them in bulk."""
        base_dir = os.path.dirname(__file__)
        dataset_dir = os.path.abspath(os.path.join(base_dir, "..", "dataset"))
        crop_knowledge_dir = os.path.join(dataset_dir, "crop_knowledge")
        gov_schemes_dir = os.path.join(dataset_dir, "government_schemes")

        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

        # 1. Ingest Crop Knowledge
        if os.path.exists(crop_knowledge_dir):
            vs_crop = self.vectorstores.get("crop_knowledge")

            for filename in os.listdir(crop_knowledge_dir):
                filepath = os.path.join(crop_knowledge_dir, filename)
                docs = []
                crop_tag = "General"
                lower_name = filename.lower()
                if "onion" in lower_name:
                    crop_tag = "Onion"
                elif "tomato" in lower_name:
                    crop_tag = "Tomato"
                elif "cotton" in lower_name:
                    crop_tag = "Cotton"

                try:
                    if filename.endswith(".pdf"):
                        logger.info(f"Parsing crop knowledge PDF: {filename} (Tag={crop_tag})...")
                        loader = PyPDFLoader(filepath)
                        docs = loader.load_and_split(text_splitter=splitter)
                    elif filename.endswith(".md") or filename.endswith(".txt"):
                        logger.info(f"Parsing crop knowledge MD: {filename} (Tag={crop_tag})...")
                        loader = TextLoader(filepath, encoding="utf-8")
                        docs = loader.load_and_split(text_splitter=splitter)

                    if docs and vs_crop is not None:
                        ids = [f"crop_know_{filename}_{i}" for i in range(len(docs))]
                        
                        # Incremental check
                        existing = vs_crop._collection.get(ids=ids)
                        existing_ids = set(existing.get("ids", []))
                        
                        new_docs = []
                        new_metadatas = []
                        new_ids = []
                        for i, doc in enumerate(docs):
                            if ids[i] not in existing_ids:
                                new_docs.append(doc)
                                new_ids.append(ids[i])
                                new_metadatas.append({"crop": crop_tag, "source": filename, "id": ids[i]})
                        
                        if new_ids:
                            logger.info(f"Indexing {len(new_ids)} new chunks from {filename}...")
                            batch_size = 32
                            for start_idx in range(0, len(new_ids), batch_size):
                                end_idx = start_idx + batch_size
                                batch_texts = [d.page_content for d in new_docs[start_idx:end_idx]]
                                batch_metas = new_metadatas[start_idx:end_idx]
                                batch_ids = new_ids[start_idx:end_idx]
                                vs_crop.add_texts(texts=batch_texts, metadatas=batch_metas, ids=batch_ids)
                                logger.info(f"  Indexed batch {start_idx // batch_size + 1}/{(len(new_ids) - 1) // batch_size + 1} ({len(batch_texts)} chunks)")
                        else:
                            logger.info(f"All chunks from {filename} already indexed. Skipping.")
                except Exception as ex:
                    logger.error(f"Error indexing crop knowledge file {filename}: {ex}")

        # 2. Ingest Government Schemes
        if os.path.exists(gov_schemes_dir):
            vs_schemes = self.vectorstores.get("government_schemes")

            for filename in os.listdir(gov_schemes_dir):
                filepath = os.path.join(gov_schemes_dir, filename)
                docs = []
                try:
                    if filename.endswith(".pdf"):
                        logger.info(f"Parsing government scheme PDF: {filename}...")
                        loader = PyPDFLoader(filepath)
                        docs = loader.load_and_split(text_splitter=splitter)

                    if docs and vs_schemes is not None:
                        ids = [f"gov_scheme_{filename}_{i}" for i in range(len(docs))]
                        
                        # Incremental check
                        existing = vs_schemes._collection.get(ids=ids)
                        existing_ids = set(existing.get("ids", []))
                        
                        new_docs = []
                        new_metadatas = []
                        new_ids = []
                        for i, doc in enumerate(docs):
                            if ids[i] not in existing_ids:
                                new_docs.append(doc)
                                new_ids.append(ids[i])
                                new_metadatas.append({"source": filename, "id": ids[i]})
                        
                        if new_ids:
                            logger.info(f"Indexing {len(new_ids)} new chunks from {filename}...")
                            batch_size = 32
                            for start_idx in range(0, len(new_ids), batch_size):
                                end_idx = start_idx + batch_size
                                batch_texts = [d.page_content for d in new_docs[start_idx:end_idx]]
                                batch_metas = new_metadatas[start_idx:end_idx]
                                batch_ids = new_ids[start_idx:end_idx]
                                vs_schemes.add_texts(texts=batch_texts, metadatas=batch_metas, ids=batch_ids)
                                logger.info(f"  Indexed batch {start_idx // batch_size + 1}/{(len(new_ids) - 1) // batch_size + 1} ({len(batch_texts)} chunks)")
                        else:
                            logger.info(f"All chunks from {filename} already indexed. Skipping.")
                except Exception as ex:
                    logger.error(f"Error indexing government scheme {filename}: {ex}")

    def ingest_mandi_prices_and_negotiations(self):
        """Load cleaned mandi prices and historical logs into ChromaDB in bulk."""
        base_dir = os.path.dirname(__file__)
        dataset_dir = os.path.abspath(os.path.join(base_dir, "..", "dataset"))
        mandi_file = os.path.join(dataset_dir, "cleaned_mandi_prices.json")
        neg_file = os.path.join(dataset_dir, "historical_negotiations.json")

        # 1. Ingest Mandi Prices
        if os.path.exists(mandi_file):
            with open(mandi_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            
            # Read MSP values to attach as metadata for agent context if available
            msp_map = {}
            msp_file = os.path.join(dataset_dir, "cleaned_msp_prices.json")
            if os.path.exists(msp_file):
                with open(msp_file, "r", encoding="utf-8") as f:
                    msp_data = json.load(f)
                    for m in msp_data:
                        msp_map[m["crop"]] = m.get("msp_price_per_quintal")

            ids = [f"mandi_idx_{idx}" for idx in range(len(records))]
            vs_mandi = self.vectorstores.get("market_prices")
            if vs_mandi is not None:
                # Incremental check
                existing = vs_mandi._collection.get(ids=ids)
                existing_ids = set(existing.get("ids", []))
                
                new_texts = []
                new_metadatas = []
                new_ids = []
                for idx, r in enumerate(records):
                    doc_id = ids[idx]
                    if doc_id not in existing_ids:
                        msp_val = msp_map.get(r["crop"])
                        msp_str = f"₹{msp_val:.2f}/quintal" if msp_val else "Not Available"
                        
                        text = (
                            f"Market transaction: Crop {r['crop']} ({r.get('crop_full_name', r['crop'])}) at "
                            f"{r.get('mandi_name', r.get('mandi', 'Unknown Mandi'))} in state {r.get('state', 'Maharashtra')}. Date: {r['date']}.\n"
                            f"Price: ₹{r['price_per_quintal']:.2f}/quintal (₹{r['price_per_quintal']/100:.2f}/kg).\n"
                            f"Government MSP (2026-27): {msp_str}.\n"
                            f"Mandi arrivals volume: {r.get('arrival_mt', 0.0):.2f} metric tonnes."
                        )
                        new_texts.append(text)
                        new_ids.append(doc_id)
                        new_metadatas.append({
                            "crop": r["crop"],
                            "date": r["date"],
                            "state": r["state"],
                            "district": r.get("district", r.get("mandi_name", "Maharashtra")),
                            "mandi": r["mandi_name"],
                            "source_file": "cleaned_mandi_prices.json",
                            "data_type": "market_price",
                            "id": doc_id,
                            "min_price": r["price_per_quintal"],
                            "max_price": r["price_per_quintal"],
                            "modal_price": r["price_per_quintal"],
                            "msp": msp_val or 0.0
                        })
                
                if new_ids:
                    logger.info(f"Indexing {len(new_ids)} new mandi price records...")
                    batch_size = 32
                    for start_idx in range(0, len(new_ids), batch_size):
                        end_idx = start_idx + batch_size
                        vs_mandi.add_texts(
                            texts=new_texts[start_idx:end_idx],
                            metadatas=new_metadatas[start_idx:end_idx],
                            ids=new_ids[start_idx:end_idx]
                        )
                    logger.info(f"Successfully indexed {len(new_ids)} new mandi records.")
                else:
                    logger.info("All mandi price records already indexed. Skipping.")

        # 2. Ingest Historical Negotiations
        if os.path.exists(neg_file):
            with open(neg_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            
            ids = [r["negotiation_id"] for r in records]
            vs_strategies = self.vectorstores.get("reflection_memory")
            if vs_strategies is not None:
                # Incremental check
                existing = vs_strategies._collection.get(ids=ids)
                existing_ids = set(existing.get("ids", []))
                
                new_texts = []
                new_metadatas = []
                new_ids = []
                for r in records:
                    doc_id = r["negotiation_id"]
                    if doc_id not in existing_ids:
                        text = (
                            f"Historical Negotiation Outcome: {r['outcome_summary']}\n"
                            f"Crop: {r['crop']} ({r['variety']}), Grade: {r['grade']}, quantity: {r['quantity']}kg.\n"
                            f"Location: district {r['district']}.\n"
                            f"Farmer strategy: {r['negotiation_strategy_used']['farmer']}, "
                            f"Buyer strategy: {r['negotiation_strategy_used']['buyer']}.\n"
                            f"Initial pricing: Farmer started at ₹{r['farmer_initial_offer']:.2f}/kg, "
                            f"Buyer bid ₹{r['buyer_initial_offer']:.2f}/kg. "
                            f"Final price: ₹{r['final_agreed_price']:.2f}/kg" if r['final_agreed_price'] else "Deal failed."
                        )
                        date_str = r["timestamp"].split("T")[0] if "T" in r.get("timestamp", "") else ""
                        new_texts.append(text)
                        new_ids.append(doc_id)
                        new_metadatas.append({
                            "crop": r["crop"],
                            "district": r["district"],
                            "deal_status": r["deal_status"],
                            "grade": r["grade"],
                            "date": date_str,
                            "id": doc_id,
                            "data_type": "historical_negotiation",
                            "source_file": "historical_negotiations.json"
                        })
                
                if new_ids:
                    logger.info(f"Indexing {len(new_ids)} new historical negotiations...")
                    batch_size = 32
                    for start_idx in range(0, len(new_ids), batch_size):
                        end_idx = start_idx + batch_size
                        vs_strategies.add_texts(
                            texts=new_texts[start_idx:end_idx],
                            metadatas=new_metadatas[start_idx:end_idx],
                            ids=new_ids[start_idx:end_idx]
                        )
                    logger.info(f"Successfully indexed {len(new_ids)} new negotiations.")
                else:
                    logger.info("All historical negotiations already indexed. Skipping.")


# Singleton instance
rag_service = RAGService()

