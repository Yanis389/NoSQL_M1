import sys
import time
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError

def run_writer(uri):
    # Timeout de selection fixe a 5000 ms[cite: 9]
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client["census"]
    collection = db["heartbeat"]
    
    success_count = 0
    fail_count = 0
    doc_id = 0

    print("--- Demarrage du script de resilience ---")
    
    while doc_id < 60:
        doc_id += 1
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        try:
            primary_node = client.primary or "Aucun"
            res = collection.insert_one({"seq": doc_id, "timestamp": now})
            success_count += 1
            print(f"[{now}] OK - Primary: {primary_node} - ID: {res.inserted_id}")
        except PyMongoError as e:
            fail_count += 1
            print(f"[{now}] ECHEC - Erreur: {type(e).__name__} | Details: {e}")
        
        time.sleep(1)

    print("\n--- Bilan de l'execution ---")
    print(f"Ecritures confirmees par l'application : {success_count}")
    print(f"Ecritures echouees : {fail_count}")
    
    try:
        real_count = collection.count_documents({})
        print(f"Nombre reel de documents en base (count_documents) : {real_count}")
    except Exception as e:
        print(f"Impossible de lire le total en base : {e}")

if __name__ == "__main__":
    connection_uri = sys.argv[1] if len(sys.argv) > 1 else "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/?replicaSet=rs0&retryWrites=true"
    run_writer(connection_uri)