"""CLI to print a summary of the RCC dataset analysis results."""

import argparse
from pathlib import Path

import pandas as pd

from oncology_rcc_dataset.analyze_data import analyze


NUMERIC_COLUMNS = [
    "accumulated_tumor_size_ml",
    "tumor_count",
    "accumulated_tumor_diameter_mm",
    "accumulated_cyst_size_ml",
    "cyst_count",
    "accumulated_cyst_diameter_mm",
]


def summarize(csv_path: Path) -> None:
    df = pd.read_csv(csv_path)

    print(f"\n=== RCC Dataset Summary ({len(df)} scans) ===\n")

    print("Histological subtypes:")
    for subtype, count in df["tumor_histological_subtype"].value_counts().items():
        print(f"  {subtype}: {count}")

    total_tumor_size = df["accumulated_tumor_size_ml"].sum()
    total_tumor_count = df["tumor_count"].sum()
    macro_avg_tumor_size = total_tumor_size / total_tumor_count if total_tumor_count > 0 else float("nan")

    total_cyst_size = df["accumulated_cyst_size_ml"].sum()
    total_cyst_count = df["cyst_count"].sum()
    macro_avg_cyst_size = total_cyst_size / total_cyst_count if total_cyst_count > 0 else float("nan")

    total_tumor_diameter = df["accumulated_tumor_diameter_mm"].sum()
    macro_avg_tumor_diameter = total_tumor_diameter / total_tumor_count if total_tumor_count > 0 else float("nan")

    total_cyst_diameter = df["accumulated_cyst_diameter_mm"].sum()
    macro_avg_cyst_diameter = total_cyst_diameter / total_cyst_count if total_cyst_count > 0 else float("nan")

    print("\nMacro average lesion size (total accumulated size / total count):")
    print(f"  Tumor: {total_tumor_size:.2f} ml total / {int(total_tumor_count)} tumors = {macro_avg_tumor_size:.2f} ml/tumor")
    print(f"  Cyst:  {total_cyst_size:.2f} ml total / {int(total_cyst_count)} cysts  = {macro_avg_cyst_size:.2f} ml/cyst")

    print("\nMacro average lesion diameter (total accumulated diameter / total count):")
    print(f"  Tumor: {total_tumor_diameter:.2f} mm total / {int(total_tumor_count)} tumors = {macro_avg_tumor_diameter:.2f} mm/tumor")
    print(f"  Cyst:  {total_cyst_diameter:.2f} mm total / {int(total_cyst_count)} cysts  = {macro_avg_cyst_diameter:.2f} mm/cyst")

    print("\nNumeric statistics:")
    stats = df[NUMERIC_COLUMNS].describe().loc[["mean", "std", "min", "max"]]
    print(stats.to_string())
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a summary of the RCC dataset analysis CSV."
    )
    parser.add_argument(
        "output_csv",
        type=Path,
        help="Path to the analysis CSV file.",
    )
    parser.add_argument(
        "--data-folder",
        type=Path,
        default=None,
        help="Dataset folder to run analysis from if the CSV does not exist yet.",
    )
    args = parser.parse_args()

    if not args.output_csv.exists():
        if args.data_folder is None:
            raise FileNotFoundError(
                f"CSV not found at '{args.output_csv}'. "
                "Provide --data-folder to generate it first."
            )
        print(f"CSV not found. Running analysis on '{args.data_folder}' first...\n")
        analyze(args.data_folder, args.output_csv)

    summarize(args.output_csv)


if __name__ == "__main__":
    main()
