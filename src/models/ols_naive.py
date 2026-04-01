from pathlib import Path
import pandas as pd
import statsmodels.api as sm


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "master_quarterly_no_fx.csv"
OUTPUT_DIR = ROOT / "outputs" / "tables"


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Fichier introuvable: {DATA_PATH}")
    return pd.read_csv(DATA_PATH)


def prepare_regression_data(df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    required_cols = [
        "cpi_log_diff",
        "oil_log_diff",
        "D_lib",
        "oil_x_Dlib",
    ]

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Colonnes manquantes pour la régression: {missing}"
        )

    reg_df = df[required_cols].copy()

    if reg_df.isna().sum().sum() > 0:
        na_counts = reg_df.isna().sum()
        raise ValueError(f"Valeurs manquantes détectées:\n{na_counts[na_counts > 0]}")

    y = reg_df["cpi_log_diff"]
    X = reg_df[["oil_log_diff", "D_lib", "oil_x_Dlib"]]
    X = sm.add_constant(X)

    return y, X


def run_ols(y: pd.Series, X: pd.DataFrame):
    model = sm.OLS(y, X)
    results = model.fit(cov_type="HC1")
    return results


def save_results(results) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    coef_table = pd.DataFrame({
        "variable": results.params.index,
        "coef": results.params.values,
        "std_err": results.bse.values,
        "t_stat": results.tvalues.values,
        "p_value": results.pvalues.values,
    })

    coef_path = OUTPUT_DIR / "ols_naive_results.csv"
    coef_table.to_csv(coef_path, index=False)

    summary_path = OUTPUT_DIR / "ols_naive_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(results.summary().as_text())

    print("Résultats sauvegardés :")
    print(coef_path)
    print(summary_path)


def print_interpretation(results) -> None:
    beta_pre = results.params["oil_log_diff"]
    beta_change = results.params["oil_x_Dlib"]
    beta_post = beta_pre + beta_change

    print("\nInterprétation rapide :")
    print(f"Effet du pétrole avant libéralisation : {beta_pre:.6f}")
    print(f"Changement d'effet après libéralisation : {beta_change:.6f}")
    print(f"Effet du pétrole après libéralisation : {beta_post:.6f}")


def main() -> None:
    df = load_data()
    y, X = prepare_regression_data(df)
    results = run_ols(y, X)

    print(results.summary())
    print_interpretation(results)
    save_results(results)


if __name__ == "__main__":
    main()