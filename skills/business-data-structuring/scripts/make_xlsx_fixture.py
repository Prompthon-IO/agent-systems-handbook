#!/usr/bin/env python3
"""Create a values-only XLSX from the bundled synthetic CSV; refuse overwrites."""
import argparse
import csv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output file; never overwrite an existing workbook.")
    import openpyxl
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Demo Pipeline"
    with (Path(__file__).resolve().parents[1] / "examples/messy-pipeline.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            sheet.append(row)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for col in "ABCDEFG":
        sheet.column_dimensions[col].width = 24
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as output:
        book.save(output)
    book.close()
    print(args.output)


if __name__ == "__main__":
    main()
