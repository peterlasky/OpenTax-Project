"""
Download IRS forms, instructions, publications, and information returns from a YAML file.
Saves into forms/, instructions/, publications/, and information-returns/ subfolders.
Skips files that already exist. Information returns (W-2, 1099s, 1098s) have no instructions.
"""
from pathlib import Path
from urllib.request import urlretrieve
from urllib.parse import urlparse
import yaml


SECTION_FOLDERS = {
    "forms": "forms",
    "instructions": "instructions",
    "publications": "publications",
    "information_returns": "information-returns",
}


def download_section(base_dir: Path, section_name: str, items: dict) -> None:
    """Download all items in a section into its subfolder. Skip existing files."""
    if not items:
        return
    folder = base_dir / SECTION_FOLDERS[section_name]
    folder.mkdir(parents=True, exist_ok=True)

    for name, url in items.items():
        filename = Path(urlparse(url).path).name
        dest = folder / filename

        if dest.exists():
            print(f"Skip (exists): [{section_name}] {name} -> {filename}")
            continue

        try:
            urlretrieve(url, dest)
            print(f"Downloaded: [{section_name}] {name} -> {filename}")
        except OSError as e:
            print(f"Error downloading {name}: {e}")


def main():
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "forms-instructions-and-publications"
    yaml_path = data_dir / "IRS_Federal_Individual_2025.yaml"

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        print("No data found in YAML.")
        return

    # Normalize section keys (YAML may have "Forms" vs "forms")
    for section_key, folder_name in SECTION_FOLDERS.items():
        # Match common capitalizations
        for key in (section_key, section_key.capitalize(), section_key.title()):
            if key in data and data[key]:
                download_section(data_dir, section_key, data[key])
                break


if __name__ == "__main__":
    main()
