"""
Convert whistle detection CSV files to Raven selection table format.

Usage:
    python csv_to_raven.py [input_folder] [options]

Arguments:
    input_folder                Path to folder containing CSV files to convert.
                                If omitted, defaults to the built-in data_samples folder.

Options:
    --duration SECONDS          Duration in seconds of each detection box (default: 1.0).
    --start_time_offset SECONDS Offset added to the time_offset of every detection, e.g. to
                                account for a fixed delay in the recording (default: 0).
    --first_seconds_to_ignore N Drop detections whose time_offset is less than N seconds.
                                Useful to skip calibration tones at the start of SoundTrap
                                recordings (default: 0, i.e. no detections are dropped).
    --merge_overlapped_detections
                                When set to True, consecutive detections that overlap in time
                                (end time of one >= begin time of the next) are merged into a
                                single detection. Chains of more than two overlapping detections
                                are fully collapsed. The merged detection spans from the earliest
                                begin_time to the latest end_time across the group. Confidence is
                                combined according to --merge_confidence_operation (default: False).
    --merge_confidence_operation
                                How to combine confidence values when merging overlapping
                                detections. Choices: 'mean' (default), 'max', 'median'.

Input CSV format:
    The script accepts CSV files produced by whistleAnalyzer. Expected columns:
        filename      - Name of the audio file the detection belongs to.
        time_offset   - Start time of the detection within the audio file (seconds).
        confidence    - Model confidence score for the detection.
    Files must be named with the prefix 'whistle_detections_' or 'whistle_all_';
    other CSV files are supported but use the base filename as the output prefix.

Output:
    For each unique audio filename found in a CSV, one Raven selection table is written
    to the same folder as the input CSV. Output files are named:
        <prefix><audio_filename>.Table1.selection.txt
    where <prefix> matches the input CSV prefix (e.g. 'whistle_detections_').
"""

import os
import sys
import csv
import argparse
import statistics

RAVEN_HEADER = [
    "Selection",
    "View",
    "Channel",
    "Begin Time (s)",
    "End Time (s)",
    "Low Freq (Hz)",
    "High Freq (Hz)",
    "Begin File",
    "Confidence",
    "TP",
    "FP",
    "FN",
    "Comments",
]


# SYNC_START
def _build_raven_rows(rows, duration, start_time_offset, first_seconds_to_ignore,
                      merge_overlapped_detections, merge_confidence_operation):
    """
    Apply all filters and transforms to a list of detection rows.

    This is the core processing function shared between the CLI script and the
    browser-based tool (index.html). It performs no file I/O.

    Steps (in order):
        1. Drop rows whose time_offset < first_seconds_to_ignore.
        2. Compute begin_time = time_offset + start_time_offset and
           end_time = begin_time + duration for each row.
        3. Optionally merge consecutive overlapping detections.

    Args:
        rows (list[dict]): Detection rows; each must have 'time_offset' and 'confidence'.
        duration (float): Duration (s) of each detection box.
        start_time_offset (float): Offset (s) added to every time_offset.
        first_seconds_to_ignore (float): Drop detections with time_offset below this value.
        merge_overlapped_detections (bool): Merge temporally overlapping detections.
        merge_confidence_operation (str): 'mean', 'max', or 'median'.

    Returns:
        list[dict]: Processed rows, each with 'begin_time' and 'end_time' added.
    """
    # Step 1: drop detections in the ignored leading window
    if first_seconds_to_ignore > 0:
        rows = [row for row in rows if float(row['time_offset']) >= first_seconds_to_ignore]

    # Step 2: compute begin/end times
    for row in rows:
        row['begin_time'] = float(row['time_offset']) + start_time_offset
        row['end_time'] = row['begin_time'] + duration

    # Step 3: merge overlapping detections
    if merge_overlapped_detections and rows:
        def merge_confidence(group):
            values = [float(r['confidence']) for r in group]
            if merge_confidence_operation == 'max':
                return str(max(values))
            elif merge_confidence_operation == 'median':
                return str(statistics.median(values))
            else:  # default: mean
                return str(sum(values) / len(values))

        rows = sorted(rows, key=lambda r: r['begin_time'])
        merged = []
        group = [rows[0]]
        for row in rows[1:]:
            if row['begin_time'] <= group[-1]['end_time']:
                group.append(row)
            else:
                merged_row = dict(group[0])
                merged_row['begin_time'] = group[0]['begin_time']
                merged_row['end_time'] = max(r['end_time'] for r in group)
                merged_row['confidence'] = merge_confidence(group)
                merged.append(merged_row)
                group = [row]
        # Flush last group
        merged_row = dict(group[0])
        merged_row['begin_time'] = group[0]['begin_time']
        merged_row['end_time'] = max(r['end_time'] for r in group)
        merged_row['confidence'] = merge_confidence(group)
        merged.append(merged_row)
        rows = merged

    return rows
# SYNC_END


def write_raven_file(output_path, rows, filename, duration, start_time_offset,
                     first_seconds_to_ignore, merge_overlapped_detections,
                     merge_confidence_operation):
    """
    Write a Raven selection table file for a single audio file.

    Delegates all filtering and transforms to _build_raven_rows(), then writes
    the resulting rows as a tab-separated Raven selection table.

    Args:
        output_path (str): Path to the output Raven selection table file.
        rows (list[dict]): Detection rows for this audio file (from csv.DictReader).
        filename (str): Audio filename written to the 'Begin File' column.
        duration (float): Duration in seconds of each detection box.
        start_time_offset (float): Fixed offset (seconds) added to every time_offset.
        first_seconds_to_ignore (float): Detections with time_offset < this value are dropped.
        merge_overlapped_detections (bool): If True, overlapping detections are merged.
        merge_confidence_operation (str): How to combine confidence when merging:
            'mean', 'max', or 'median'.
    """
    rows = _build_raven_rows(rows, duration, start_time_offset, first_seconds_to_ignore,
                              merge_overlapped_detections, merge_confidence_operation)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        f.write('\t'.join(RAVEN_HEADER) + '\n')
        for i, row in enumerate(rows, start=1):
            raven_row = [
                str(i),                          # Selection
                "Spectrogram 1",                 # View
                "1",                             # Channel
                f"{row['begin_time']:.6f}",      # Begin Time (s)
                f"{row['end_time']:.6f}",        # End Time (s)
                "0",                             # Low Freq (Hz)
                "22000",                         # High Freq (Hz)
                filename,                        # Begin File
                row['confidence'],               # Confidence
                "",                              # TP
                "",                              # FP
                "",                              # FN
                ""                               # Comments
            ]
            f.write('\t'.join(raven_row) + '\n')

    print(f"    Created: {os.path.basename(output_path)} ({len(rows)} selections)")


def csv_to_raven(csv_path, output_folder, duration, start_time_offset, first_seconds_to_ignore,
                 merge_overlapped_detections, merge_confidence_operation):
    """
    Convert a single whistleAnalyzer CSV file to Raven selection table files.

    Rows are grouped by the 'filename' column; one output file is produced per unique
    audio filename. Output files are written to output_folder.

    Args:
        csv_path (str): Path to the input CSV file.
        output_folder (str): Folder where output .Table1.selection.txt files are written.
        duration (float): Duration in seconds of each detection box.
        start_time_offset (float): Fixed offset (seconds) added to every detection's time_offset.
        first_seconds_to_ignore (float): Detections with time_offset < this value are dropped.
        merge_overlapped_detections (bool): If True, temporally overlapping detections are merged.
        merge_confidence_operation (str): How to combine confidence when merging: 'mean', 'max',
            or 'median'.
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
        output_name = f"{prefix}{filename}.Table1.selection.txt"
        output_path = os.path.join(output_folder, output_name)
        write_raven_file(output_path, rows, filename, duration, start_time_offset,
                         first_seconds_to_ignore, merge_overlapped_detections,
                         merge_confidence_operation)


def convert_folder(input_folder, duration=None, start_time_offset=None,
                   first_seconds_to_ignore=None, merge_overlapped_detections=None,
                   merge_confidence_operation=None):
    """
    Convert all whistleAnalyzer CSV files in a folder to Raven selection tables.

    Iterates over every .csv file in input_folder and calls csv_to_raven() for each.
    Output .Table1.selection.txt files are written to the same folder.

    Args:
        input_folder (str): Path to folder containing CSV files.
        duration (float): Duration in seconds of each detection box (default: 1.0).
        start_time_offset (float): Fixed offset (seconds) added to every detection's
            time_offset (default: 0).
        first_seconds_to_ignore (float): Detections with time_offset < this value are
            dropped (default: 0).
        merge_overlapped_detections (bool): If True, temporally overlapping detections
            are merged into a single detection (default: False).
        merge_confidence_operation (str): How to combine confidence when merging:
            'mean', 'max', or 'median' (default: 'mean').
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
        csv_to_raven(csv_path, input_folder, duration, start_time_offset,
                     first_seconds_to_ignore, merge_overlapped_detections,
                     merge_confidence_operation)

    print("Done!")


def main():
    parser = argparse.ArgumentParser(
        description="Convert whistle detection CSV files to Raven selection table format."
    )
    parser.add_argument(
        "input_folder",
        nargs="?",
        default=r"C:\Users\xavier.mouy\Documents\GitHub\whistleAnalyzer_tools\data_samples",
        help="Path to folder containing CSV files to convert"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=1.0,
        help="Duration in seconds of each detection (default: 1.0)"
    )
    parser.add_argument(
        "--start_time_offset",
        type=float,
        default=0,
        help="Offset in seconds of the start time of each detection (default: 0)"
    )
    parser.add_argument(
        "--first_seconds_to_ignore",
        type=float,
        default=0,
        help="Number of seconds at the beginning of each recording to ignore (default: 0). "
             "Mostly used to skip calibration tones from SoundTrap recorders."
    )
    parser.add_argument(
        "--merge_overlapped_detections",
        type=bool,
        default=False,
        help="Merge detections that overlap in time (default: False)."
    )
    parser.add_argument(
        "--merge_confidence_operation",
        type=str,
        default='mean',
        help="How to calculate confidence of merged detections: 'mean', 'max', or 'median' "
             "(default: 'mean')."
    )

    args = parser.parse_args()
    convert_folder(
        args.input_folder,
        duration=args.duration,
        start_time_offset=args.start_time_offset,
        first_seconds_to_ignore=args.first_seconds_to_ignore,
        merge_overlapped_detections=args.merge_overlapped_detections,
        merge_confidence_operation=args.merge_confidence_operation,
    )


if __name__ == "__main__":
    main()
