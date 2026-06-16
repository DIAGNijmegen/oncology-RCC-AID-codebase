"""
Presample Data before running segmentation and manual annotation

Input: series-data.csv
Output: reduced series-data.csv

The input file can be downloaded via TCGA: https://nbia.cancerimagingarchive.net/nbia-search/?CollectionCriteria=TCGA-KICH
Use the selection: Collections(TCGA-KIRP, TCGA-KICH, TCGA-KIRC ) ANDImage Modality(CT )
"""

import sys

import pandas as pd


def main(data_path: str):

    orig_meta = pd.read_csv(data_path)
    print("Original metadata entries:", len(orig_meta))
    print("Unique patients:", orig_meta["PatientID"].nunique())
    meta_v1 = orig_meta.copy()

    ####### - Primary Filtering - #######
    # at most 5 mm slice thickness,
    # at least 10 images,
    # valid SeriesDescription,
    # no sagittal/coronal,
    # one seriesdate per study

    print("-" * 15 + " Primary Filtering " + "-" * 15)

    # keep only first series date per study
    meta_v1["SeriesDate"] = meta_v1["SeriesDate"].apply(
        lambda x: x if pd.notna(x) else "11-14-2025"
    )  # assign a future date to missing dates for filtering

    studies = meta_v1["StudyInstanceUID"].unique().tolist()
    to_remove = []
    for study in studies:
        study_series = meta_v1[meta_v1["StudyInstanceUID"] == study]
        series_dates = study_series["SeriesDate"].unique().tolist()
        if len(series_dates) > 1:
            # keep only the first date (format MM-DD-YYYY)
            first_date = min(series_dates, key=lambda d: pd.to_datetime(d, format="%m-%d-%Y"))
            to_remove.extend(study_series[study_series["SeriesDate"] != first_date].index.tolist())

    meta_v1 = meta_v1.drop(index=to_remove)
    print("After keeping only first SeriesDate per study:", len(meta_v1))

    # remove entries without SeriesDescription or slice thickness
    # Convert SliceThickness to float
    def convert_slice_thickness(x):
        try:
            return float(x)
        except Exception:
            try:
                return float(x.split(", ")[1])  # use max if range given
            except Exception:
                return float("nan")

    meta_v1["SliceThickness(mm)"] = meta_v1["SliceThickness(mm)"].apply(convert_slice_thickness)
    meta_v1 = meta_v1.dropna(subset=["SeriesDescription", "SliceThickness(mm)"])
    print("After removing entries without SeriesDescription or SliceThickness:", len(meta_v1))

    # remove entries with slice thickness > 5 mm
    meta_v1 = meta_v1[meta_v1["SliceThickness(mm)"] <= 5.0]
    print("After removing entries with SliceThickness > 5 mm:", len(meta_v1))

    # remove series with less than 10 images
    meta_v1 = meta_v1[meta_v1["ImageCount"] >= 10]
    print("After removing series with less than 10 images:", len(meta_v1))

    # remove sagittal/coronal series
    mask_orient = meta_v1["SeriesDescription"].str.contains(
        r"sag|cor", case=False, regex=True, na=False
    )
    meta_v1 = meta_v1[~mask_orient]
    print("After removing sagittal/coronal series:", len(meta_v1))

    ########### - Secondary Filtering - #######
    # if multiple series of a study have the same series description,
    # keep only the one with (1) the smalles slice thickness or (2) the highest image count
    print("\n" + "-" * 15 + " Secondary Filtering " + "-" * 15)
    meta_v2 = meta_v1.copy()
    to_remove = []
    studies = meta_v2["StudyInstanceUID"].unique().tolist()
    for study in studies:
        study_series = meta_v2[meta_v2["StudyInstanceUID"] == study]
        series_descs = study_series["SeriesDescription"].unique().tolist()
        for desc in series_descs:
            desc_series = study_series[study_series["SeriesDescription"] == desc]
            if len(desc_series) > 1:
                # find the series with the smallest slice thickness
                min_thickness = desc_series["SliceThickness(mm)"].min()
                candidates = desc_series[desc_series["SliceThickness(mm)"] == min_thickness]
                if len(candidates) > 1:
                    # if multiple, select the one with the highest image count
                    max_images = candidates["ImageCount"].max()
                    final_choice = candidates[candidates["ImageCount"] == max_images].iloc[0]
                else:
                    final_choice = candidates.iloc[0]
                # mark all other series for removal
                to_remove.extend(
                    desc_series[
                        desc_series["SeriesInstanceUID"] != final_choice["SeriesInstanceUID"]
                    ].index.tolist()
                )
    meta_v2 = meta_v2.drop(index=to_remove)
    print("After removing duplicate series descriptions:", len(meta_v2))

    ########### - Tertiary Filtering - #######
    print("\n" + "-" * 15 + " Tertiary Filtering " + "-" * 15)
    meta = meta_v2.copy()

    # remove scout images and reconstructions
    recon_keywords = [
        # explicit recon labels
        r"\brecon(?:\s*\d+)?\b",
        r"reconstruction",
        r"Reformatted"
        # reformatted or projection types
        r"\bmip\b",
        r"\bmpr\b",
        r"3d",
        r"\bvr\b",
        r"volume",
        r"sag",
        r"cor",
        r"axial mips?",
        # windowed/leveled images
        r"wl/ww",
        r"window level",
        r"window/level",
        r"lung",
        r"bone",
        r"soft tissue",
        # scouts and misc utilities
        r"localizer",
        r"scout",
        r"smart prep",
        r"pseudo",
        # weird DICOM export artifacts
        r"<mpr",
        r"bind\(",
        r"range",
        r"movie",
    ]
    mask_recon = meta["SeriesDescription"].str.contains(
        "|".join(recon_keywords), case=False, regex=True, na=False
    )
    meta = meta[~mask_recon]
    print("After recon/scout removal:", len(meta))

    # check if we completely removed any studies/patients and restore if so
    # (keep at least one series per study)
    difference = meta_v2["StudyInstanceUID"].unique().tolist()
    difference = set(difference) - set(meta["StudyInstanceUID"].unique().tolist())
    print("Missing studies after recon/scout removal:", len(difference))

    # select the series with the highest image count per study to restore
    diff_df = meta_v2[meta_v2["StudyInstanceUID"].isin(difference)]
    diff_df = diff_df.sort_values("ImageCount", ascending=False).drop_duplicates(
        subset=["StudyInstanceUID"], keep="first"
    )
    meta = pd.concat([meta, diff_df], ignore_index=True)
    print("After restoring missing studies:", len(meta))

    # # remove duplicated series ids (patients can have multiple phases/scans for the same series)
    meta = meta.drop_duplicates(subset=["SeriesInstanceUID"], keep="first")
    meta = meta.sort_values(["StudyInstanceUID"])
    meta = meta.reset_index(drop=True)
    print("After removing duplicates:", len(meta))
    print("Unique patients:", meta["PatientID"].nunique())

    meta.to_csv("presampled_data.csv", index=False)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise Exception("Function requires path to data csv as input")

    main(sys.argv[1])
