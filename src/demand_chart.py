"""Charts for the demand-side split (who burns the gas)."""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demand as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
ORDER = ["Households", "Commercial & public services", "Power & heat generation", "Industry"]
COL = {"Households": "#c0392b", "Commercial & public services": "#e67e22",
       "Power & heat generation": "#2980b9", "Industry": "#7f8c8d"}
NAMES = {"DE":"Germany","IT":"Italy","TR":"Turkiye","FR":"France","ES":"Spain","NL":"Netherlands",
         "PL":"Poland","RO":"Romania","BE":"Belgium","HU":"Hungary","CZ":"Czechia","AT":"Austria"}

def sector_mix(countries=("DE","IT","TR","FR","ES","NL","PL","RO","BE","HU")):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = range(len(countries)); bottom = [0.0]*len(countries)
    for lab in ORDER:
        vals = [D.by_sector(c).get(lab, 0)/1000 for c in countries]
        ax.bar(x, vals, bottom=bottom, label=lab, color=COL[lab], edgecolor="white", linewidth=.6)
        bottom = [b+v for b, v in zip(bottom, vals)]
    ax.set_xticks(list(x)); ax.set_xticklabels([NAMES.get(c, c) for c in countries], rotation=30, ha="right")
    ax.set_ylabel("Natural gas, TWh (2024)")
    ax.set_title("Who burns the gas — sectoral split, Eurostat nrg_bal_c 2024")
    for i, c in enumerate(countries):
        ax.text(i, bottom[i]+8, "%.0f%% weather-\nexposed" % (D.weather_exposed_share(c)*100),
                ha="center", fontsize=7, color="#444")
    ax.set_ylim(0, max(bottom)*1.22)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(axis="y", alpha=.25)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "demand_by_sector.png"), dpi=150); plt.close(fig)

def de_industry():
    b = D.de_industry_branches()
    items = sorted(b.items(), key=lambda kv: kv[1])
    fig, ax = plt.subplots(figsize=(8.5, 4))
    ax.barh([k for k, _ in items], [v/1000 for _, v in items], color="#7f8c8d")
    for i, (k, v) in enumerate(items):
        ax.text(v/1000 + 1, i, "%.1f TWh" % (v/1000), va="center", fontsize=8)
    dc = D.DE_DATACENTRE_ELECTRICITY_TWH_2024
    ax.axvline(dc, color="#c0392b", ls="--", lw=1.2)
    ax.text(dc + 1, -0.75, "German data centres: %.0f TWh of *electricity* (2024)" % dc,
            color="#c0392b", fontsize=8)
    ax.set_xlabel("Natural gas, TWh (2024)")
    ax.set_title("Germany — industrial gas by branch, and data centres for scale")
    ax.set_xlim(0, 62); ax.grid(axis="x", alpha=.25)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "de_industry_gas.png"), dpi=150); plt.close(fig)

if __name__ == "__main__":
    sector_mix(); de_industry(); print("wrote results/demand_by_sector.png, results/de_industry_gas.png")
