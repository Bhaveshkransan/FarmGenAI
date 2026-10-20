import psycopg2
import inspect
from backend.services.price_prediction_service import predict_price_xgboost

print("predict_price_xgboost signature:", inspect.signature(predict_price_xgboost))

conn = psycopg2.connect("postgresql://admin:admin_password@postgres:5432/agrinegotiator")
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
tables = [r[0] for r in cur.fetchall()]
print("PostgreSQL Tables:", tables)

for t in tables:
    try:
        cur.execute(f"SELECT COUNT(1) FROM {t};")
        cnt = cur.fetchone()[0]
        print(f"  - Table '{t}': {cnt} rows")
    except Exception as e:
        print(f"  - Table '{t}': error ({e})")
        conn.rollback()

cur.close()
conn.close()
