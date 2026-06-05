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
    "slice_thickness_mm",
    "num_slices",
]


def summarize(csv_path: Path) -> None:
    df = pd.read_csv(csv_path)

    print(f"\n=== RCC Dataset Summary ({len(df)} scans) ===\n")

    print("Histological subtypes:")
    for subtype, count in df["tumor_histological_subtype"].value_counts().items():
        print(f"  {subtype}: {count}")

    print("\nPatient demographics:")
    sex_counts = df["patient_sex"].value_counts(dropna=False)
    for sex, count in sex_counts.items():
        label = str(sex) if pd.notna(sex) else "Unknown"
        print(f"  {label}: {count}")
    age = df["patient_age"].apply(
        lambda x: (
            pd.to_numeric(str(x).rstrip("Y"), errors="coerce") if pd.notna(x) else float("nan")
        )
    )
    n_age = age.notna().sum()
    if n_age > 0:
        print(
            f"  Age: mean {age.mean():.1f}  (min {int(age.min())}, max {int(age.max())}, n={n_age})"
        )
    else:
        print("  Age: no numeric data available")

    total_tumor_size = df["accumulated_tumor_size_ml"].sum()
    total_tumor_count = df["tumor_count"].sum()
    macro_avg_tumor_size = (
        total_tumor_size / total_tumor_count if total_tumor_count > 0 else float("nan")
    )

    total_cyst_size = df["accumulated_cyst_size_ml"].sum()
    total_cyst_count = df["cyst_count"].sum()
    macro_avg_cyst_size = (
        total_cyst_size / total_cyst_count if total_cyst_count > 0 else float("nan")
    )

    total_tumor_diameter = df["accumulated_tumor_diameter_mm"].sum()
    macro_avg_tumor_diameter = (
        total_tumor_diameter / total_tumor_count if total_tumor_count > 0 else float("nan")
    )

    total_cyst_diameter = df["accumulated_cyst_diameter_mm"].sum()
    macro_avg_cyst_diameter = (
        total_cyst_diameter / total_cyst_count if total_cyst_count > 0 else float("nan")
    )

    print("\nMacro average lesion size (total accumulated size / total count):")
    print(
        f"  Tumor: {total_tumor_size:.2f} ml total / {int(total_tumor_count)} "
        f"tumors = {macro_avg_tumor_size:.2f} ml/tumor"
    )
    print(
        f"  Cyst:  {total_cyst_size:.2f} ml total / {int(total_cyst_count)} "
        f"cysts  = {macro_avg_cyst_size:.2f} ml/cyst"
    )

    print("\nMacro average lesion diameter (total accumulated diameter / total count):")
    print(
        f"  Tumor: {total_tumor_diameter:.2f} mm total / {int(total_tumor_count)} "
        f"tumors = {macro_avg_tumor_diameter:.2f} mm/tumor"
    )
    print(
        f"  Cyst:  {total_cyst_diameter:.2f} mm total / {int(total_cyst_count)} "
        f"cysts  = {macro_avg_cyst_diameter:.2f} mm/cyst"
    )

    print("\nScan geometry:")
    print(
        f"  Avg slice thickness: {df['slice_thickness_mm'].mean():.2f} mm  "
        f"(min {df['slice_thickness_mm'].min():.2f}, max {df['slice_thickness_mm'].max():.2f})"
    )
    print(
        f"  Avg number of slices: {df['num_slices'].mean():.1f} "
        f"(min {int(df['num_slices'].min())}, max {int(df['num_slices'].max())})"
    )

    print("\nMacro average lesion size and diameter per subtype:")
    subtype_col = "tumor_histological_subtype"
    header = (
        f"  {'Subtype':<22} {'Tumors':>7} {'Avg size (ml)':>14} {'Avg diam (mm)':>14}"
        f" {'Cysts':>7} {'Avg size (ml)':>14} {'Avg diam (mm)':>14}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for subtype, group in df.groupby(subtype_col):
        t_count = group["tumor_count"].sum()
        avg_t_size = (
            group["accumulated_tumor_size_ml"].sum() / t_count if t_count > 0 else float("nan")
        )
        avg_t_diam = (
            group["accumulated_tumor_diameter_mm"].sum() / t_count if t_count > 0 else float("nan")
        )
        c_count = group["cyst_count"].sum()
        avg_c_size = (
            group["accumulated_cyst_size_ml"].sum() / c_count if c_count > 0 else float("nan")
        )
        avg_c_diam = (
            group["accumulated_cyst_diameter_mm"].sum() / c_count if c_count > 0 else float("nan")
        )
        print(
            f"  {subtype:<22} {int(t_count):>7} {avg_t_size:>14.2f} {avg_t_diam:>14.2f}"
            f" {int(c_count):>7} {avg_c_size:>14.2f} {avg_c_diam:>14.2f}"
        )

    print("\nNumeric statistics:")
    stats = df[NUMERIC_COLUMNS].describe().loc[["mean", "std", "min", "max"]]
    print(stats.to_string())
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a summary of the RCC dataset analysis CSV.")
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
                f"CSV not found at '{args.output_csv}'. Provide --data-folder to generate it first."
            )
        print(f"CSV not found. Running analysis on '{args.data_folder}' first...\n")
        analyze(args.data_folder, args.output_csv)

    summarize(args.output_csv)


if __name__ == "__main__":
    main()
