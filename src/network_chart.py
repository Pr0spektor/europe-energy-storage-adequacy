"""Schematic map of Germany's gas border points, coloured by how hard they are running."""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entsog, network as N

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
# label offset per point (in points), tuned so nothing overlaps and no leader line is needed
OFFSET = {
    "Dornum / NETRA":        (-12, -14),
    "Emden (EPT1)":          (14, -16),
    "Mallnow":               (12, 6),
    "GCP GAZ-SYSTEM/ONTRAS": (12, 4),
    "VIP Brandov":           (12, 6),
    "VIP Waidhaus":          (12, 6),
    "VIP Oberkappel":        (12, 4),
    "Uberackern ABG":        (-12, 6),
    "Uberackern SUDAL":      (-12, -16),
    "VIP Germany-CH":        (12, 4),
}

COL = {"above firm — running on non-firm capacity": "#c0392b",
       "no firm capacity published": "#e67e22",
       "at the firm limit": "#f1c40f",
       "spare firm capacity": "#2980b9",
       "idle": "#95a5a6"}

CROWD = 5.0   # schematic units within which points are treated as overlapping


def _declutter(ys, min_gap, lo, hi):
    """Spread label y-positions so none are closer than min_gap, staying within [lo,hi]."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    pos = list(ys)
    for k in range(1, len(order)):
        a, b = order[k - 1], order[k]
        if pos[b] - pos[a] < min_gap:
            pos[b] = pos[a] + min_gap
    # if we overran the top, push the whole stack down
    overflow = pos[order[-1]] - hi
    if overflow > 0:
        for i in order:
            pos[i] -= overflow
    return pos


def draw():
    snap = entsog.snapshot()
    fig, ax = plt.subplots(figsize=(10.5, 8))

    for p in snap["points"]:
        st = N.classify(p)
        flow = p["physical_flow"] / 1e6
        ax.scatter(p["x"], p["y"], s=55 + flow * 1.1, color=COL[st], alpha=.9,
                   edgecolor="white", linewidth=1.2, zorder=4)
        u = N.utilisation(p)
        if flow > 0:
            head = "%s  →%s\n%.0f GWh/d%s" % (p["label"], p["to"], flow,
                    ("  ·  %.0f%% of firm" % (u * 100)) if u else "  ·  no firm published")
        else:
            head = "%s  →%s\nidle — 0 GWh/d" % (p["label"], p["to"])
        dx, dy = OFFSET.get(p["label"], (12, 6))
        ha = "right" if dx < 0 else "left"
        ax.annotate(head, xy=(p["x"], p["y"]), xytext=(dx, dy),
                    textcoords="offset points", fontsize=7.5, fontweight="bold",
                    va="center", ha=ha,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8),
                    zorder=6)
        if flow > 0:
            ax.annotate("", xy=(p["x"], p["y"]),
                        xytext=(p["x"] - (7 if p["direction"] == "entry" else -7), p["y"]),
                        arrowprops=dict(arrowstyle="-|>", color=COL[st], lw=1.6, alpha=.8),
                        zorder=3)

    ax.set_title("Germany's gas border on the peak winter gas day %s\n"
                 "ENTSOG Transparency Platform — physical flow vs firm technical capacity "
                 "(every point verified)" % snap["_gas_day"], fontsize=11)
    ax.set_xlabel("← west          ENTSOG schematic map coordinates          east →", fontsize=8)
    ax.set_ylabel("← south                                      north →", fontsize=8)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=k, markersize=8)
               for k, c in COL.items()]
    ax.legend(handles=handles, fontsize=7.5, loc="center left", bbox_to_anchor=(0.02, 0.30),
              title="status", title_fontsize=8, framealpha=0.9)
    ax.grid(alpha=.2); ax.set_xlim(-56, 16); ax.set_ylim(-46, 16)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "network_map.png"), dpi=150); plt.close(fig)


def corridor_chart():
    c = N.corridors()
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ks = list(c)[::-1]
    ax.barh(ks, [c[k] for k in ks], color=["#2980b9" if "->DE" in k else "#7f8c8d" for k in ks])
    for i, k in enumerate(ks):
        ax.text(c[k] + 12, i, "%.0f GWh/d" % c[k], va="center", fontsize=8)
    ax.set_xlabel("Physical flow, GWh/d (gas day 2026-01-15)")
    ax.set_title("Germany's border corridors — imports in blue, transit out in grey", fontsize=10)
    ax.set_xlim(0, max(c.values()) * 1.25); ax.grid(axis="x", alpha=.25)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "network_corridors.png"), dpi=150); plt.close(fig)

if __name__ == "__main__":
    draw(); corridor_chart(); print("wrote results/network_map.png, results/network_corridors.png")
