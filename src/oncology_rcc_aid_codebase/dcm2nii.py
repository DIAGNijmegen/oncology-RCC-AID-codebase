import argparse
import csv
import os
from collections import Counter, defaultdict

import pydicom
import SimpleITK as sitk
from tqdm.auto import tqdm


def get_depth_directories(root_dir, target_depth):
    """Find directories at a specific depth from the root."""
    return [
        dirpath
        for dirpath, _, _ in os.walk(root_dir)
        if os.path.relpath(dirpath, root_dir).count(os.sep) == target_depth
    ]


def validate_and_group_slices(file_list):
    """Groups valid slices by Acquisition Number and filters inconsistent dimensions."""
    slices_by_acq = defaultdict(list)

    for f in file_list:
        try:
            ds = pydicom.dcmread(f, stop_before_pixels=True)
            acq_num = str(getattr(ds, "AcquisitionNumber", "unknown")).strip()
            rows, cols = ds.get("Rows"), ds.get("Columns")

            if rows is not None and cols is not None:
                slices_by_acq[acq_num or "unknown"].append((f, rows, cols))
        except Exception:
            continue  # Skip files that aren't valid DICOMs

    valid_groups = {}
    for acq, slices in slices_by_acq.items():
        if not slices:
            continue
        # Enforce consistent dimensions per acquisition group
        dim_counts = Counter((s[1], s[2]) for s in slices)
        common_dim = dim_counts.most_common(1)[0][0]
        valid_groups[acq] = [s[0] for s in slices if (s[1], s[2]) == common_dim]

    return valid_groups


def process_dicom_series(dicom_dir, nifti_dir, csv_path, prefix=""):
    """Converts DICOMs to NIfTI by series and acquisition."""
    os.makedirs(nifti_dir, exist_ok=True)
    csv_data = []

    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(dicom_dir)

    for series_id in series_ids:
        series_files = reader.GetGDCMSeriesFileNames(dicom_dir, series_id)
        acq_groups = validate_and_group_slices(series_files)

        for acq_num, filtered_files in acq_groups.items():
            if not filtered_files:
                continue
            try:
                reader.SetFileNames(filtered_files)
                image = reader.Execute()

                uid = series_id.replace(".", "_")
                base_name = f"{prefix}_{uid}_acq_{acq_num}" if prefix else f"{uid}_acq_{acq_num}"
                sitk.WriteImage(image, os.path.join(nifti_dir, f"{base_name}.nii.gz"))

                csv_data.append([dicom_dir, series_id, acq_num, len(filtered_files)])
            except Exception as e:
                tqdm.write(f"Failed to process Series {series_id}, Acq {acq_num}: {e}")

    # Append to tracker CSV
    if csv_data:
        file_exists = os.path.isfile(csv_path)
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["input_dir", "series_uid", "acquisition_number", "slice_count"])
            writer.writerows(csv_data)


def main():
    parser = argparse.ArgumentParser(description="Batch convert TCIA DICOMs to NIfTI.")
    parser.add_argument("input_dir", help="Root directory containing DICOM files")
    parser.add_argument("output_dir", help="Directory to save the resulting NIfTI files")
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Directory depth to search for DICOMs (default: 3)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Optional prefix for output NIfTI filenames",
    )

    args = parser.parse_args()
    csv_path = os.path.join(args.output_dir, "conversion_log.csv")

    # 1. First create the list of relevant directories
    target_dirs = get_depth_directories(args.input_dir, args.depth)
    if not target_dirs:  # Fallback if depth finds nothing
        target_dirs = [args.input_dir]

    print(f"Found {len(target_dirs)} directories to process at depth {args.depth}.")

    # 2. Execute the conversion with tqdm over the pre-built list
    for d in tqdm(target_dirs, desc="Converting Directories"):
        process_dicom_series(d, args.output_dir, csv_path, args.prefix)


if __name__ == "__main__":
    main()
