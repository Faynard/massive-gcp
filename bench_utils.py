"""Utilitaires partagés entre bench_conc.py et bench_fanout.py."""
import csv
import os
import subprocess
import time

PROJECT     = "tp1cloud-489814"
GCLOUD_PATH = r"C:\Users\thay\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
PYTHON_PATH = r"C:\Users\thay\AppData\Local\Google\Cloud SDK\google-cloud-sdk\platform\bundledpython\python.exe"


def get_instance_count() -> int:
    """Retourne le nombre d'instances App Engine actives."""
    try:
        r = subprocess.run(
            [GCLOUD_PATH, "app", "instances", "list", f"--project={PROJECT}"],
            capture_output=True, text=True, timeout=30
        )
        return sum(1 for l in r.stdout.splitlines()
                   if l.strip() and not l.upper().startswith("SERVICE"))
    except Exception as e:
        print(f"  [instances] Erreur : {e}")
        return -1


def kill_instances():
    """Supprime toutes les instances App Engine et attend 15 s."""
    try:
        r = subprocess.run(
            [GCLOUD_PATH, "app", "instances", "list",
             "--format=csv[no-heading](service,version,id)",
             f"--project={PROJECT}"],
            capture_output=True, text=True, timeout=30
        )
        lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except Exception as e:
        print(f"  [kill] Erreur listing : {e}")
        return

    if not lines:
        print("  [kill] Aucune instance a supprimer.")
        return

    deleted = 0
    for line in lines:
        parts = line.split(",")
        if len(parts) < 3:
            continue
        s, v, i = parts[0].strip(), parts[1].strip(), parts[2].strip()
        try:
            subprocess.run(
                [GCLOUD_PATH, "app", "instances", "delete", i,
                 "-s", s, "-v", v, f"--project={PROJECT}", "-q"],
                capture_output=True, timeout=30
            )
            deleted += 1
        except Exception as e:
            print(f"  [kill] Erreur instance {i[:12]} : {e}")

    print(f"  [kill] {deleted}/{len(lines)} instance(s) supprimee(s). Attente 15s...")
    time.sleep(15)


def run_locust(host: str, nb_users: int, run_time: int, csv_prefix: str) -> dict:
    """Lance Locust en mode headless et retourne avg_ms + failed."""
    cmd = [
        PYTHON_PATH, "-m", "locust",
        "-f", "locustfile.py",
        "--headless",
        "-u", str(nb_users),
        "-r", str(min(nb_users, 100)),
        "--run-time", f"{run_time}s",
        "--host", host,
        "--csv", csv_prefix,
        "--only-summary",
    ]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    print(f"    Lancement : {nb_users} users x {run_time}s ...")
    try:
        subprocess.run(cmd, env=env, timeout=run_time + 60, check=True)
    except subprocess.CalledProcessError as e:
        print(f"    Locust code {e.returncode}")
    except subprocess.TimeoutExpired:
        print("    Timeout Locust")

    avg_ms, failed = -1.0, 0
    stats_file = f"{csv_prefix}_stats.csv"
    if os.path.exists(stats_file):
        with open(stats_file, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("Name", "").strip().lower() == "aggregated":
                    try:
                        avg_ms = float(row.get("Average Response Time",
                                               row.get("Average Response Time (ms)", -1)))
                    except (ValueError, TypeError):
                        pass
                    try:
                        failed = int(row.get("Failure Count", 0))
                    except (ValueError, TypeError):
                        pass
                    break
    else:
        print(f"    Stats introuvable : {stats_file}")

    return {"avg_ms": avg_ms, "failed": failed}
