# Oncology RCC Dataset

A curated dataset of CT scans and segmentation masks for Renal Cell Carcinoma (RCC), combining cases from the TCGA-KIRC, TCGA-KIRP, and TCGA-KICH collections. This repository provides tooling to download the dataset and extract tumor and cyst features for analysis.

## Dataset Summary

| Subtype | Source | Number of cases 
|---|---|---|
Clear Cell RCC | TCGA-KIRC | 95
Papillary RCC | TCGA-KIRP | 29
Chromophobe RCC | TCGA-KICH | 18

### Segmentation label encoding

| Label | Structure |
|---|---|
| 0 | Background |
| 1 | Kidney |
| 2 | Tumor |
| 3 | Cyst |

### Analysis summary

| Metric | Tumor | Cyst |
|---|---|---|
| Total count | 142 | 123 |
| Macro avg size (ml/lesion) | 168.34 | 17.38 |
| Macro avg diameter (mm/lesion) | 55.51 | 21.00 |

## Installation

Requires Python ≥ 3.10.

```bash
pip install -e .
```

## Usage

### 1. Download the dataset

Downloads the dataset from Hugging Face to a local folder:

```bash
download-rcc-data /path/to/output_folder
```

### 2. Run the analysis

Processes all CT scans and segmentation masks, and saves results to a CSV file. Results are written incrementally after each scan:

```bash
analyze-rcc-data /path/to/data_folder /path/to/results.csv
```

### 3. Print a summary

Prints dataset statistics to the command line, including subtype distribution and macro average lesion size and diameter:

```bash
summarize-rcc-data /path/to/results.csv
```

If the CSV does not exist yet, pass `--data-folder` to run the analysis first automatically:

```bash
summarize-rcc-data /path/to/results.csv --data-folder /path/to/data_folder
```

## Citation

If you use this dataset, please cite our paper:

```bibtex
@article{TODO,
  title   = {TODO},
  author  = {TODO},
  journal = {TODO},
  year    = {TODO},
  url     = {TODO}
}
```

The dataset is derived from the following TCGA collections. Please also cite them:

**TCGA-KIRC (Clear Cell RCC)**
```bibtex
@misc{tcga-kirc,
  title  = {TODO},
  author = {TODO},
  url    = {TODO}
}
```

**TCGA-KIRP (Papillary RCC)**
```bibtex
@misc{tcga-kirp,
  title  = {TODO},
  author = {TODO},
  url    = {TODO}
}
```

**TCGA-KICH (Chromophobe RCC)**
```bibtex
@misc{tcga-kich,
  title  = {TODO},
  author = {TODO},
  url    = {TODO}
}
```

## License

This project is licensed under the MIT License. The underlying TCGA data is subject to the [TCGA Data Use Policy](TODO).
