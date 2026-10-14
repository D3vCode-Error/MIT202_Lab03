
import psycopg
from pymongo import MongoClient

print("Testing PostgreSQL connection...")

with psycopg.connect(
    host="127.0.0.1",
    port=5432,
    dbname="ecommerce",
    user="labuser",
    password="lab_postgres_pw"
) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM ecommerce.customers"
        )
        count = cur.fetchone()[0]
        print(f"PostgreSQL customers: {count}")

print("Testing MongoDB connection...")

client = MongoClient(
    "mongodb://labadmin:lab_mongo_pw"
    "@127.0.0.1:27017/"
    "?authSource=admin",
    serverSelectionTimeoutMS=5000
)

print(client.admin.command("ping"))
client.close()

print("Both database connections succeeded.")
