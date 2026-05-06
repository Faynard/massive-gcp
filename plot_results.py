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
    print(f"  OK Graphique sauvegarde : {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    conc_csv = os.path.join(OUT_DIR, "conc.csv")
    if os.path.exists(conc_csv):
        print(f"\n[1/2] Lecture de {conc_csv} ...")
        make_barplot(
            data=load_csv(conc_csv),
            xlabel="Nombre d'utilisateurs simultanés",
            title="Temps moyen par requête selon la concurrence\n"
                  "(1000 users, 50 posts/user, 20 followers)",
            out_path=os.path.join(OUT_DIR, "conc.png"),
        )
    else:
        print(f"  Fichier introuvable : {conc_csv} — lancez d'abord bench_conc.py")

    fanout_csv = os.path.join(OUT_DIR, "fanout.csv")
    if os.path.exists(fanout_csv):
        print(f"\n[2/2] Lecture de {fanout_csv} ...")
        make_barplot(
            data=load_csv(fanout_csv),
            xlabel="Nombre de followees par utilisateur",
            title="Temps moyen par requête selon le fanout\n"
                  "(1000 users, 100 posts/user, 50 users simultanés)",
            out_path=os.path.join(OUT_DIR, "fanout.png"),
        )
    else:
        print(f"  Fichier introuvable : {fanout_csv} — lancez d'abord bench_fanout.py")

    conc_nw_csv = os.path.join(OUT_DIR, "conc_no_warmup.csv")
    if os.path.exists(conc_nw_csv) and os.path.exists(conc_csv):
        print(f"\n[3/3] Comparaison warmup vs no-warmup ...")
        nw_data = load_csv(conc_nw_csv)
        w_data  = load_csv(conc_csv)

        def sort_key(k):
            try: return float(k)
            except ValueError: return k

        labels  = sorted(set(nw_data) | set(w_data), key=sort_key)
        w_means  = [np.mean(w_data.get(l,  [0])) for l in labels]
        nw_means = [np.mean(nw_data.get(l, [0])) for l in labels]
        w_stds   = [np.std(w_data.get(l,   [0]), ddof=0) for l in labels]
        nw_stds  = [np.std(nw_data.get(l,  [0]), ddof=0) for l in labels]

        x     = np.arange(len(labels))
        width = 0.38
        fig, ax = plt.subplots(figsize=(11, 5))

        ax.bar(x - width/2, w_means,  width, yerr=w_stds,  capsize=5,
               label="Avec warmup",  color="#4C8FBF", edgecolor="#2a5980",
               linewidth=0.8, error_kw={"elinewidth": 1.2, "ecolor": "#1a3a55"})
        ax.bar(x + width/2, nw_means, width, yerr=nw_stds, capsize=5,
               label="Sans warmup",  color="#E07B4F", edgecolor="#8B3E1A",
               linewidth=0.8, error_kw={"elinewidth": 1.2, "ecolor": "#5a2000"})

        for i, (wm, nwm, ws, nws) in enumerate(zip(w_means, nw_means, w_stds, nw_stds)):
            top = max(wm + ws, nwm + nws)
            if wm  > 0: ax.text(x[i] - width/2, wm  + ws  + top * 0.01, f"{wm:.0f}",
                                ha="center", va="bottom", fontsize=8, color="#2a5980")
            if nwm > 0: ax.text(x[i] + width/2, nwm + nws + top * 0.01, f"{nwm:.0f}",
                                ha="center", va="bottom", fontsize=8, color="#8B3E1A")

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=11)
        ax.set_xlabel("Nombre d'utilisateurs simultanes", fontsize=12)
        ax.set_ylabel("Temps moyen par requete (ms)", fontsize=12)
        ax.set_title("Impact du Cold Start : avec vs sans warmup\n"
                     "(1000 users, 50 posts/user, 20 followers)",
                     fontsize=13, fontweight="bold", pad=14)
        ax.set_ylim(0, max(max(nw_means), max(w_means)) * 1.35 + 200)
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)
        ax.legend(fontsize=11)

        plt.tight_layout()
        out = os.path.join(OUT_DIR, "conc_comparison.png")
        plt.savefig(out, dpi=150)
        plt.close()
        print(f"  OK Graphique sauvegarde : {out}")

    print("\nTermine.")


if __name__ == "__main__":
    main()
