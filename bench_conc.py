import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
import time

# ── Configuration de l'expérience ─────────────────────────────────────────────
CONCURRENCY_LEVELS = [1, 10, 20, 50, 100, 1000]
NB_RUNS = 3
USER_PREFIX = "user"
NUM_USERS = 1000
OUT_DIR = "out"
OUT_FILE = os.path.join(OUT_DIR, "conc.csv")
CSV_HEADER = ["PARAM", "AVG_TIME", "RUN", "FAILED", "NB_INSTANCES"]


# ── Helpers ────────────────────────────────────────────────────────────────────

GCLOUD_PATH = r"C:\Users\thay\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

def get_instance_count() -> int:
    try:
        result = subprocess.run(
            [GCLOUD_PATH, "app", "instances", "list", "--format=value(id)",
             "--project=tp1cloud-489814"],
            capture_output=True, text=True, timeout=30
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return len(lines)
    except Exception as e:
        print(f"  Impossible de récupérer le nombre d'instances : {e}")
        return -1


def run_locust(host: str, nb_users: int, run_time: int, csv_prefix: str) -> dict:

    spawn_rate = min(nb_users, 100)  # max 100 users/s de spawn
    env = os.environ.copy()
    env["NUM_USERS"] = str(NUM_USERS)
    env["USER_PREFIX"] = USER_PREFIX

    cmd = [
        sys.executable, "-m", "locust",
        "-f", "locustfile.py",
        "--headless",
        "-u", str(nb_users),
        "-r", str(spawn_rate),
        "--run-time", f"{run_time}s",
        "--host", host,
        "--csv", csv_prefix,
        "--csv-full-history",
        "--only-summary",
    ]

    print(f"    Lancement : {nb_users} users × {run_time}s ...")
    try:
        subprocess.run(cmd, env=env, timeout=run_time + 60, check=True)
    except subprocess.CalledProcessError as e:
        print(f"    Locust a retourné le code {e.returncode}")
    except subprocess.TimeoutExpired:
        print("    Timeout Locust")

    # Lecture du CSV de stats généré par locust
    stats_file = f"{csv_prefix}_stats.csv"
    avg_ms = -1.0
    failed = 0

    if os.path.exists(stats_file):
        with open(stats_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Name", "").strip().lower() == "aggregated":
                    try:
                        avg_ms = float(row.get("Average Response Time", row.get("Average Response Time (ms)", -1)))
                    except (ValueError, TypeError):
                        avg_ms = -1.0
                    try:
                        failed = int(row.get("Failure Count", 0))
                    except (ValueError, TypeError):
                        failed = 0
                    break
    else:
        print(f"    Fichier stats introuvable : {stats_file}")

    return {"avg_ms": avg_ms, "failed": failed}


def seed_data(host: str, seed_token: str):
    """Appelle /admin/seed pour peupler le Datastore (1000 users, 50 posts/user, 20 follows)."""
    import urllib.request
    import urllib.error
    url = (
        f"{host.rstrip('/')}/admin/seed"
        f"?users={NUM_USERS}&posts={NUM_USERS * 50}&follows_min=20&follows_max=20&prefix={USER_PREFIX}"
    )
    print(f"\n  Seeding via {url} ...")
    req = urllib.request.Request(url, method="POST")
    req.add_header("X-Seed-Token", seed_token)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = resp.read().decode()
            print(f"  ✓ Seed OK : {body[:120]}")
    except urllib.error.HTTPError as e:
        print(f"  ✗ Seed HTTP {e.code} : {e.read().decode()[:120]}")
    except Exception as e:
        print(f"  ✗ Seed erreur : {e}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Benchmark concurrence TinyInsta")
    parser.add_argument("--host", required=True, help="URL de l'app (ex: https://app.appspot.com)")
    parser.add_argument("--skip-seed", action="store_true", help="Ne pas re-seeder les données")
    parser.add_argument("--seed-token", default="change-me-seed-token", help="Token pour /admin/seed")
    parser.add_argument("--run-time", type=int, default=30, help="Durée de chaque run Locust (secondes)")
    parser.add_argument("--runs", type=int, default=NB_RUNS, help="Nombre de répétitions par niveau")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    # ── Seeding ────────────────────────────────────────────────────────────────
    if not args.skip_seed:
        seed_data(args.host, args.seed_token)
        print("  Attente 10s pour que Datastore indexe les données...")
        time.sleep(10)
    else:
        print("  [skip-seed] Seeding ignoré.")

    # ── Benchmark ─────────────────────────────────────────────────────────────
    rows = []
    print("\n" + "=" * 60)
    print("  EXPÉRIENCE : Passage à l'échelle sur la concurrence")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        for nb_users in CONCURRENCY_LEVELS:
            print(f"\n▶ Concurrence = {nb_users} utilisateur(s) simultané(s)")
            for run in range(1, args.runs + 1):
                print(f"  Run {run}/{args.runs}")
                csv_prefix = os.path.join(tmpdir, f"locust_conc{nb_users}_run{run}")
                stats = run_locust(args.host, nb_users, args.run_time, csv_prefix)
                nb_instances = get_instance_count()

                avg_display = f"{stats['avg_ms']:.0f}ms" if stats['avg_ms'] >= 0 else "N/A"
                print(f"    → AVG={avg_display}  FAILED={stats['failed']}  INSTANCES={nb_instances}")

                rows.append({
                    "PARAM": nb_users,
                    "AVG_TIME": f"{stats['avg_ms']:.1f}ms" if stats['avg_ms'] >= 0 else "N/A",
                    "RUN": run,
                    "FAILED": stats['failed'],
                    "NB_INSTANCES": nb_instances,
                })

                # Pause entre les runs pour laisser les instances se stabiliser
                if run < args.runs:
                    time.sleep(5)

            # Pause plus longue entre les niveaux de concurrence
            time.sleep(10)

    # ── Écriture CSV ──────────────────────────────────────────────────────────
    with open(OUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Résultats sauvegardés dans : {OUT_FILE}")
    print("\nAperçu :")
    with open(OUT_FILE) as f:
        print(f.read())


if __name__ == "__main__":
    main()
