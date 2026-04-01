from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = ROOT / "outputs" / "tables" / "lp_results_cpi_2016_Q1_lags2.csv"
FIGURES_DIR = ROOT / "outputs" / "figures"

C_PRE = "#3B82C4"
C_CHG = "#D85A30"
C_PST = "#1D9E75"


def load_results(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")
    df = pd.read_csv(path)
    for prefix, col_b, col_se in [
        ("pre", "beta_pre", "beta_pre_se"),
        ("chg", "beta_change", "beta_change_se"),
    ]:
        df[f"{prefix}_lo90"] = df[col_b] - 1.645 * df[col_se]
        df[f"{prefix}_hi90"] = df[col_b] + 1.645 * df[col_se]
        df[f"{prefix}_lo95"] = df[col_b] - 1.96 * df[col_se]
        df[f"{prefix}_hi95"] = df[col_b] + 1.96 * df[col_se]

    df["post_se"] = np.sqrt(df["beta_pre_se"] ** 2 + df["beta_change_se"] ** 2)
    df["post_lo90"] = df["beta_post"] - 1.645 * df["post_se"]
    df["post_hi90"] = df["beta_post"] + 1.645 * df["post_se"]
    df["post_lo95"] = df["beta_post"] - 1.96 * df["post_se"]
    df["post_hi95"] = df["beta_post"] + 1.96 * df["post_se"]
    return df


def _style_ax(ax: plt.Axes, title: str, ylabel: str | None = None) -> None:
    ax.set_title(title, fontsize=10, fontweight="500", pad=8)
    ax.set_xlabel("Horizon (quarters)", fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)
    ax.axhline(0, color="#999", linewidth=0.8, linestyle="--", zorder=1)
    ax.set_xticks(range(9))
    ax.tick_params(labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#ccc")
    ax.spines["bottom"].set_color("#ccc")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.3f"))


def _plot_band(
    ax: plt.Axes,
    h: np.ndarray,
    coef: pd.Series,
    lo90: pd.Series,
    hi90: pd.Series,
    lo95: pd.Series,
    hi95: pd.Series,
    color: str,
    marker: str = "o",
    label: str = "",
) -> None:
    ax.fill_between(h, lo95, hi95, alpha=0.10, color=color, zorder=2)
    ax.fill_between(h, lo90, hi90, alpha=0.20, color=color, zorder=3)
    ax.plot(
        h,
        coef,
        color=color,
        linewidth=2,
        marker=marker,
        markersize=5,
        markerfacecolor="white",
        markeredgecolor=color,
        markeredgewidth=1.8,
        label=label,
        zorder=4,
    )


def plot_three_panels(df: pd.DataFrame, figures_dir: Path) -> None:
    h = df["horizon"].values
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    fig.patch.set_facecolor("white")

    _plot_band(
        axes[0],
        h,
        df["beta_pre"],
        df["pre_lo90"],
        df["pre_hi90"],
        df["pre_lo95"],
        df["pre_hi95"],
        C_PRE,
    )
    _style_ax(axes[0], "Pre-liberalization effect (beta_0)", "CPI response to 1% Brent shock")

    _plot_band(
        axes[1],
        h,
        df["beta_change"],
        df["chg_lo90"],
        df["chg_hi90"],
        df["chg_lo95"],
        df["chg_hi95"],
        C_CHG,
    )
    for _, row in df[df["beta_change_pvalue"] < 0.05].iterrows():
        axes[1].text(
            row["horizon"],
            row["chg_hi90"] + 0.001,
            "**",
            ha="center",
            fontsize=8,
            color=C_CHG,
            fontweight="bold",
        )
    _style_ax(axes[1], "Amplification post-reform (delta)")

    _plot_band(
        axes[2],
        h,
        df["beta_post"],
        df["post_lo90"],
        df["post_hi90"],
        df["post_lo95"],
        df["post_hi95"],
        C_PST,
    )
    _style_ax(axes[2], "Post-liberalization effect (beta_0 + delta)")

    legend_els = [
        Patch(facecolor="#888", alpha=0.35, label="90% CI"),
        Patch(facecolor="#888", alpha=0.15, label="95% CI"),
    ]
    fig.legend(
        handles=legend_els,
        loc="lower center",
        ncol=2,
        fontsize=9,
        frameon=False,
        bbox_to_anchor=(0.5, -0.04),
    )

    fig.text(
        0.5,
        -0.09,
        "Local Projections (Jorda 2005). Break: 2016Q1. "
        "Controls: IGREA, fiscal proxy, COVID dummy. "
        "SE: HAC Newey-West (maxlags=h+1). N=61-69 obs.",
        ha="center",
        fontsize=7.5,
        color="#777",
    )
    fig.suptitle(
        "Oil Price Pass-Through to Moroccan CPI: Pre vs Post Subsidy Liberalization",
        fontsize=11.5,
        fontweight="500",
        y=1.02,
    )

    plt.tight_layout(pad=1.5)
    for ext in ("pdf", "png"):
        out = figures_dir / f"lp_irf_cpi_main.{ext}"
        plt.savefig(out, bbox_inches="tight", dpi=300, facecolor="white")
        print(f"  saved {out.name}")
    plt.close()


def plot_overlay(df: pd.DataFrame, figures_dir: Path) -> None:
    h = df["horizon"].values
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    fig.patch.set_facecolor("white")

    _plot_band(
        ax,
        h,
        df["beta_pre"],
        df["pre_lo90"],
        df["pre_hi90"],
        df["pre_lo95"],
        df["pre_hi95"],
        C_PRE,
        marker="o",
        label="Pre-reform effect (beta_0)",
    )
    _plot_band(
        ax,
        h,
        df["beta_change"],
        df["chg_lo90"],
        df["chg_hi90"],
        df["chg_lo95"],
        df["chg_hi95"],
        C_CHG,
        marker="s",
        label="Amplification post-reform (delta)",
    )

    for _, row in df[df["beta_change_pvalue"] < 0.05].iterrows():
        ax.text(
            row["horizon"],
            row["chg_hi90"] + 0.0015,
            "**",
            ha="center",
            va="bottom",
            fontsize=8.5,
            color=C_CHG,
            fontweight="bold",
        )

    peak = df.loc[df["horizon"] == 6, "beta_change"].values[0]
    ax.annotate(
        f"delta = +{peak:.3f}***\n(p < 0.001)",
        xy=(6, peak),
        xytext=(6.3, 0.022),
        fontsize=8.5,
        color=C_CHG,
        arrowprops=dict(
            arrowstyle="->",
            color=C_CHG,
            lw=1.2,
            connectionstyle="arc3,rad=-0.2",
        ),
    )

    ax.axhline(0, color="#999", linewidth=0.8, linestyle="--", zorder=1)
    ax.set_xlabel("Horizon (quarters)", fontsize=9.5)
    ax.set_ylabel("Cumulative CPI response to 1% Brent shock", fontsize=9.5)
    ax.set_title(
        "Oil Pass-Through to Moroccan CPI\nPre- vs Post-Subsidy Liberalization (Break: 2016Q1)",
        fontsize=10.5,
        fontweight="500",
    )
    ax.set_xticks(h)
    ax.tick_params(labelsize=9)
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#ccc")
    ax.spines["bottom"].set_color("#ccc")

    fig.text(
        0.5,
        -0.04,
        "HAC Newey-West SE (maxlags=h+1). Controls: IGREA, fiscal proxy, COVID dummy. "
        "Shaded: 90%/95% CI. ** p<0.05.",
        ha="center",
        fontsize=7.5,
        color="#777",
    )

    plt.tight_layout()
    for ext in ("pdf", "png"):
        out = figures_dir / f"lp_irf_cpi_overlay.{ext}"
        plt.savefig(out, bbox_inches="tight", dpi=300, facecolor="white")
        print(f"  saved {out.name}")
    plt.close()


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df = load_results(RESULTS_PATH)
    print("Generating figures...")
    plot_three_panels(df, FIGURES_DIR)
    plot_overlay(df, FIGURES_DIR)
    print("Done.")


if __name__ == "__main__":
    main()
