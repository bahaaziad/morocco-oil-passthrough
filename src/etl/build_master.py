from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def load_csv(filename: str) -> pd.DataFrame:
    path = RAW_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")
    return pd.read_csv(path)


def standardize_quarter_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    possible_cols = ["quarter", "date", "observation_date", "Unnamed: 0"]
    quarter_col = None

    for col in possible_cols:
        if col in df.columns:
            quarter_col = col
            break

    if quarter_col is None:
        raise ValueError(
            f"Aucune colonne de date/trimestre trouvée parmi {possible_cols}. "
            f"Colonnes disponibles: {list(df.columns)}"
        )

    df = df.rename(columns={quarter_col: "quarter"})
    df["quarter"] = df["quarter"].astype(str).str.strip()

    return df


def keep_expected_columns(df: pd.DataFrame, expected_cols: list[str]) -> pd.DataFrame:
    missing = [col for col in expected_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Colonnes manquantes: {missing}. Colonnes disponibles: {list(df.columns)}"
        )
    return df[expected_cols].copy()


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    oil = load_csv("oil_quarterly.csv")
    cpi = load_csv("cpi_quarterly.csv")
    igrea = load_csv("igrea_quarterly.csv")
    macro = load_csv("macro_quarterly.csv")

    oil = standardize_quarter_column(oil)
    cpi = standardize_quarter_column(cpi)
    igrea = standardize_quarter_column(igrea)
    macro = standardize_quarter_column(macro)

    oil = keep_expected_columns(
        oil,
        ["quarter", "oil_usd", "oil_log_diff", "D_lib", "D_covid", "oil_x_Dlib"],
    )

    cpi = keep_expected_columns(
        cpi,
        ["quarter", "cpi_level", "cpi_log_diff"],
    )

    igrea = keep_expected_columns(
        igrea,
        ["quarter", "igrea"],
    )

    macro = keep_expected_columns(
        macro,
        ["quarter", "ca_pct_gdp", "fiscal_balance_pct_gdp", "fiscal_proxy"],
    )

    master = oil.merge(cpi, on="quarter", how="inner")
    master = master.merge(igrea, on="quarter", how="inner")
    master = master.merge(macro, on="quarter", how="inner")

    master = master.sort_values("quarter").reset_index(drop=True)

    if master["quarter"].duplicated().any():
        duplicated_quarters = master.loc[master["quarter"].duplicated(), "quarter"].tolist()
        raise ValueError(f"Doublons détectés dans quarter: {duplicated_quarters}")

    required_cols = [
        "quarter",
        "oil_usd",
        "oil_log_diff",
        "cpi_level",
        "cpi_log_diff",
        "igrea",
        "ca_pct_gdp",
        "fiscal_balance_pct_gdp",
        "fiscal_proxy",
        "D_lib",
        "D_covid",
        "oil_x_Dlib",
    ]

    if master[required_cols].isna().sum().sum() > 0:
        na_counts = master[required_cols].isna().sum()
        raise ValueError(f"Valeurs manquantes détectées:\n{na_counts[na_counts > 0]}")

    output_path = PROCESSED_DIR / "master_quarterly_no_fx.csv"
    master.to_csv(output_path, index=False)

    print("Fichier master créé avec succès :")
    print(output_path)
    print(f"Nombre de lignes : {len(master)}")
    print(f"Période : {master['quarter'].min()} -> {master['quarter'].max()}")


if __name__ == "__main__":
    main()