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
    fig, ax = plt.subplots(figsize=(11, 8.5))

    # ---- unmetered interconnection points: hollow dots, every one labelled ----
    # ENTSOG's schematic coordinates pile same-corridor points on top of each other, so
    # labels are pulled out to a clear column on the side and joined with a leader line.
    topo = snap["topology"]
    for p in topo:
        ax.scatter(p["x"], p["y"], s=24, facecolor="none", edgecolor="#b0b0b0",
                   linewidth=.9, zorder=2)
    left = sorted([p for p in topo if p["x"] <= -25], key=lambda p: p["y"])
    right = sorted([p for p in topo if p["x"] > -25], key=lambda p: p["y"])
    ly = _declutter([p["y"] for p in left], 3.6, -46, 16)
    ry = _declutter([p["y"] for p in right], 3.6, -46, 16)
    for grp, ys, lx, ha in ((left, ly, -57.5, "right"), (right, ry, 4.5, "left")):
        for p, y in zip(grp, ys):
            ax.annotate(p["label"], xy=(p["x"], p["y"]), xytext=(lx, y),
                        fontsize=6.5, color="#7a7a7a", va="center", ha=ha,
                        arrowprops=dict(arrowstyle="-", lw=0.5, color="#c8c8c8",
                                        shrinkA=0, shrinkB=2))

    # ---- metered points: coloured, sized by flow, with the flow arrow ----
    for p in snap["points"]:
        st = N.classify(p)
        flow = p["physical_flow"] / 1e6
        ax.scatter(p["x"], p["y"], s=45 + flow * 1.1, color=COL[st], alpha=.9,
                   edgecolor="white", linewidth=1.2, zorder=4)
        u = N.utilisation(p)
        if flow > 0:
            lab = "%s\n%.0f GWh/d%s" % (p["label"], flow,
                                        ("  ·  %.0f%% of firm" % (u * 100)) if u else "")
        else:
            lab = "%s\nidle — 0 GWh/d" % p["label"]     # do not imply a flow it does not carry
        ax.annotate(lab, (p["x"], p["y"]), fontsize=8, fontweight="bold",
                    xytext=OFFSET.get(p["label"], (9, 6)),
                    textcoords="offset points", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
        # flow arrow only where gas actually moves
        if flow > 0:
            ax.annotate("", xy=(p["x"], p["y"]),
                        xytext=(p["x"] - (7 if p["direction"] == "entry" else -7), p["y"]),
                        arrowprops=dict(arrowstyle="-|>", color=COL[st], lw=1.6, alpha=.8),
                        zorder=3)

    ax.set_title("Germany's gas border on the peak winter gas day %s\n"
                 "ENTSOG Transparency Platform — physical flow vs firm technical capacity"
                 % snap["_gas_day"], fontsize=11)
    ax.set_xlabel("← west          ENTSOG schematic map coordinates          east →", fontsize=8)
    ax.set_ylabel("← south                                      north →", fontsize=8)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=k, markersize=8)
               for k, c in COL.items()]
    handles.append(plt.Line2D([], [], marker="o", ls="", mfc="none", mec="#b0b0b0",
                              label="other point (no metered flow)", markersize=8))
    ax.legend(handles=handles, fontsize=7.5, loc="center left", bbox_to_anchor=(0.30, 0.60),
              title="status", title_fontsize=8, framealpha=0.9)
    ax.grid(alpha=.2); ax.set_xlim(-62, 12); ax.set_ylim(-46, 18)
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
