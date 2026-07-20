"""Charts for the LNG regasification layer."""
import os, sys, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
DATA_FILE = os.path.join(ROOT, "data", "raw", "alsi_2026-07-18.json")

def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)

def terminal_map():
    data = load_data()
    rows = [r for r in data["terminals_by_country"] if r["send_out_gwh_d"] is not None]
    rows = sorted(rows, key=lambda r: r["send_out_gwh_d"])

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh([r["code"] for r in rows], [r["send_out_gwh_d"] for r in rows], color="#2980b9")

    max_val = max(r["send_out_gwh_d"] for r in rows)
    x_limit = max_val * 1.25

    for i, r in enumerate(rows):
        ax.text(r["send_out_gwh_d"] + max_val * 0.02, i,
                "%d terminals" % r["terminals"],
                va="center", fontsize=7)

    ax.set_xlabel("Send-out, GWh/d")
    ax.set_title("European LNG regasification send-out by country, gas day 2026-07-18", fontsize=11)
    ax.set_xlim(0, x_limit)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "lng_terminals.png"), dpi=150)
    plt.close(fig)

def winter_peaks():
    data = load_data()
    rows = sorted(data["winter_2025_26"], key=lambda r: r["peak_send_out_twh_d"])

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh([r["code"] for r in rows], [r["peak_send_out_twh_d"] for r in rows], color="#16a085")

    max_val = max(r["peak_send_out_twh_d"] for r in rows)
    x_limit = max_val * 1.25

    for i, r in enumerate(rows):
        ax.text(r["peak_send_out_twh_d"] + max_val * 0.02, i,
                "%.1f TWh over the winter" % r["winter_total_twh"],
                va="center", fontsize=7)

    ax.set_xlabel("Peak send-out, TWh/d")
    ax.set_title("Peak LNG send-out, winter 2025/26", fontsize=11)
    ax.set_xlim(0, x_limit)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "lng_winter_peaks.png"), dpi=150)
    plt.close(fig)


def flexibility_split():
    """Where each country's peak-day flexibility came from — caverns or ships."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import lng as L
    rows = L.flexibility_table()[::-1]
    fig, ax = plt.subplots(figsize=(8.5, 5))
    codes = [r["code"] for r in rows]
    st = [r["storage_twh_d"] for r in rows]
    ln = [r["lng_twh_d"] for r in rows]
    ax.barh(codes, st, color="#2980b9", label="storage withdrawal")
    ax.barh(codes, ln, left=st, color="#16a085", label="LNG send-out")
    for i, r in enumerate(rows):
        ax.text(r["total_twh_d"] + 0.05, i, "%.0f%% from ships" % (r["lng_share"] * 100),
                va="center", fontsize=8)
    ax.set_xlabel("Peak-day supply of flexibility, TWh/d (winter 2025/26)")
    ax.set_title("Caverns or ships — where the peak day actually came from\n"
                 "GIE AGSI+ and ALSI, peak day of winter 2025/26", fontsize=11)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_xlim(0, max(r["total_twh_d"] for r in rows) * 1.35)
    ax.grid(axis="x", alpha=.25)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "lng_vs_storage.png"), dpi=150)
    plt.close(fig)

if __name__ == "__main__":
    terminal_map()
    winter_peaks()
    flexibility_split()
    print("wrote results/lng_terminals.png, results/lng_winter_peaks.png, results/lng_vs_storage.png")
