"""Expérience 1 — Passage à l'échelle en concurrence.

Usage :
  $env:GCLOUD_TOKEN = (gcloud auth print-access-token)
  python bench_conc.py --host https://tp1cloud-489814.ew.r.appspot.com
"""
import argparse
import csv
import os
import tempfile
import time

from bench_utils import get_instance_count, kill_instances, run_locust

CONCURRENCY_LEVELS = [1, 10, 20, 50, 100, 1000]
NB_RUNS    = 3
OUT_FILE   = os.path.join("out", "conc.csv")
CSV_HEADER = ["PARAM", "AVG_TIME", "RUN", "FAILED", "NB_INSTANCES"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--run-time", type=int, default=30)
    parser.add_argument("--runs",     type=int, default=NB_RUNS)
    args = parser.parse_args()

    os.makedirs("out", exist_ok=True)
    rows = []

    print("\n" + "=" * 60)
    print("  EXPERIENCE : Passage a l'echelle sur la concurrence")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        for nb_users in CONCURRENCY_LEVELS:
            print(f"\n>> Concurrence = {nb_users} user(s)")
            kill_instances()

            for run in range(1, args.runs + 1):
                print(f"  Run {run}/{args.runs}")
                stats = run_locust(args.host, nb_users, args.run_time,
                                   os.path.join(tmpdir, f"conc{nb_users}_r{run}"))
                nb_inst = get_instance_count()
                avg_str = f"{stats['avg_ms']:.0f}ms" if stats['avg_ms'] >= 0 else "N/A"
                print(f"    AVG={avg_str}  FAILED={stats['failed']}  INSTANCES={nb_inst}")

                rows.append({
                    "PARAM":        nb_users,
                    "AVG_TIME":     round(stats['avg_ms']) if stats['avg_ms'] >= 0 else -1,
                    "RUN":          run,
                    "FAILED":       stats['failed'],
                    "NB_INSTANCES": nb_inst,
                })
                if run < args.runs:
                    time.sleep(5)

    with open(OUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResultats sauvegardes : {OUT_FILE}")
    print(open(OUT_FILE).read())


if __name__ == "__main__":
    main()
