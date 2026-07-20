"""Schematic map of Germany's gas border points, coloured by how hard they are running."""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entsog, network as N

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
OFFSET = {"Emden (EPT1)": (-34, -30), "Dornum / NETRA": (10, 12),
          "Uberackern ABG": (-40, -22), "VIP Oberkappel": (10, 4)}
COL = {"above firm — running on non-firm capacity": "#c0392b",
       "no firm capacity published": "#e67e22",
       "at the firm limit": "#f1c40f",
       "spare firm capacity": "#2980b9",
       "idle": "#95a5a6"}

def draw():
    snap = entsog.snapshot()
    fig, ax = plt.subplots(figsize=(9.5, 8))

    # unmetered topology points: the rest of the border, for context
    for p in snap["topology"]:
        ax.scatter(p["x"], p["y"], s=26, facecolor="none", edgecolor="#b0b0b0",
                   linewidth=.9, zorder=2)
        ax.annotate(p["label"], (p["x"], p["y"]), fontsize=6, color="#909090",
                    xytext=(4, -7), textcoords="offset points")

    for p in snap["points"]:
        st = N.classify(p)
        flow = p["physical_flow"] / 1e6
        ax.scatter(p["x"], p["y"], s=40 + flow * 1.1, color=COL[st], alpha=.85,
                   edgecolor="white", linewidth=1.2, zorder=4)
        u = N.utilisation(p)
        lab = "%s\n%.0f GWh/d%s" % (p["label"], flow,
                                    ("  ·  %.0f%% of firm" % (u * 100)) if u else "")
        ax.annotate(lab, (p["x"], p["y"]), fontsize=8, fontweight="bold",
                    xytext=OFFSET.get(p["label"], (9, 6)),
                    textcoords="offset points", zorder=5)
        ax.annotate("", xy=(p["x"], p["y"]),
                    xytext=(p["x"] - (7 if p["direction"] == "entry" else -7), p["y"]),
                    arrowprops=dict(arrowstyle="-|>", color=COL[st], lw=1.6, alpha=.8), zorder=3)

    ax.set_title("Germany's gas border on the peak winter gas day %s\n"
                 "ENTSOG Transparency Platform — physical flow vs firm technical capacity"
                 % snap["_gas_day"], fontsize=11)
    ax.set_xlabel("← west          ENTSOG schematic map coordinates          east →", fontsize=8)
    ax.set_ylabel("← south                                      north →", fontsize=8)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=k, markersize=8)
               for k, c in COL.items()]
    ax.legend(handles=handles, fontsize=7.5, loc="lower left", title="status", title_fontsize=8)
    ax.grid(alpha=.2); ax.set_xlim(-52, 4); ax.set_ylim(-46, 16)
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
