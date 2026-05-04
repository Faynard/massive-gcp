import os
import csv
import re
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # Mode non-interactif (pas besoin d'écran)
import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = "out"


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_ms(value: str) -> float:
    """Convertit '123.4ms' ou '123.4' en float (ms). Retourne -1 si invalide."""
    if not value or value.strip().upper() == "N/A":
        return -1.0
    cleaned = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return -1.0


def load_csv(filepath: str) -> dict[str, list[float]]:
    """
    Charge un CSV de benchmark et retourne un dict :
      { param_value -> [avg_ms_run1, avg_ms_run2, avg_ms_run3] }
    Les valeurs -1 (erreurs) sont exclues.
    """
    data = defaultdict(list)
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            param = str(row["PARAM"]).strip()
            avg_ms = parse_ms(row.get("AVG_TIME", "-1"))
            if avg_ms >= 0:
                data[param].append(avg_ms)
    return dict(data)


def make_barplot(data: dict, xlabel: str, title: str, out_path: str):
    """
    Génère un barplot avec barres d'erreur (std des 3 runs).

    - data : { label -> [val_run1, val_run2, val_run3] }
    - Barre d'erreur = écart-type des runs
    """
    # Tri des clés (conversion numérique si possible)
    def sort_key(k):
        try:
            return float(k)
        except ValueError:
            return k

    labels = sorted(data.keys(), key=sort_key)
    means = []
    stds = []
    for label in labels:
        vals = data[label]
        means.append(np.mean(vals))
        stds.append(np.std(vals, ddof=0))

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9, 5))

    bars = ax.bar(
        x, means,
        yerr=stds,
        capsize=6,
        color="#4C8FBF",
        edgecolor="#2a5980",
        linewidth=0.8,
        error_kw={"elinewidth": 1.5, "ecolor": "#1a3a55"},
    )

    # Valeurs au-dessus des barres
    for bar, mean, std in zip(bars, means, stds):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + std + max(means) * 0.01,
            f"{mean:.0f}ms",
            ha="center", va="bottom",
            fontsize=9, fontweight="bold", color="#1a3a55"
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel("Temps moyen par requête (ms)", fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
    ax.set_ylim(0, max(means) * 1.3 + max(stds) * 1.5 + 10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  ✓ Graphique sauvegardé : {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── conc.png ──────────────────────────────────────────────────────────────
    conc_csv = os.path.join(OUT_DIR, "conc.csv")
    if os.path.exists(conc_csv):
        print(f"\n[1/2] Lecture de {conc_csv} ...")
        conc_data = load_csv(conc_csv)
        make_barplot(
            data=conc_data,
            xlabel="Nombre d'utilisateurs simultanés",
            title="Temps moyen par requête selon la concurrence\n"
                  "(1000 users, 50 posts/user, 20 followers)",
            out_path=os.path.join(OUT_DIR, "conc.png"),
        )
    else:
        print(f"  Fichier introuvable : {conc_csv} — lancez d'abord bench_conc.py")

    # ── fanout.png ────────────────────────────────────────────────────────────
    fanout_csv = os.path.join(OUT_DIR, "fanout.csv")
    if os.path.exists(fanout_csv):
        print(f"\n[2/2] Lecture de {fanout_csv} ...")
        fanout_data = load_csv(fanout_csv)
        make_barplot(
            data=fanout_data,
            xlabel="Nombre de followees par utilisateur",
            title="Temps moyen par requête selon le fanout\n"
                  "(1000 users, 100 posts/user, 50 users simultanés)",
            out_path=os.path.join(OUT_DIR, "fanout.png"),
        )
    else:
        print(f"  Fichier introuvable : {fanout_csv} — lancez d'abord bench_fanout.py")

    print("\nTerminé.")


if __name__ == "__main__":
    main()
