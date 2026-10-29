import requests
import redis
import psycopg2
import sys

def verify():
    print("=== ENVIRONMENT HEALTH AUDIT ===")
    
    # 1. Backend HTTP Health
    try:
        h = requests.get("http://localhost:8000/health", timeout=5).json()
        print(f"1. Backend Health: {h}")
    except Exception as e:
        print(f"1. Backend Health FAILED: {e}")

    # 2. Redis
    try:
        r = redis.Redis(host="redis", port=6379, socket_timeout=5)
        ping = r.ping()
        print(f"2. Redis Ping: {ping} (keys: {len(r.keys('*'))})")
    except Exception as e:
        print(f"2. Redis FAILED: {e}")

    # 3. PostgreSQL
    try:
        conn = psycopg2.connect("postgresql://admin:admin_password@postgres:5432/agrinegotiator")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM negotiations;")
        neg_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(1) FROM crop_listings;")
        prod_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(1) FROM users;")
        user_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(1) FROM vehicles;")
        veh_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f"3. PostgreSQL Connected: negotiations={neg_count}, crop_listings={prod_count}, users={user_count}, vehicles={veh_count}")
    except Exception as e:
        print(f"3. PostgreSQL FAILED: {e}")

    # 4. ChromaDB
    try:
        ch = requests.get("http://chromadb:8000/api/v2/heartbeat", timeout=5)
        print(f"4. ChromaDB v2 Heartbeat: {ch.status_code}")
    except Exception as e:
        print(f"4. ChromaDB FAILED: {e}")

    # 5. XGBoost Price Prediction Model
    try:
        from backend.services.price_prediction_service import predict_price_xgboost
        pred = predict_price_xgboost(crop="Soybean", district="Latur")
        print(f"5. XGBoost Model: OK -> Soybean in Latur predicted modal={pred.get('predicted_price')} ({pred.get('trend')})")
    except Exception as e:
        print(f"5. XGBoost FAILED: {e}")

    # 6. RAG Service Embedding Model
    try:
        from backend.services.rag_service import rag_service
        chunks = rag_service.query_crop_knowledge("Soybean APMC guidelines", crop="Soybean", n_results=2)
        print(f"6. RAG Service: OK -> Retrieved {len(chunks)} chunks from crop knowledge")
    except Exception as e:
        print(f"6. RAG Service FAILED: {e}")

if __name__ == "__main__":
    verify()
