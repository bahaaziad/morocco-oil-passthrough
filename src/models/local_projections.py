from pathlib import Path
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "master_quarterly_no_fx.csv"
OUTPUT_DIR = ROOT / "outputs" / "tables"

BREAK_QUARTERS = ["2013Q3", "2014Q1", "2015Q1", "2016Q1"]  # baseline inclus
N_LAGS = 2
MAX_HORIZON = 8


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Fichier introuvable: {DATA_PATH}")
    return pd.read_csv(DATA_PATH)


def add_regime_variables(df: pd.DataFrame, break_quarter: str) -> pd.DataFrame:
    df = df.copy()
    df["quarter_period"] = pd.PeriodIndex(df["quarter"], freq="Q")
    break_period = pd.Period(break_quarter, freq="Q")
    df["D_lib_model"] = (df["quarter_period"] >= break_period).astype(int)
    df["oil_x_Dlib_model"] = df["oil_log_diff"] * df["D_lib_model"]
    return df


def add_lags(df: pd.DataFrame, col: str, n_lags: int) -> pd.DataFrame:
    df = df.copy()
    for lag in range(1, n_lags + 1):
        df[f"{col}_lag{lag}"] = df[col].shift(lag)
    return df


def build_lp_dataset(df: pd.DataFrame, horizon: int,
                     break_quarter: str, n_lags: int) -> pd.DataFrame:
    work = df[["quarter", "cpi_log_diff", "oil_log_diff",
               "D_covid", "igrea", "fiscal_proxy"]].copy()
    work = add_regime_variables(work, break_quarter=break_quarter)
    work["y_lead"] = work["cpi_log_diff"].shift(-horizon)
    work["y_lag1"] = work["cpi_log_diff"].shift(1)
    work["lp_depvar"] = work["y_lead"] - work["y_lag1"]
    work = add_lags(work, "cpi_log_diff", n_lags=n_lags)
    work = add_lags(work, "oil_log_diff", n_lags=n_lags)

    lag_cols = [f"{v}_lag{l}" for l in range(1, n_lags + 1)
                for v in ["cpi_log_diff", "oil_log_diff"]]

    cols = ["quarter", "lp_depvar", "oil_log_diff", "oil_x_Dlib_model",
            "D_lib_model", "D_covid", "igrea", "fiscal_proxy", *lag_cols]
    return work[cols].dropna().reset_index(drop=True)


def run_lp_regression(lp_df: pd.DataFrame, n_lags: int, horizon: int):
    y = lp_df["lp_depvar"]
    x_cols = ["oil_log_diff", "oil_x_Dlib_model", "D_lib_model",
               "D_covid", "igrea", "fiscal_proxy"]
    for lag in range(1, n_lags + 1):
        x_cols += [f"cpi_log_diff_lag{lag}", f"oil_log_diff_lag{lag}"]
    X = sm.add_constant(lp_df[x_cols])
    return sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": horizon + 1})


def collect_lp_results(df: pd.DataFrame, break_quarter: str,
                       n_lags: int, max_horizon: int) -> pd.DataFrame:
    rows = []
    for h in range(max_horizon + 1):
        lp_df = build_lp_dataset(df, horizon=h,
                                 break_quarter=break_quarter, n_lags=n_lags)
        res = run_lp_regression(lp_df, n_lags=n_lags, horizon=h)

        b0  = res.params["oil_log_diff"]
        b0_se = res.bse["oil_log_diff"]
        d   = res.params["oil_x_Dlib_model"]
        d_se  = res.bse["oil_x_Dlib_model"]

        rows.append({
            "break_quarter":       break_quarter,
            "horizon":             h,
            "n_obs":               int(res.nobs),
            "beta_pre":            b0,
            "beta_pre_se":         b0_se,
            "beta_pre_pvalue":     res.pvalues["oil_log_diff"],
            "beta_change":         d,
            "beta_change_se":      d_se,
            "beta_change_pvalue":  res.pvalues["oil_x_Dlib_model"],
            "beta_post":           b0 + d,
            "r_squared":           res.rsquared,
        })
    return pd.DataFrame(rows)


def print_summary(all_results: pd.DataFrame) -> None:
    print("\n" + "=" * 65)
    print("ROBUSTNESS — β_change par date de rupture (HAC)")
    print("=" * 65)
    print(f"{'Break':<10} {'h=3':>8} {'h=4':>8} {'h=5':>8} {'h=6':>8}")
    print("-" * 65)
    for bq in BREAK_QUARTERS:
        sub = all_results[all_results.break_quarter == bq].set_index("horizon")
        vals = []
        for h in [3, 4, 5, 6]:
            b = sub.loc[h, "beta_change"]
            p = sub.loc[h, "beta_change_pvalue"]
            star = "***" if p < 0.01 else ("**" if p < 0.05 else
                   ("*" if p < 0.10 else ""))
            vals.append(f"{b:+.3f}{star}")
        print(f"{bq:<10} " + "  ".join(f"{v:>10}" for v in vals))
    print("-" * 65)
    print("* p<0.10  ** p<0.05  *** p<0.01  (HAC Newey-West, maxlags=h+1)")


def main() -> None:
    df = load_data()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []

    for bq in BREAK_QUARTERS:
        print(f"\nEstimation : break = {bq} ...", end=" ", flush=True)
        results_df = collect_lp_results(df, break_quarter=bq,
                                        n_lags=N_LAGS, max_horizon=MAX_HORIZON)
        all_results.append(results_df)

        safe = bq.replace("Q", "_Q")
        path = OUTPUT_DIR / f"lp_results_cpi_{safe}_lags{N_LAGS}.csv"
        results_df.to_csv(path, index=False)
        print(f"→ {path.name}")

    combined = pd.concat(all_results, ignore_index=True)
    combined.to_csv(OUTPUT_DIR / "lp_robustness_all_breaks.csv", index=False)
    print_summary(combined)


if __name__ == "__main__":
    main()