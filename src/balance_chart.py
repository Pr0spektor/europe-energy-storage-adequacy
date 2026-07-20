"""Charts for the storage cycle: what fills the swing, and who has nothing to fill."""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import balance as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
M = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def eu_cycle_chart():
    v = [x/3600 for x in B.parse()["EU27_2020"]]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar(M, v, color=["#2980b9" if x > 0 else "#c0392b" for x in v], edgecolor="white")
    ax.axhline(0, color="#333", lw=.8)
    for i, x in enumerate(v):
        ax.text(i, x + (6 if x > 0 else -14), "%.0f" % x, ha="center", fontsize=7)
    ax.set_ylabel("Net stock change, TWh")
    ax.set_title("EU-27 gas storage cycle 2025 — blue = injection (refill), red = withdrawal\n"
                 "Eurostat nrg_cb_gasm, STK_CHG_MG", fontsize=10)
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "storage_cycle.png"), dpi=150); plt.close(fig)

def cover_chart(n=16):
    rows = [r for r in B.table() if r["storage_cover"] is not None][:n]
    rows = sorted(rows, key=lambda r: r["storage_cover"])
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    cols = ["#c0392b" if r["storage_cover"] < 0.9 else "#2980b9" for r in rows]
    ax.barh([r["country"] for r in rows], [r["storage_cover"]*100 for r in rows], color=cols)
    ax.axvline(100, color="#333", ls="--", lw=1)
    for i, r in enumerate(rows):
        ax.text(r["storage_cover"]*100 + 2, i, "swing %.0f TWh · peak %.0f GW"
                % (r["swing_twh"], r["peak_withdrawal_gw"]), va="center", fontsize=7)
    ax.set_xlabel("Storage withdrawal as % of the country's own seasonal swing (2025)")
    ax.set_title("Does domestic storage cover the seasonal swing?", fontsize=11)
    ax.set_xlim(0, 200); ax.grid(axis="x", alpha=.25)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "storage_cover.png"), dpi=150); plt.close(fig)

if __name__ == "__main__":
    eu_cycle_chart(); cover_chart()
    print("wrote results/storage_cycle.png, results/storage_cover.png")
