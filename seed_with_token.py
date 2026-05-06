"""Seed Datastore via GCLOUD_TOKEN (ADC non disponible sur ce poste).

Usage :
  $env:GCLOUD_TOKEN = (gcloud auth print-access-token)
  python seed_with_token.py --users 1000 --posts 50000 --follows 20
"""
import argparse
import os
import random
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.cloud import datastore

PROJECT   = "tp1cloud-489814"
BATCH     = 500


def get_client():
    token = os.environ.get("GCLOUD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GCLOUD_TOKEN non defini. Lance : $env:GCLOUD_TOKEN = (gcloud auth print-access-token)")
    return datastore.Client(project=PROJECT, credentials=Credentials(token=token))


def seed_users(client, num_users: int, follows_exact: int, prefix: str = "user"):
    """Cree/ecrase les users avec exactement follows_exact abonnes chacun."""
    names = [f"{prefix}{i}" for i in range(1, num_users + 1)]
    batch = []
    for name in names:
        key = client.key("User", name)
        entity = datastore.Entity(key)
        others = [u for u in names if u != name]
        selection = random.sample(others, min(follows_exact, len(others)))
        entity["follows"] = sorted(selection)
        batch.append(entity)
        if len(batch) >= BATCH:
            client.put_multi(batch)
            batch = []
    if batch:
        client.put_multi(batch)
    print(f"  Users : {num_users} crees avec {follows_exact} follows chacun")
    return names


def seed_posts(client, names: list, total_posts: int):
    """Cree total_posts posts repartis aleatoirement entre les users."""
    base_time = datetime.utcnow()
    batch = []
    for i in range(total_posts):
        author = random.choice(names)
        key = client.key("Post")
        post = datastore.Entity(key)
        post["author"] = author
        post["content"] = f"Post {i + 1}"
        post["created"] = base_time - timedelta(seconds=i)
        batch.append(post)
        if len(batch) >= BATCH:
            client.put_multi(batch)
            if (i + 1) % 10000 == 0:
                print(f"  Posts : {i + 1}/{total_posts}...")
            batch = []
    if batch:
        client.put_multi(batch)
    print(f"  Posts : {total_posts} crees")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--users",      type=int, default=1000)
    parser.add_argument("--posts",      type=int, default=50000)
    parser.add_argument("--follows",    type=int, default=20,
                        help="Nombre exact de followees par user (overwrite)")
    parser.add_argument("--prefix",     type=str, default="user")
    parser.add_argument("--skip-users", action="store_true",
                        help="Ne pas re-creer les users (posts seulement)")
    args = parser.parse_args()

    client = get_client()

    num_for_names = args.users if args.users > 0 else 1000
    names = [f"{args.prefix}{i}" for i in range(1, num_for_names + 1)]

    if not args.skip_users and args.users > 0:
        print(f"[Seed] {args.users} users | {args.posts} posts | {args.follows} follows/user")
        seed_users(client, args.users, args.follows, args.prefix)
    else:
        print(f"[Seed] skip users | {args.posts} posts (auteurs: {num_for_names} users)")

    seed_posts(client, names, args.posts)
    print("[Seed] Termine.")


if __name__ == "__main__":
    main()
