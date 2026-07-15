from __future__ import annotations

import csv
from pathlib import Path


def read_sample_csv(sample_path, template_row_index):
    path = Path(sample_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file mẫu: {path}")
    with path.open("r", encoding="utf-16", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
        headers = reader.fieldnames or []
    if not headers:
        raise RuntimeError("File mẫu không có header")
    if not rows:
        return headers, {}
    index = min(max(template_row_index, 0), len(rows) - 1)
    return headers, dict(rows[index])


def read_sample_rows(sample_path):
    path = Path(sample_path)
    with path.open("r", encoding="utf-16", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return reader.fieldnames or [], list(reader)


def write_facebook_csv(output_path, headers, rows):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-16", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=headers,
            delimiter="\t",
            quoting=csv.QUOTE_MINIMAL,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return output.resolve()
