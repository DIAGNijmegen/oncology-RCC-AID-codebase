"""CLI to print a summary of the RCC dataset analysis results."""

import argparse
from pathlib import Path

import pandas as pd

from oncology_rcc_aid_codebase.analyze_data import analyze

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


def _macro_avg(total: float, count: float) -> float:
    return total / count if count > 0 else float("nan")


def summarize(csv_path: Path) -> None:
    """Print a summary of the RCC dataset analysis CSV to stdout."""
    df = pd.read_csv(csv_path)

    n_patients = df["patient_id"].nunique()
    print(f"\n=== RCC Dataset Summary ({len(df)} scans, {n_patients} patients) ===\n")

    patients_per_subtype = df.groupby("tumor_histological_subtype")[
        "patient_id"
    ].nunique()
    print("Histological subtypes (scans / patients):")
    for subtype, scan_count in df["tumor_histological_subtype"].value_counts().items():
        print(f"  {subtype}: {scan_count} / {patients_per_subtype[subtype]} patients")

    n_scans_with_cyst = (df["cyst_count"] > 0).sum()
    n_patients_with_cyst = df.loc[df["cyst_count"] > 0, "patient_id"].nunique()
    print(
        f"\nScans with at least one cyst:    {n_scans_with_cyst} / {len(df)} ({100 * n_scans_with_cyst / len(df):.1f}%)"
    )
    print(
        f"Patients with at least one cyst: {n_patients_with_cyst} / {n_patients} ({100 * n_patients_with_cyst / n_patients:.1f}%)"
    )

    patients = df.drop_duplicates(subset="patient_id")

    print("\nPatient demographics:")
    sex_counts = patients["patient_sex"].value_counts(dropna=False)
    for sex, count in sex_counts.items():
        label = str(sex) if pd.notna(sex) else "Unknown"
        print(f"  {label}: {count}")
    age = patients["patient_age"].apply(
        lambda x: (
            pd.to_numeric(str(x).rstrip("Y"), errors="coerce")
            if pd.notna(x)
            else float("nan")
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
    total_cyst_size = df["accumulated_cyst_size_ml"].sum()
    total_cyst_count = df["cyst_count"].sum()
    total_tumor_diameter = df["accumulated_tumor_diameter_mm"].sum()
    total_cyst_diameter = df["accumulated_cyst_diameter_mm"].sum()

    print("\nMacro average lesion size (total accumulated size / total count):")
    print(
        f"  Tumor: {total_tumor_size:.2f} ml total"
        f" / {int(total_tumor_count)} tumors"
        f" = {_macro_avg(total_tumor_size, total_tumor_count):.2f} ml/tumor"
    )
    print(
        f"  Cyst:  {total_cyst_size:.2f} ml total"
        f" / {int(total_cyst_count)} cysts"
        f" = {_macro_avg(total_cyst_size, total_cyst_count):.2f} ml/cyst"
    )

    print("\nMacro average lesion diameter (total accumulated diameter / total count):")
    print(
        f"  Tumor: {total_tumor_diameter:.2f} mm total"
        f" / {int(total_tumor_count)} tumors"
        f" = {_macro_avg(total_tumor_diameter, total_tumor_count):.2f} mm/tumor"
    )
    print(
        f"  Cyst:  {total_cyst_diameter:.2f} mm total"
        f" / {int(total_cyst_count)} cysts"
        f" = {_macro_avg(total_cyst_diameter, total_cyst_count):.2f} mm/cyst"
    )

    thickness = df["slice_thickness_mm"]
    slices = df["num_slices"]
    print("\nScan geometry:")
    print(
        f"  Avg slice thickness: {thickness.mean():.2f} mm"
        f"  (min {thickness.min():.2f}, max {thickness.max():.2f})"
    )
    print(
        f"  Avg number of slices: {slices.mean():.1f}"
        f"  (min {int(slices.min())}, max {int(slices.max())})"
    )

    subtype_col = "tumor_histological_subtype"

    print("\nSize and diameter per subtype:")
    header = (
        f"  {'Subtype':<24} {'Count':>7}"
        f" {'Avg size (ml)':>14} {'Std size (ml)':>14}"
        f" {'Avg diam (mm)':>14} {'Std diam (mm)':>14}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for subtype, group in df.groupby(subtype_col):
        t_count = group["tumor_count"].sum()
        avg_t_size = _macro_avg(group["accumulated_tumor_size_ml"].sum(), t_count)
        std_t_size = group["accumulated_tumor_size_ml"].std()
        avg_t_diam = _macro_avg(group["accumulated_tumor_diameter_mm"].sum(), t_count)
        std_t_diam = group["accumulated_tumor_diameter_mm"].std()
        print(
            f"  {subtype:<24} {int(t_count):>7}"
            f" {avg_t_size:>14.2f} {std_t_size:>14.2f}"
            f" {avg_t_diam:>14.2f} {std_t_diam:>14.2f}"
        )
    total_cyst_count = df["cyst_count"].sum()
    avg_c_size = _macro_avg(df["accumulated_cyst_size_ml"].sum(), total_cyst_count)
    std_c_size = df["accumulated_cyst_size_ml"].std()
    avg_c_diam = _macro_avg(df["accumulated_cyst_diameter_mm"].sum(), total_cyst_count)
    std_c_diam = df["accumulated_cyst_diameter_mm"].std()
    print("  " + "-" * (len(header) - 2))
    print(
        f"  {'Cyst':<24} {int(total_cyst_count):>7}"
        f" {avg_c_size:>14.2f} {std_c_size:>14.2f}"
        f" {avg_c_diam:>14.2f} {std_c_diam:>14.2f}"
    )

    print("\nNumeric statistics:")
    stats = df[NUMERIC_COLUMNS].describe().loc[["mean", "std", "min", "max"]]
    print(stats.to_string())
    print()


def main() -> None:
    """Entry point for the summarize-rcc-data CLI command."""
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
