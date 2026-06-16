from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk

# CT soft-tissue window (HU)
WL, WW = 50, 400
CT_MIN, CT_MAX = WL - WW // 2, WL + WW // 2

SUBTYPES = ["Clear Cell RCC", "Papillary RCC", "Chromophobe RCC"]
COLUMNS = ["Smallest volume", "Largest volume"]


def select_representatives(group) -> list:
    group = group.sort_values("accumulated_tumor_size_ml").reset_index(drop=True)
    return [group.iloc[0], group.iloc[-1]]


def best_tumor_slice(label_arr: np.ndarray) -> int:
    """Return the axial slice index with the largest tumor (label=2) area."""
    areas = (label_arr == 2).sum(axis=(1, 2))
    return int(areas.argmax())


def load_slice(scan_path: str, label_path: str):
    """Load CT and segmentation, reorient to LPS, return the best axial slice.

    LPS orientation ensures:
    - axis 0 = Superior->Inferior  -> slicing along axis 0 gives axial slices
    - axis 1 = Anterior->Posterior -> with origin='upper', spine is at the bottom
    - axis 2 = Right->Left
    """
    ct_img = sitk.ReadImage(scan_path)
    seg_img = sitk.ReadImage(label_path)

    orient = sitk.DICOMOrientImageFilter()
    orient.SetDesiredCoordinateOrientation("LPS")
    ct_img = orient.Execute(ct_img)
    seg_img = orient.Execute(seg_img)

    ct_arr = sitk.GetArrayFromImage(ct_img)  # (S, P, L)
    seg_arr = sitk.GetArrayFromImage(seg_img)  # (S, P, L)

    z = best_tumor_slice(seg_arr)
    return ct_arr[z], seg_arr[z]


def window_ct(ct_slice: np.ndarray) -> np.ndarray:
    """Apply soft-tissue CT window and normalise to [0, 1]."""
    return (np.clip(ct_slice, CT_MIN, CT_MAX) - CT_MIN) / (CT_MAX - CT_MIN)


def make_example_cases_figure(
    df: pd.DataFrame, output_filename: str, data_folder: str
) -> None:
    representatives = {
        subtype: select_representatives(df[df["tumor_histological_subtype"] == subtype])
        for subtype in SUBTYPES
    }

    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    scan_dir = Path(data_folder) / "images"
    label_dir = Path(data_folder) / "labels"

    for col, subtype in enumerate(SUBTYPES):
        if subtype == "Clear Cell RCC":
            prefix = "KIRC"
        elif subtype == "Papillary RCC":
            prefix = "KIRP"
        elif subtype == "Chromophobe RCC":
            prefix = "KICH"
        else:
            raise ValueError(f"Unknown subtype: {subtype}")
        for row, scan_row in enumerate(representatives[subtype]):
            ax = axes[row, col]

            series_uid = scan_row["series_uid"].replace(".", "_")
            ct_path = Path(scan_dir).glob(f"{prefix}_{series_uid}_acq_*.nii.gz")
            if len(list(ct_path)) > 1:
                raise ValueError(f"More than one file match for {series_uid}")
            seg_path = Path(label_dir).glob(f"{prefix}_{series_uid}_acq_*_seg.nii.gz")
            if len(list(seg_path)) > 1:
                raise ValueError(f"More than one segmentation match for {series_uid}")
            ct_slice, seg_slice = load_slice(
                str(list(ct_path)[0]),
                str(list(seg_path)[0]),
            )

            ax.imshow(window_ct(ct_slice), cmap="gray", origin="upper")
            ax.contour(
                seg_slice == 2, levels=[0.5], colors="red", linewidths=1
            )  # tumor

            diam = scan_row["accumulated_tumor_diameter_mm"]
            ax.set_title(f"{diam:.0f} mm", fontsize=9)
            ax.axis("off")

        # Subtype column header on top row
        axes[0, col].set_title(f"{subtype}\n{axes[0, col].get_title()}", fontsize=10)

    # Row labels on the left
    for row, label in enumerate(COLUMNS):
        axes[row, 0].set_ylabel(label, fontsize=11, labelpad=10)
        axes[row, 0].axis("on")
        axes[row, 0].tick_params(
            left=False, bottom=False, labelleft=False, labelbottom=False
        )
        for spine in axes[row, 0].spines.values():
            spine.set_visible(False)

    tumor_patch = mpatches.Patch(edgecolor="red", facecolor="none", label="Tumor")
    fig.legend(
        handles=[tumor_patch], loc="lower center", ncol=1, fontsize=10, frameon=False
    )

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    plt.savefig(output_filename, dpi=300)


def main() -> None:
    import argparse

    argparser = argparse.ArgumentParser(
        description="Generate figures for the RCC dataset analysis."
    )
    argparser.add_argument(
        "csv_path",
        type=str,
        help="Path to the CSV file containing the analyzed RCC dataset.",
    )
    argparser.add_argument(
        "output_filename",
        type=str,
        help="Output filename to save the generated figure.",
    )
    argparser.add_argument(
        "data_folder",
        type=str,
        help="Path to the folder containing the CT scans and segmentation labels.",
    )

    args = argparser.parse_args()
    df = pd.read_csv(args.csv_path)
    make_example_cases_figure(df, args.output_filename, args.data_folder)


if __name__ == "__main__":
    main()
