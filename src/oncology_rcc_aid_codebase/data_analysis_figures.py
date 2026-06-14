import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

SUBTYPE_ORDER = ["Clear Cell RCC", "Papillary RCC", "Chromophobe RCC"]
SEX_ORDER = ["Male", "Female"]
SEX_PALETTE = {"Male": "#999999", "Female": "#cccccc"}


def make_figures(df: pd.DataFrame, output_filename: str) -> None:
    patients = df.drop_duplicates(subset="patient_id")
    sex_counts = (
        patients.groupby(["tumor_histological_subtype", "patient_sex"])
        .size()
        .reset_index(name="count")
    )

    fig, axes = plt.subplots(3, 2, figsize=(12, 14))

    # Row 1 — Tumor characteristics
    sns.kdeplot(
        data=df,
        x="accumulated_tumor_size_ml",
        hue="tumor_histological_subtype",
        hue_order=SUBTYPE_ORDER,
        fill=True,
        cut=0,
        alpha=0.4,
        common_norm=False,
        ax=axes[0, 0],
    )
    axes[0, 0].set_title("Tumor volume by subtype")
    axes[0, 0].set_xlabel("Volume (ml)")
    axes[0, 0].set_ylabel("Density")
    sns.move_legend(axes[0, 0], "upper right", title="Subtype")

    sns.kdeplot(
        data=df,
        x="accumulated_tumor_diameter_mm",
        hue="tumor_histological_subtype",
        hue_order=SUBTYPE_ORDER,
        fill=True,
        cut=0,
        alpha=0.4,
        common_norm=False,
        ax=axes[0, 1],
    )
    axes[0, 1].set_title("Tumor diameter by subtype")
    axes[0, 1].set_xlabel("Diameter (mm)")
    axes[0, 1].set_ylabel("Density")
    sns.move_legend(axes[0, 1], "upper right", title="Subtype")

    # Row 2 — Relationships
    sns.scatterplot(
        data=df,
        x="age",
        y="accumulated_tumor_size_ml",
        hue="tumor_histological_subtype",
        hue_order=SUBTYPE_ORDER,
        ax=axes[1, 0],
    )
    sns.regplot(
        data=df,
        x="age",
        y="accumulated_tumor_size_ml",
        scatter=False,
        color="grey",
        ax=axes[1, 0],
    )
    r_age = df["age"].corr(df["accumulated_tumor_size_ml"])
    axes[1, 0].annotate(
        f"r = {r_age:.2f}", xy=(0.05, 0.92), xycoords="axes fraction", fontsize=10
    )
    axes[1, 0].set_title("Tumor volume vs age")
    axes[1, 0].set_xlabel("Age (years)")
    axes[1, 0].set_ylabel("Volume (ml)")
    sns.move_legend(axes[1, 0], "upper right", title="Subtype")

    sns.scatterplot(
        data=df,
        x="accumulated_tumor_diameter_mm",
        y="accumulated_tumor_size_ml",
        hue="tumor_histological_subtype",
        hue_order=SUBTYPE_ORDER,
        ax=axes[1, 1],
    )
    axes[1, 1].set_xscale("log")
    axes[1, 1].set_yscale("log")
    r_diam = df["accumulated_tumor_diameter_mm"].corr(
        df["accumulated_tumor_size_ml"], method="spearman"
    )
    axes[1, 1].annotate(
        f"Spearman r = {r_diam:.2f}",
        xy=(0.05, 0.92),
        xycoords="axes fraction",
        fontsize=10,
    )
    axes[1, 1].set_title("Tumor volume vs diameter")
    axes[1, 1].set_xlabel("Diameter (mm)")
    axes[1, 1].set_ylabel("Volume (ml)")
    sns.move_legend(axes[1, 1], "lower right", title="Subtype")

    # Row 3 — Patient demographics
    sns.kdeplot(
        data=patients,
        x="age",
        hue="patient_sex",
        hue_order=SEX_ORDER,
        fill=True,
        cut=0,
        alpha=0.4,
        common_norm=False,
        palette=SEX_PALETTE,
        ax=axes[2, 0],
    )
    axes[2, 0].set_title("Age distribution by sex")
    axes[2, 0].set_xlabel("Age (years)")
    axes[2, 0].set_ylabel("Density")
    sns.move_legend(axes[2, 0], "upper right", title="Sex")

    sns.barplot(
        data=sex_counts,
        x="tumor_histological_subtype",
        y="count",
        hue="patient_sex",
        hue_order=SEX_ORDER,
        order=SUBTYPE_ORDER,
        palette=SEX_PALETTE,
        ax=axes[2, 1],
    )
    axes[2, 1].set_title("Sex distribution by subtype")
    axes[2, 1].set_xlabel("Subtype")
    axes[2, 1].set_ylabel("Number of patients")
    sns.move_legend(axes[2, 1], "upper right", title="Sex")

    plt.tight_layout()

    for ax, letter in zip(axes.flat, "abcdef"):
        ax.text(
            -0.1,
            1.05,
            letter,
            transform=ax.transAxes,
            fontsize=14,
            fontweight="bold",
            va="top",
        )

    plt.savefig(output_filename, dpi=300)


def main() -> None:
    sns.set_theme(style="ticks")

    argparser = argparse.ArgumentParser(
        description="Generate figures summarizing the RCC dataset analysis."
    )
    argparser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the CSV file containing the analyzed RCC dataset.",
    )
    argparser.add_argument(
        "output_filename",
        type=str,
        default="data_analysis_figures.pdf",
        help="Output filename to save the generated figure.",
    )
    args = argparser.parse_args()

    df = pd.read_csv(args.csv_path)

    # Parse age from TCGA format (e.g. '036Y' -> 36)
    df["age"] = pd.to_numeric(df["patient_age"].str.rstrip("Y"), errors="coerce")

    # Expand sex labels
    df["patient_sex"] = df["patient_sex"].map({"M": "Male", "F": "Female"})

    make_figures(df, args.output_filename)


if __name__ == "__main__":
    main()
