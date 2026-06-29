#!/usr/bin/env python3
"""
Export one representative product row per unique category hierarchy path.

The category column, the hierarchy depth, and the delimiters are all detected
dynamically from the data — nothing about the structure is hardcoded, so this
works regardless of how many category levels the file contains.

Detected convention (WooCommerce-style export):
  * Hierarchy levels are joined by  " > "  (space-greater-space)
        e.g.  "Fabrics > Jacquard > Solution Dyed Acrylic 800"
  * A product assigned to several categories joins them with ","
  * Depth is variable (paths may have any number of levels)

Usage:
    python3 export_category_samples.py [INPUT_CSV] [OUTPUT_CSV]

Defaults:
    INPUT_CSV  = all_products.csv   (falls back to products.csv if present)
    OUTPUT_CSV = products_sample.csv
"""

import csv
import os
import sys
from collections import OrderedDict

# Delimiters of the hierarchical convention.
LEVEL_SEP = " > "      # separates levels within one path
MULTI_SEP = ","        # separates multiple paths assigned to one product

# A column "participates in the category structure" if at least this fraction
# of its non-empty values look like a hierarchy path (contain LEVEL_SEP).
HIERARCHY_THRESHOLD = 0.30


def split_paths(cell):
    """Split a category cell into individual, cleaned hierarchy paths."""
    paths = []
    for raw in cell.split(MULTI_SEP):
        path = raw.strip()
        if path:
            # Normalise internal whitespace around the level separator.
            levels = [lvl.strip() for lvl in path.split(LEVEL_SEP)]
            paths.append(LEVEL_SEP.join(levels))
    return paths


def detect_category_columns(rows, fieldnames):
    """Return columns whose values follow the ' > ' hierarchy convention."""
    detected = []
    for col in fieldnames:
        non_empty = 0
        hierarchical = 0
        for row in rows:
            val = (row.get(col) or "").strip()
            if not val:
                continue
            non_empty += 1
            # A real path has the ' > ' separator and no line breaks
            # (free-text Meta fields may contain a stray '>' but not ' > ').
            if LEVEL_SEP in val and "\n" not in val:
                hierarchical += 1
        if non_empty and hierarchical / non_empty >= HIERARCHY_THRESHOLD:
            detected.append((col, hierarchical, non_empty))
    return detected


def pick_primary(detected):
    """Choose the primary category column (prefer one named 'categor*')."""
    for col, _, _ in detected:
        if "categor" in col.lower():
            return col
    return detected[0][0] if detected else None


def main():
    infile = sys.argv[1] if len(sys.argv) > 1 else None
    if infile is None:
        infile = "all_products.csv" if os.path.exists("all_products.csv") else "products.csv"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "products_sample.csv"

    if not os.path.exists(infile):
        sys.exit(f"Input file not found: {infile}")

    with open(infile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames:
        sys.exit("Input CSV has no header row.")

    # --- 1. Detect hierarchical columns dynamically ---------------------------
    detected = detect_category_columns(rows, fieldnames)
    if not detected:
        sys.exit("No category-hierarchy column detected (no ' > ' delimited values found).")

    primary = pick_primary(detected)

    print("Columns participating in the category structure:")
    for col, hier, non_empty in detected:
        flag = "  <- primary" if col == primary else ""
        print(f"  {col!r}: {hier}/{non_empty} hierarchical values{flag}")

    # --- 2. Collect one representative row per unique path --------------------
    # OrderedDict preserves first-seen order; key = full category path string.
    representatives = OrderedDict()
    max_depth = 0
    for row in rows:
        cell = (row.get(primary) or "").strip()
        if not cell:
            continue
        for path in split_paths(cell):
            max_depth = max(max_depth, path.count(LEVEL_SEP) + 1)
            if path not in representatives:
                representatives[path] = row

    # --- 3. Write output, preserving every original column -------------------
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in representatives.values():
            writer.writerow(row)

    print()
    print(f"Primary category column : {primary!r}")
    print(f"Maximum hierarchy depth : {max_depth} levels")
    print(f"Unique category paths   : {len(representatives)}")
    print(f"Rows written            : {len(representatives)} -> {outfile}")


if __name__ == "__main__":
    main()
