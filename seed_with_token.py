import subprocess
import random
import math
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.cloud import datastore

BATCH_SIZE = 500
PROJECT = "tp1cloud-489814"
USERS = 1000
POSTS_PER_USER = 50
FOLLOWS = 20
PREFIX = "user"

# Credentials depuis le token gcloud (compte déjà connecté)
print("[0/3] Récupération du token...")
# Le token est passé via la variable d'env GCLOUD_TOKEN (injecté depuis PowerShell)
import os
token = os.environ.get("GCLOUD_TOKEN", "").strip()
if not token:
    raise RuntimeError("Variable GCLOUD_TOKEN manquante. Lance depuis PowerShell avec $env:GCLOUD_TOKEN.")
creds = Credentials(token=token)
client = datastore.Client(project=PROJECT, credentials=creds)
print(f"      Token OK ({len(token)} chars)")

names = [f"{PREFIX}{i}" for i in range(1, USERS + 1)]

# --- 1. Utilisateurs ---
print(f"[1/3] Création de {USERS} utilisateurs (follows={FOLLOWS})...")
entities = []
for name in names:
    key = client.key("User", name)
    e = datastore.Entity(key)
    others = [u for u in names if u != name]
    e["follows"] = sorted(random.sample(others, min(FOLLOWS, len(others))))
    entities.append(e)

nb_batches = math.ceil(len(entities) / BATCH_SIZE)
for i in range(0, len(entities), BATCH_SIZE):
    client.put_multi(entities[i:i + BATCH_SIZE])
    print(f"  users batch {i // BATCH_SIZE + 1}/{nb_batches}")
print(f"  OK: {USERS} utilisateurs crees")

# --- 2. Posts ---
total_posts = USERS * POSTS_PER_USER
print(f"[2/3] Création de {total_posts} posts ({POSTS_PER_USER}/user)...")
base_time = datetime.utcnow()
posts = []
counter = 0
for author in names:
    for j in range(POSTS_PER_USER):
        key = client.key("Post")
        p = datastore.Entity(key)
        p["author"] = author
        p["content"] = f"Post {j + 1} by {author}"
        p["created"] = base_time - timedelta(seconds=counter)
        posts.append(p)
        counter += 1

nb_post_batches = math.ceil(len(posts) / BATCH_SIZE)
for i in range(0, len(posts), BATCH_SIZE):
    client.put_multi(posts[i:i + BATCH_SIZE])
    pct = int(100 * (i + BATCH_SIZE) / len(posts))
    print(f"  posts batch {i // BATCH_SIZE + 1}/{nb_post_batches}  ({min(pct,100)}%)")

print(f"  OK: {total_posts} posts crees")
print("[3/3] Seeding termine!")
