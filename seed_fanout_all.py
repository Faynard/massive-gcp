import os, random, math
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.cloud import datastore

BATCH_SIZE = 500
PROJECT = "tp1cloud-489814"
USERS = 1000
POSTS_PER_USER = 100

DATASETS = [
    {"follows": 20, "prefix": "f20user"},
    {"follows": 40, "prefix": "f40user"},
    {"follows": 60, "prefix": "f60user"},
]

token = os.environ.get("GCLOUD_TOKEN", "").strip()
if not token:
    raise RuntimeError("GCLOUD_TOKEN manquant")

creds = Credentials(token=token)
client = datastore.Client(project=PROJECT, credentials=creds)

for ds in DATASETS:
    follows = ds["follows"]
    prefix = ds["prefix"]
    names = [f"{prefix}{i}" for i in range(1, USERS + 1)]

    print(f"\n=== Dataset: prefix={prefix}, follows={follows} ===")

    # -- Users --
    print(f"  [1/2] {USERS} users...")
    entities = []
    for name in names:
        key = client.key("User", name)
        e = datastore.Entity(key)
        others = [u for u in names if u != name]
        e["follows"] = sorted(random.sample(others, min(follows, len(others))))
        entities.append(e)
    for i in range(0, len(entities), BATCH_SIZE):
        client.put_multi(entities[i:i+BATCH_SIZE])
    print(f"  OK: {USERS} users")

    # -- Posts --
    total = USERS * POSTS_PER_USER
    print(f"  [2/2] {total} posts...")
    base_time = datetime.utcnow()
    posts = []
    counter = 0
    for author in names:
        for j in range(POSTS_PER_USER):
            key = client.key("Post")
            p = datastore.Entity(key)
            p["author"] = author
            p["content"] = f"Post {j+1} by {author}"
            p["created"] = base_time - timedelta(seconds=counter)
            posts.append(p)
            counter += 1
    nb_b = math.ceil(len(posts) / BATCH_SIZE)
    for i in range(0, len(posts), BATCH_SIZE):
        client.put_multi(posts[i:i+BATCH_SIZE])
        pct = min(100, int(100*(i+BATCH_SIZE)/len(posts)))
        print(f"    batch {i//BATCH_SIZE+1}/{nb_b} ({pct}%)")
    print(f"  OK: {total} posts")

print("\nSeeding fanout termine!")
