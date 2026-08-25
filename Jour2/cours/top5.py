from pymongo import MongoClient

client = MongoClient("mongodb://admin:ipssi2025@localhost:27017/?authSource=admin")
db = client["ecommerce"]

pipeline = [
    # 1. Exclure les commandes annulées
    {"$match": {"statut": {"$ne": "annulee"}}},
    
    # 2. Regrouper par client et sommer les montants
    {"$group": {
        "_id": "$client_id",
        "total_depense": {"$sum": "$montant_total"},
        "nb_commandes": {"$sum": 1}
    }},
    
    # 3. Trier par CA décroissant et limiter au top 5
    {"$sort": {"total_depense": -1}},
    {"$limit": 5},
    
    # 4. Jointure avec la collection clients
    {"$lookup": {
        "from": "clients",
        "localField": "_id",
        "foreignField": "_id",
        "as": "client_info"
    }},
    
    # 5. Aplatir l'objet client
    {"$unwind": "$client_info"}
]

print("\n" + "="*50)
print("       TOP 5 CLIENTS PAR CHIFFRE D'AFFAIRES")
print("="*50)

results = db.commandes.aggregate(pipeline)

for i, doc in enumerate(results, start=1):
    nom = doc["client_info"]["nom"]
    email = doc["client_info"]["email"]
    total = doc["total_depense"]
    commandes = doc["nb_commandes"]
    print(f"{i}. {nom:<25} | {email:<30} | {commandes} cmd(s) | Total: {total:8.2f} €")

print("="*50 + "\n")

client.close()