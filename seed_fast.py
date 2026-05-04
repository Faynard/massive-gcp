from __future__ import annotations
import argparse
import random
import math
from datetime import datetime, timedelta
from google.cloud import datastore

BATCH_SIZE = 500  # Limite Datastore pour put_multi


def parse_args():
    p = argparse.ArgumentParser(description="Seeder rapide pour TinyInsta")
    p.add_argument("--users", type=int, default=1000, help="Nombre d'utilisateurs")
    p.add_argument("--posts-per-user", type=int, default=50, help="Posts par utilisateur")
    p.add_argument("--follows", type=int, default=20, help="Nombre de followees par utilisateur")
    p.add_argument("--prefix", type=str, default="user", help="Préfixe des usernames")
    p.add_argument("--dry-run", action="store_true", help="Simulation sans écriture")
    return p.parse_args()


def batch_put(client: datastore.Client, entities: list, dry: bool):
    """Écrit une liste d'entités en batches de BATCH_SIZE."""
    for i in range(0, len(entities), BATCH_SIZE):
        chunk = entities[i: i + BATCH_SIZE]
        if not dry:
            client.put_multi(chunk)
        print(f"  → Batch {i // BATCH_SIZE + 1}/{math.ceil(len(entities) / BATCH_SIZE)} ({len(chunk)} entités)")


def create_users(client: datastore.Client, names: list[str], follows: int, dry: bool) -> int:
    """Crée (ou met à jour) les utilisateurs avec leurs followees assignés aléatoirement."""
    print(f"\n[1/3] Création de {len(names)} utilisateurs (follows={follows})...")
    entities = []
    for name in names:
        key = client.key("User", name)
        entity = datastore.Entity(key)
        others = [u for u in names if u != name]
        nb_follows = min(follows, len(others))
        entity["follows"] = sorted(random.sample(others, nb_follows))
        entities.append(entity)

    batch_put(client, entities, dry)
    print(f"  ✓ {len(names)} utilisateurs {'simulés' if dry else 'créés/mis à jour'}.")
    return len(names)


def create_posts(client: datastore.Client, names: list[str], posts_per_user: int, dry: bool) -> int:
    """Crée les posts en batch (posts_per_user posts par utilisateur)."""
    total = len(names) * posts_per_user
    print(f"\n[2/3] Création de {total} posts ({posts_per_user} par utilisateur)...")
    base_time = datetime.utcnow()
    entities = []
    counter = 0
    for author in names:
        for j in range(posts_per_user):
            key = client.key("Post")
            post = datastore.Entity(key)
            post["author"] = author
            post["content"] = f"Post {j + 1} by {author}"
            # Timestamps artificiellement décalés pour avoir un tri naturel
            post["created"] = base_time - timedelta(seconds=counter)
            entities.append(post)
            counter += 1

    batch_put(client, entities, dry)
    print(f"  ✓ {total} posts {'simulés' if dry else 'créés'}.")
    return total


def main():
    args = parse_args()
    client = datastore.Client()

    names = [f"{args.prefix}{i}" for i in range(1, args.users + 1)]

    print("=" * 55)
    print("  TinyInsta — Seeder Rapide (Batch)")
    print("=" * 55)
    print(f"  Utilisateurs  : {args.users}  (préfixe: '{args.prefix}')")
    print(f"  Posts/user    : {args.posts_per_user}  (total: {args.users * args.posts_per_user})")
    print(f"  Followees     : {args.follows} par utilisateur")
    if args.dry_run:
        print("  MODE DRY-RUN  : aucune écriture ne sera effectuée")
    print("=" * 55)

    create_users(client, names, args.follows, args.dry_run)
    create_posts(client, names, args.posts_per_user, args.dry_run)

    print("\n[3/3] Terminé ✓")
    print(f"  Testez avec : /api/timeline?user={names[0]}&limit=20")


if __name__ == "__main__":
    main()
