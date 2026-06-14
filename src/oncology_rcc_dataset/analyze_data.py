"""CLI to analyze the RCC dataset.

This script processes the CT scans and segmentation labels to extract relevant features
such as tumor size, count, and diameter, as well as cyst characteristics. The results
are saved in a CSV file for further analysis.

The labels in the segmentation masks are expected to be encoded as follows:
- 0: Background
- 1: Kidney
- 2: Tumor
- 3: Cyst
"""

import argparse
import glob
from pathlib import Path

import pandas as pd
import SimpleITK as sitk


def get_connected_components(seg_binary: sitk.Image) -> tuple[sitk.Image, int]:
    image_filter = sitk.ConnectedComponentImageFilter()
    image_filter.SetFullyConnected(True)
    cc = image_filter.Execute(seg_binary)
    num = image_filter.GetObjectCount()

    return cc, num


def diameter_lesion(seg_single_lesion: sitk.Image) -> float:
    stats3d = sitk.LabelShapeStatisticsImageFilter()
    stats3d.Execute(seg_single_lesion)

    size = list(seg_single_lesion.GetSize())  # (x, y, z)

    stats2d = sitk.LabelShapeStatisticsImageFilter()
    stats2d.SetComputeFeretDiameter(True)

    if stats3d.GetNumberOfLabels() != 1:
        raise ValueError("Expected exactly one lesion in the input segmentation.")

    label = 1
    # Use bounding box to restrict which slices we check
    # BoundingBox is (x, y, z, size_x, size_y, size_z)
    bb = stats3d.GetBoundingBox(label)
    z0 = int(bb[2])
    z1 = int(bb[2] + bb[5])  # exclusive

    max_d = 0.0
    for z in range(z0, z1):
        slice_lab = sitk.Extract(seg_single_lesion, size=[size[0], size[1], 0], index=[0, 0, z])
        slice_bin = sitk.Cast(slice_lab == label, sitk.sitkUInt8)

        # If label exists on this slice, it will be the only foreground (value 1)
        stats2d.Execute(slice_bin)
        if stats2d.HasLabel(1):
            d = stats2d.GetFeretDiameter(1)
            if d > max_d:
                max_d = d

    return max_d


def analyze_tumors(seg: sitk.Image) -> tuple[float, int, float]:
    tumor_seg = sitk.BinaryThreshold(seg, lowerThreshold=2, upperThreshold=2)

    connected_components, num_tumors = get_connected_components(tumor_seg)

    tumor_size_ml = (
        sitk.GetArrayFromImage(tumor_seg).sum()
        * (seg.GetSpacing()[0] * seg.GetSpacing()[1] * seg.GetSpacing()[2])
        / 1000.0
    )

    tumor_count = num_tumors

    tumor_diameter_mm = 0.0
    for tumor_label in range(1, num_tumors + 1):
        tumor_binary = sitk.BinaryThreshold(
            connected_components, lowerThreshold=tumor_label, upperThreshold=tumor_label
        )
        tumor_diameter_mm += diameter_lesion(tumor_binary)

    return tumor_size_ml, tumor_count, tumor_diameter_mm


def analyze_cysts(seg: sitk.Image) -> tuple[float, int, float]:
    cyst_seg = sitk.BinaryThreshold(seg, lowerThreshold=3, upperThreshold=3)

    connected_components, num_cysts = get_connected_components(cyst_seg)

    cyst_size_ml = (
        sitk.GetArrayFromImage(cyst_seg).sum()
        * (seg.GetSpacing()[0] * seg.GetSpacing()[1] * seg.GetSpacing()[2])
        / 1000.0
    )

    cyst_count = num_cysts

    cyst_diameter_mm = 0.0
    for cyst_label in range(1, num_cysts + 1):
        cyst_binary = sitk.BinaryThreshold(
            connected_components, lowerThreshold=cyst_label, upperThreshold=cyst_label
        )
        cyst_diameter_mm += diameter_lesion(cyst_binary)

    return cyst_size_ml, cyst_count, cyst_diameter_mm


def analyze(data_folder: Path, output_csv: Path) -> None:
    scans = glob.glob(str(data_folder / "images" / "*.nii.gz"), recursive=True)
    labels = glob.glob(str(data_folder / "labels" / "*.nii.gz"), recursive=True)
    print(f"Found {len(scans)} scan files.")
    print(f"Found {len(labels)} label files.")

    metadata_csv_path = data_folder / "metadata.csv"
    metadata_df = pd.read_csv(metadata_csv_path)

    dataset_mapping = {
        "KIRC": "Clear Cell RCC",
        "KIRP": "Papillary RCC",
        "KICH": "Chromophobe RCC",
    }
    for i, scan_path in enumerate(scans):
        scan_name = Path(scan_path).name.removesuffix(".nii.gz")
        label_path = data_folder / "labels" / f"{scan_name}_seg.nii.gz"
        if str(label_path) not in labels:
            raise FileNotFoundError(f"Label file not found for scan: {scan_path}")

        ct = sitk.ReadImage(scan_path)
        seg = sitk.ReadImage(label_path)

        dataset = scan_name.split("_")[0]
        histological_subtype = dataset_mapping[dataset]

        tumor_size_ml, tumor_count, tumor_diameter_mm = analyze_tumors(seg)
        cyst_size_ml, cyst_count, cyst_diameter_mm = analyze_cysts(seg)

        slice_thickness_mm = ct.GetSpacing()[2]
        num_slices = ct.GetSize()[2]

        series_uid = scan_name.split("_acq")[0].removeprefix(dataset + "_").replace("_", ".")

        match = metadata_df.loc[metadata_df["SeriesInstanceUID"] == series_uid]
        patient_sex = match["PatientSex"].iloc[0] if not match.empty else None
        patient_age = match["PatientAge"].iloc[0] if not match.empty else None

        scan_data = {
            "series_uid": series_uid,
            "patient_sex": patient_sex,
            "patient_age": patient_age,
            "accumulated_tumor_size_ml": tumor_size_ml,
            "tumor_count": tumor_count,
            "accumulated_tumor_diameter_mm": tumor_diameter_mm,
            "tumor_histological_subtype": histological_subtype,
            "accumulated_cyst_size_ml": cyst_size_ml,
            "cyst_count": cyst_count,
            "accumulated_cyst_diameter_mm": cyst_diameter_mm,
            "slice_thickness_mm": slice_thickness_mm,
            "num_slices": num_slices,
        }

        write_header = i == 0
        pd.DataFrame([scan_data]).to_csv(
            output_csv,
            mode="w" if write_header else "a",
            header=write_header,
            index=False,
        )
        print(f"  [{i + 1}/{len(scans)}] Saved {scan_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze the RCC dataset.")
    parser.add_argument(
        "data_folder",
        type=Path,
        help="""Directory containing the downloaded dataset files.
        Should contain 'images/', 'labels/', and 'metadata.csv'.""",
    )
    parser.add_argument(
        "output_csv",
        type=Path,
        help="Path to the output CSV file.",
    )
    args = parser.parse_args()
    analyze(args.data_folder, args.output_csv)


if __name__ == "__main__":
    main()
