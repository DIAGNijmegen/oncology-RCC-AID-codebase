"""CLI to extract acquisition variables from DICOM files and save to CSV."""

import argparse
from pathlib import Path

import pandas as pd
import pydicom

SUBTYPE_TO_DATASET = {
    "Clear cell": "TCGA-KIRC/manifest-xxn3N2Qq630907925598003437/TCGA-KIRC",
    "Papillary": "TCGA-KIRP/manifest-2oAypiYl1025908774074683865/TCGA-KIRP",
    "Chromophobe": "TCGA-KICH/manifest-gPS8A5x81592964856394188085/TCGA-KICH",
}


def find_series_folder(patient_folder: Path, series_uid: str) -> Path | None:
    """Walk patient/<study>/<series>/ and return the folder whose SeriesInstanceUID matches."""
    for study_folder in patient_folder.iterdir():
        if not study_folder.is_dir():
            continue
        for series_folder in study_folder.iterdir():
            if not series_folder.is_dir():
                continue
            dcm_files = sorted(series_folder.glob("*.dcm"))
            if not dcm_files:
                continue
            try:
                ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)
                if (
                    str(getattr(ds, "SeriesInstanceUID", "")).strip()
                    == series_uid.strip()
                ):
                    return series_folder
            except Exception:
                continue
    return None


def read_tag(ds: pydicom.Dataset, tag, default=None):
    elem = ds.get(tag)
    if elem is None:
        return default
    val = elem.value
    if hasattr(val, "__iter__") and not isinstance(val, str):
        return list(val)
    return val


_CONTRAST_KEYWORDS = {
    "contrast",
    "portal",
    "arterial",
    "venous",
    "bolus",
    "enhanced",
    "ce",
    "+c",
    "delayed",
    "delays",
    "delay",
    "ven",
    "art",
    "phas",
    "min",
    "with",
    "post",
    "kidney",
    "renal",
    "c",
}


def _detect_contrast(ds: pydicom.Dataset) -> str:
    """Check multiple DICOM tags for evidence of contrast, in order of reliability."""
    if read_tag(ds, (0x0018, 0x0010)):
        return "yes"

    if read_tag(ds, (0x0018, 0x1042)):
        return "yes"

    for tag in ((0x0008, 0x103E), (0x0018, 0x1030), (0x0008, 0x0008)):
        val = read_tag(ds, tag)
        if val is None:
            continue
        text = " ".join(val).lower() if isinstance(val, list) else str(val).lower()
        if any(kw in text for kw in _CONTRAST_KEYWORDS):
            return "yes"

    return "no"


def extract_acquisition_variables(dcm_path: Path) -> dict:
    ds = pydicom.dcmread(str(dcm_path), stop_before_pixels=True)

    contrast_agent = read_tag(ds, (0x0018, 0x0010))
    contrast_start = read_tag(ds, (0x0018, 0x1042))

    return {
        "manufacturer": read_tag(ds, (0x0008, 0x0070)),
        "tube_voltage_kvp": read_tag(ds, (0x0018, 0x0060)),
        "tube_current_ma": read_tag(ds, (0x0018, 0x1151)),
        "exposure_mas": read_tag(ds, (0x0018, 0x1152)),
        "slice_thickness_mm": read_tag(ds, (0x0018, 0x0050)),
        "pixel_spacing_mm": read_tag(ds, (0x0028, 0x0030)),
        "reconstruction_algorithm": read_tag(ds, (0x0018, 0x1210)),
        "contrast_agent": contrast_agent,
        "contrast_used": _detect_contrast(ds),
        "contrast_start_time": contrast_start,
    }


def extract(csv_path: Path, dicom_root: Path, output_csv: Path) -> None:
    df = pd.read_csv(csv_path)
    rows = []

    for i, (_, row) in enumerate(df.iterrows(), 1):
        patient_id = row["PatientID"]
        series_uid = row["SeriesInstanceUID"]
        subtype = row["TumorSubtype"]
        dataset_prefix = SUBTYPE_TO_DATASET.get(subtype)

        base = {"series_uid": series_uid, "patient_id": patient_id, "tumor_histological_subtype": subtype}

        if dataset_prefix is None:
            print(f"  [WARN] Unknown subtype '{subtype}' for {patient_id}")
            rows.append(base)
            continue

        patient_folder = dicom_root / dataset_prefix / patient_id
        if not patient_folder.exists():
            print(f"  [WARN] Patient folder not found: {patient_folder}")
            rows.append(base)
            continue

        series_folder = find_series_folder(patient_folder, series_uid)
        if series_folder is None:
            print(f"  [WARN] Series not found for {patient_id} / {series_uid}")
            rows.append(base)
            continue

        dcm_files = sorted(series_folder.glob("*.dcm"))
        variables = extract_acquisition_variables(dcm_files[0])
        rows.append({**base, **variables})
        print(f"  [{i}/{len(df)}] OK  {patient_id} — {series_folder.name}")

    pd.DataFrame(rows).to_csv(output_csv, index=False)
    print(f"\nSaved {len(rows)} rows -> {output_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract DICOM acquisition variables for each CSV entry."
    )
    parser.add_argument("csv_path", type=Path, help="Path to the analysis CSV file.")
    parser.add_argument(
        "dicom_root",
        type=Path,
        help="Root folder containing TCGA-KIRC/KIRP/KICH subfolders.",
    )
    parser.add_argument("output_csv", type=Path, help="Path to write the output CSV.")
    args = parser.parse_args()
    extract(args.csv_path, args.dicom_root, args.output_csv)


if __name__ == "__main__":
    main()
