"""Charts for the AGSI+ storage layer."""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agsi, storage_fleet as SF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
MON = ["Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep"]

def fill_curves():
    m = agsi.snapshot()["monthly_fill_eu"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for gy, vals in m.items():
        latest = gy == "2025/26"
        xs = [i for i, v in enumerate(vals) if v is not None]
        ys = [vals[i] for i in xs]
        ax.plot(xs, ys, lw=3 if latest else 1.4, color="#c0392b" if latest else "#95a5a6",
                alpha=1 if latest else .75, zorder=5 if latest else 2, label=gy)
        if latest:
            ax.scatter(xs, ys, s=26, color="#c0392b", zorder=6)
    ax.set_xticks(range(12)); ax.set_xticklabels(MON)
    ax.set_ylabel("EU storage fill, %")
    ax.set_title("EU gas storage through the gas year — 2025/26 in red\nGIE AGSI+, monthly means", fontsize=11)
    ax.axhline(90, color="#2980b9", ls="--", lw=1)
    ax.text(0.1, 91, "90% EU refill target", fontsize=7.5, color="#2980b9")
    ax.legend(fontsize=7.5, ncol=4); ax.grid(alpha=.25); ax.set_ylim(0, 105)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "storage_fill_curves.png"), dpi=150); plt.close(fig)

def deliverability():
    rows = SF.deliverability_pressure()
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    rows = rows[::-1]
    cols = ["#c0392b" if r["peak_utilisation_pct"] >= 85 else
            "#e67e22" if r["peak_utilisation_pct"] >= 70 else "#2980b9" for r in rows]
    ax.barh([r["code"] for r in rows], [r["peak_utilisation_pct"] for r in rows], color=cols)
    for i, r in enumerate(rows):
        ax.text(r["peak_utilisation_pct"] + 1.5, i,
                "%.2f of %.2f TWh/d · min fill %d%%"
                % (r["peak_withdrawal_twh_d"], r["withdrawal_capacity_twh_d"], r["min_fill"]),
                va="center", fontsize=7)
    ax.axvline(100, color="#333", ls="--", lw=1)
    ax.set_xlabel("Peak day withdrawal as % of the country's own withdrawal capacity, winter 2025/26")
    ax.set_title("Who ran out of delivery rate, not out of gas", fontsize=11)
    ax.set_xlim(0, 155); ax.grid(axis="x", alpha=.25)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "storage_deliverability.png"), dpi=150); plt.close(fig)

def german_sites(n=16):
    fac = sorted(agsi.facilities_de()["facilities"], key=lambda f: f["working_gas_volume"])[-n:]
    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    cmap = plt.get_cmap("RdYlBu")
    cols = [cmap(f["full"] / 100) for f in fac]
    ax.barh([f["facility"][:42] for f in fac], [f["working_gas_volume"] for f in fac],
            color=cols, edgecolor="#666", linewidth=.5)
    for i, f in enumerate(fac):
        ax.text(f["working_gas_volume"] + .4, i, "%.1f TWh · %.0f%% full · %d GWh/d out"
                % (f["working_gas_volume"], f["full"], f["withdrawal_capacity"]),
                va="center", fontsize=7)
    ax.set_xlabel("Working gas volume, TWh")
    ax.set_title("Germany's biggest storage sites, gas day 2026-07-18\n"
                 "colour = how full (blue full, red empty) — GIE AGSI+ facility level", fontsize=11)
    ax.set_xlim(0, 52); ax.grid(axis="x", alpha=.25)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "de_storage_sites.png"), dpi=150); plt.close(fig)

if __name__ == "__main__":
    fill_curves(); deliverability(); german_sites()
    print("wrote results/storage_fill_curves.png, storage_deliverability.png, de_storage_sites.png")
