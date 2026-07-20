"""Cold-snap stress test — the headline chart."""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stress as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
CAP = 200

def days_to_bind():
    m = S.matrix()
    order = sorted(m, key=lambda c: (m[c][1.0] is None, m[c][1.0] or CAP))
    fig, ax = plt.subplots(figsize=(9.5, 6.4))
    w = 0.26
    cols = {1.0: "#2980b9", 1.2: "#e67e22", 1.4: "#c0392b"}
    for k, sev in enumerate(S.SEVERITIES):
        ys = [i + (k - 1) * w for i in range(len(order))]
        xs = [(m[c][sev] if m[c][sev] else CAP) for c in order]
        ax.barh(ys, xs, height=w, color=cols[sev], label="%.1fx worst day" % sev)
        for y, c in zip(ys, order):
            if m[c][sev] == 1:
                ax.text(2, y, "rate-bound", va="center", fontsize=6.5, color="white",
                        fontweight="bold")
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order)
    ax.set_xlabel("Days of sustained cold before flexibility binds  (bar at 200 = holds)")
    ax.set_title("Cold-snap stress test — how long each country holds, and what fails first\n"
                 "day 1 = rate-bound (no delivery capacity); later = volume-bound (inventory empties)",
                 fontsize=11)
    ax.axvline(30, color="#333", ls="--", lw=1)
    ax.text(31, len(order) - .5, "one month", fontsize=7.5)
    ax.legend(fontsize=8, loc="lower right"); ax.grid(axis="x", alpha=.25); ax.set_xlim(0, CAP)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "stress_days.png"), dpi=150); plt.close(fig)

if __name__ == "__main__":
    days_to_bind(); print("wrote results/stress_days.png")
