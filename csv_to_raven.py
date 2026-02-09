"""
Convert whistle detection CSV files to Raven selection table format.

Usage:
    python csv_to_raven.py <input_folder> [--duration SECONDS]

This script converts all CSV files in the specified folder to Raven-compatible
selection table files (.Table1.selection.txt).
"""

import os
import sys
import csv
import argparse


def write_raven_file(output_path, rows, filename, start_time_offset=0, duration=2.0):
    """
    Write a Raven selection table file for a single audio file.

    Args:
        output_path: Path to the output Raven selection table file
        rows: List of row dictionaries for this file
        filename: The audio filename for Begin File column
        start_time_offset: Time offset in seconds to adjust start time of detections
        duration: Duration in seconds for each selection box (default: 1.0)
    """
    # Raven header columns
    header = [
        "Selection",
        "View",
        "Channel",
        "Begin Time (s)",
        "End Time (s)",
        "Low Freq (Hz)",
        "High Freq (Hz)",
        "Begin File",
        "confidence",
        "Sound type"
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        # Write header (tab-separated)
        f.write('\t'.join(header) + '\n')

        # Write data rows
        for i, row in enumerate(rows, start=1):
            begin_time = float(row['time_offset'])+start_time_offset
            end_time = begin_time + duration

            raven_row = [
                str(i),                          # Selection
                "Spectrogram 1",                 # View
                "1",                             # Channel
                f"{begin_time:.6f}",             # Begin Time (s)
                f"{end_time:.6f}",               # End Time (s)
                "0",                             # Low Freq (Hz)
                "22000",                         # High Freq (Hz)
                filename,                        # Begin File
                row['confidence'],               # confidence
                "Dolphin_whistles"               # Sound type
            ]
            f.write('\t'.join(raven_row) + '\n')

    print(f"    Created: {os.path.basename(output_path)} ({len(rows)} selections)")


def csv_to_raven(csv_path, output_folder, duration=1.0):
    """
    Convert a single CSV file to multiple Raven selection table files (one per unique filename).

    Args:
        csv_path: Path to the input CSV file
        output_folder: Path to folder where output files will be written
        duration: Duration in seconds for each selection box (default: 1.0)
    """
    # Determine prefix from CSV filename (whistle_detections_ or whistle_all_)
    csv_basename = os.path.basename(csv_path)
    if csv_basename.startswith("whistle_detections_"):
        prefix = "whistle_detections_"
    elif csv_basename.startswith("whistle_all_"):
        prefix = "whistle_all_"
    else:
        # Fallback: use the CSV name without extension
        prefix = os.path.splitext(csv_basename)[0] + "_"

    # Read all rows and group by filename
    rows_by_file = {}
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['filename']
            if filename not in rows_by_file:
                rows_by_file[filename] = []
            rows_by_file[filename].append(row)

    if not rows_by_file:
        print(f"  Skipping {csv_path}: no data rows found")
        return

    print(f"  Found {len(rows_by_file)} unique file(s)")

    # Create one Raven file per unique filename
    for filename, rows in rows_by_file.items():
        # Output filename: prefix + filename + .Table1.selection.txt
        output_name = f"{prefix}{filename}.Table1.selection.txt"
        output_path = os.path.join(output_folder, output_name)
        write_raven_file(output_path, rows, filename, duration)


def convert_folder(input_folder, duration=1.0):
    """
    Convert all CSV files in the specified folder to Raven selection tables.

    Args:
        input_folder: Path to folder containing CSV files
        duration: Duration in seconds for each selection box (default: 1.0)
    """
    if not os.path.isdir(input_folder):
        print(f"Error: '{input_folder}' is not a valid directory")
        sys.exit(1)

    csv_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.csv')]

    if not csv_files:
        print(f"No CSV files found in '{input_folder}'")
        return

    print(f"Found {len(csv_files)} CSV file(s) in '{input_folder}'")

    for csv_file in csv_files:
        csv_path = os.path.join(input_folder, csv_file)
        print(f"Converting: {csv_file}")
        csv_to_raven(csv_path, input_folder, duration)

    print("Done!")


def main():
    parser = argparse.ArgumentParser(
        description="Convert whistle detection CSV files to Raven selection table format."
    )
    parser.add_argument(
        "input_folder",
        help="Path to folder containing CSV files to convert"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=1.0,
        help="Duration in seconds for each selection box (default: 1.0)"
    )

    args = parser.parse_args()
    convert_folder(args.input_folder, args.duration)


if __name__ == "__main__":
    main()
