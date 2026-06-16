"""Generate a per-subtype acquisition variables table for publication."""

import argparse
import ast
from pathlib import Path

import pandas as pd

SUBTYPE_ORDER = ["Clear cell", "Papillary", "Chromophobe"]

NUMERIC_VARS = [
    ("tube_voltage_kvp", "Tube voltage (kVp)"),
    ("tube_current_ma", "Tube current (mA)"),
    ("exposure_mas", "Exposure (mAs)"),
    ("slice_thickness_mm", "Slice thickness (mm)"),
    ("pixel_spacing_mm", "Pixel spacing (mm)"),
]


def _pixel_spacing_scalar(val) -> float | None:
    """Convert pixel_spacing_mm to a single number (in-plane, first element)."""
    if pd.isna(val):
        return None
    try:
        parsed = ast.literal_eval(str(val))
        if isinstance(parsed, (list, tuple)):
            return float(parsed[0]) if parsed else None
        return float(parsed)
    except (ValueError, SyntaxError):
        return None


def _mean_sd(series: pd.Series) -> str:
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty:
        return "—"
    return f"{series.mean():.1f} ± {series.std():.1f}"


def _top_manufacturers(series: pd.Series, n: int = 3) -> str:
    counts = series.dropna().value_counts()
    total = counts.sum()
    parts = []
    for name, cnt in counts.head(n).items():
        parts.append(f"{name} ({cnt}, {100 * cnt / total:.0f}%)")
    return "; ".join(parts)


def build_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pixel_spacing_mm"] = df["pixel_spacing_mm"].apply(_pixel_spacing_scalar)

    subtypes = [
        s for s in SUBTYPE_ORDER if s in df["tumor_histological_subtype"].unique()
    ]
    groups = {s: df[df["tumor_histological_subtype"] == s] for s in subtypes}
    groups["Total"] = df

    rows = []

    # N
    rows.append({"Variable": "N (scans)"} | {k: str(len(g)) for k, g in groups.items()})

    # Manufacturers
    rows.append(
        {"Variable": "Manufacturer (top 3)"}
        | {k: _top_manufacturers(g["manufacturer"]) for k, g in groups.items()}
    )

    # Numeric variables
    for col, label in NUMERIC_VARS:
        if col not in df.columns:
            continue
        rows.append(
            {"Variable": f"{label}, mean ± SD"}
            | {k: _mean_sd(g[col]) for k, g in groups.items()}
        )

    # Contrast
    rows.append(
        {"Variable": "Contrast enhanced, n (%)"}
        | {
            k: f"{(g['contrast_used'] == 'yes').sum()} ({100 * (g['contrast_used'] == 'yes').mean():.0f}%)"
            for k, g in groups.items()
        }
    )

    return pd.DataFrame(rows).set_index("Variable")


def print_table(table: pd.DataFrame) -> None:
    print("\n=== Acquisition Variables by RCC Subtype ===\n")
    print(table.to_string())
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a per-subtype acquisition variables table."
    )
    parser.add_argument(
        "acquisition_csv",
        type=Path,
        help="Output CSV from extract-acquisition-variables.",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.acquisition_csv)
    table = build_table(df)
    print_table(table)


if __name__ == "__main__":
    main()
