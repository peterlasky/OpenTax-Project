from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.generic import IndirectObject


def resolve(obj):
    return obj.get_object() if isinstance(obj, IndirectObject) else obj


def count_terminal_fields(field_obj) -> int:
    field_obj = resolve(field_obj)
    kids = field_obj.get("/Kids")

    if not kids:
        return 1

    return sum(count_terminal_fields(kid) for kid in kids)


def inspect_pdf(pdf_path: Path) -> dict[str, Any]:
    try:
        reader = PdfReader(str(pdf_path))
        root = reader.trailer["/Root"]
        acroform = root.get("/AcroForm")

        if acroform is None:
            return {
                "file": str(pdf_path),
                "acroform": False,
                "field_count": 0,
            }

        acroform = resolve(acroform)
        fields = acroform.get("/Fields", [])

        field_count = sum(count_terminal_fields(field) for field in fields)

        return {
            "file": str(pdf_path),
            "acroform": True,
            "field_count": field_count,
        }

    except Exception as e:
        return {
            "file": str(pdf_path),
            "acroform": False,
            "field_count": 0,
            "error": str(e),
        }

def scan_folder(folder_path: str | Path) -> list[dict[str, Any]]:
    folder = Path(folder_path)
    results = []

    for pdf_file in folder.rglob("*.pdf"):
        results.append(inspect_pdf(pdf_file))

    return results


def save_results(folder_path: str | Path, results: list[dict[str, Any]]):
    # Sort: AcroForm=True first, then by field_count (descending), then filename
    results_sorted = sorted(
        results,
        key=lambda x: (
            not x["acroform"],          # False (acroform=True) comes first
            -x["field_count"],          # more fields first
            x["file"].lower(),          # stable ordering
        ),
    )

    output_path = Path(folder_path) / "pdf_form_scan.json"
    with open(output_path, "w") as f:
        json.dump(results_sorted, f, indent=2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python scan_pdfs.py /path/to/folder")
        raise SystemExit(1)

    folder = sys.argv[1]
    results = scan_folder(folder)
    save_results(folder, results)

    print(f"Scanned {len(results)} PDFs. Output saved to pdf_form_scan.json")