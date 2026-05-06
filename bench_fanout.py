"""Expérience 2 — Passage à l'échelle en fanout.

Usage :
  $env:GCLOUD_TOKEN = (gcloud auth print-access-token)
  python bench_fanout.py --host https://tp1cloud-489814.ew.r.appspot.com
"""
import argparse
import csv
import os
import tempfile
import time

from bench_utils import get_instance_count, kill_instances, run_locust
from seed_with_token import get_client, seed_users

FOLLOWEE_LEVELS     = [20, 40, 60]
NB_CONCURRENT_USERS = 50
NB_RUNS             = 3
NUM_USERS           = 1000
OUT_FILE            = os.path.join("out", "fanout.csv")
CSV_HEADER          = ["PARAM", "AVG_TIME", "RUN", "FAILED", "NB_INSTANCES"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--run-time", type=int, default=30)
    parser.add_argument("--runs",     type=int, default=NB_RUNS)
    args = parser.parse_args()

    os.makedirs("out", exist_ok=True)
    client = get_client()
    rows = []

    print("\n" + "=" * 60)
    print("  EXPERIENCE : Passage a l'echelle sur le fanout")
    print("=" * 60)
    print(f"  Concurrence fixe : {NB_CONCURRENT_USERS} users | Fanout testes : {FOLLOWEE_LEVELS}")

    with tempfile.TemporaryDirectory() as tmpdir:
        for follows in FOLLOWEE_LEVELS:
            print(f"\n>> Fanout = {follows} followees/user")
            print(f"  Mise a jour follows -> {follows} par user...")
            seed_users(client, num_users=NUM_USERS, follows_exact=follows)
            kill_instances()

            for run in range(1, args.runs + 1):
                print(f"  Run {run}/{args.runs} — kill + warmup...")
                kill_instances()
                run_locust(args.host, NB_CONCURRENT_USERS, 20,
                           os.path.join(tmpdir, f"warmup_f{follows}_r{run}"))
                time.sleep(5)

                print(f"  Mesure run {run}/{args.runs}...")
                stats = run_locust(args.host, NB_CONCURRENT_USERS, args.run_time,
                                   os.path.join(tmpdir, f"fanout{follows}_r{run}"))
                nb_inst = get_instance_count()
                avg_str = f"{stats['avg_ms']:.0f}ms" if stats['avg_ms'] >= 0 else "N/A"
                print(f"    AVG={avg_str}  FAILED={stats['failed']}  INSTANCES={nb_inst}")

                rows.append({
                    "PARAM":        follows,
                    "AVG_TIME":     round(stats['avg_ms']) if stats['avg_ms'] >= 0 else -1,
                    "RUN":          run,
                    "FAILED":       stats['failed'],
                    "NB_INSTANCES": nb_inst,
                })

    with open(OUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResultats sauvegardes : {OUT_FILE}")
    print(open(OUT_FILE).read())


if __name__ == "__main__":
    main()
