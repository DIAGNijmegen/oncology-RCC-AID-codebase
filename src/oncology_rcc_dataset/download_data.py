"""CLI to download the RCC dataset from Hugging Face."""

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

# TODO: Replace with the actual Hugging Face dataset repository ID, e.g. "username/rcc-dataset"
HF_DATASET_ID = "PLACEHOLDER/oncology-rcc-dataset"


def download(output_folder: Path) -> None:
    output_folder.mkdir(parents=True, exist_ok=True)

    print(f"Downloading '{HF_DATASET_ID}' from Hugging Face...")
    snapshot_download(
        repo_id=HF_DATASET_ID,
        repo_type="dataset",
        local_dir=str(output_folder),
    )
    print(f"Download complete -> {output_folder}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the RCC dataset from Hugging Face."
    )
    parser.add_argument(
        "output_folder",
        type=Path,
        help="Directory where the downloaded data will be saved.",
    )
    args = parser.parse_args()
    download(args.output_folder)


if __name__ == "__main__":
    main()
