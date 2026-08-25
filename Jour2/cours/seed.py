import random
from datetime import datetime, timedelta
from faker import Faker
from pymongo import MongoClient

fake = Faker('fr_FR')

# Connexion à MongoDB Local (Docker)
client = MongoClient("mongodb://admin:ipssi2025@localhost:27017/?authSource=admin")
db = client["ecommerce"]

print("Nettoyage des collections existantes...")
db.clients.drop()
db.produits.drop()
db.commandes.drop()

print("1/3 - Génération des 1 000 clients...")
clients_data = []
for _ in range(1000):
    clients_data.append({
        "nom": fake.name(),
        "email": fake.unique.email(),
        "ville": fake.city(),
        "date_inscription": fake.date_time_between(start_date="-2y", end_date="now")
    })
res_clients = db.clients.insert_many(clients_data)
client_ids = res_clients.inserted_ids

print("2/3 - Génération des 200 produits...")
categories = ["Tech", "Maison", "Vêtements", "Sport", "Livres"]
produits_data = []
for _ in range(200):
    produits_data.append({
        "nom": f"{fake.word().capitalize()} {fake.word()}",
        "description": fake.sentence(nb_words=12),
        "prix": round(random.uniform(5.0, 450.0), 2),
        "stock": random.choice([0, 0, random.randint(1, 80)]),  # ~20% de produits en rupture
        "categorie": random.choice(categories)
    })
res_produits = db.produits.insert_many(produits_data)
produits_list = list(db.produits.find({}, {"_id": 1, "nom": 1, "prix": 1}))

print("3/3 - Génération des 5 000 commandes...")
commandes_data = []
statuts = ["payee", "expediee", "livree", "annulee"]

for _ in range(5000):
    c_id = random.choice(client_ids)
    nb_articles = random.randint(1, 4)
    lignes = []
    total_cmd = 0.0
    
    articles_choisis = random.sample(produits_list, nb_articles)
    for art in articles_choisis:
        qte = random.randint(1, 3)
        pu = art["prix"]
        total_cmd += pu * qte
        lignes.append({
            "produit_id": art["_id"],
            "nom": art["nom"],
            "prix_unitaire": pu,
            "quantite": qte
        })
        
    commandes_data.append({
        "client_id": c_id,
        "date": fake.date_time_between(start_date="-1y", end_date="now"),
        "statut": random.choice(statuts),
        "montant_total": round(total_cmd, 2),
        "lignes": lignes
    })

db.commandes.insert_many(commandes_data)
print(" Base e-commerce générée avec succès !")
client.close()