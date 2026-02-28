# whistleAnalyzer_tools

Tools to convert detections from whistleAnalyzer (D. Mann) to Raven selection tables.

## Live Web App

**Use the converter directly in your browser (no installation required):**

https://xaviermouy.github.io/whistleAnalyzer_tools/

The HTML file can also be [downloaded](index.html) and used offline - just open it in any modern browser.

## Features

- Converts whistleAnalyzer CSV files to Raven Pro selection table format
- Creates one Raven file per unique audio file found in the CSV
- Configurable selection duration and start time offset
- Optional filtering of detections at the beginning of each recording (e.g. to skip SoundTrap calibration tones)
- Optional merging of overlapping detections, with configurable confidence combination (mean, max, or median)
- Works entirely in the browser (no server needed) and can be used offline after first load
- Also available as a command-line script for batch processing

## Output Format

Each output file is a tab-separated Raven selection table with the following columns:

| Raven Column | Value |
|---|---|
| `Selection` | Sequential detection number |
| `View` | `Spectrogram 1` |
| `Channel` | `1` |
| `Begin Time (s)` | `time_offset + start_time_offset` |
| `End Time (s)` | `Begin Time + duration` |
| `Low Freq (Hz)` | `0` |
| `High Freq (Hz)` | `22000` |
| `Begin File` | Audio filename from the CSV `filename` column |
| `Confidence` | Detection confidence score |
| `TP` | *(empty, for manual annotation)* |
| `FP` | *(empty, for manual annotation)* |
| `FN` | *(empty, for manual annotation)* |
| `Comments` | *(empty, for manual annotation)* |

Output files are named based on the source CSV prefix and audio filename:
- `whistle_detections_<audio_filename>.Table1.selection.txt`
- `whistle_all_<audio_filename>.Table1.selection.txt`

## Command-Line Script

For batch processing, use `csv_to_raven.py` directly.

### Requirements

- Python 3.6+

### Usage

```bash
python csv_to_raven.py [input_folder] [options]
```

`input_folder` is optional when running interactively — the script defaults to the `data_samples` folder when omitted.

### Options

| Argument | Description | Default |
|---|---|---|
| `input_folder` | Path to folder containing CSV files to convert | `data_samples/` |
| `--duration` | Duration in seconds of each selection box | `1.0` |
| `--start_time_offset` | Offset in seconds added to the start time of each detection | `0` |
| `--first_seconds_to_ignore` | Drop detections whose `time_offset` is less than this value (seconds). Useful to skip SoundTrap calibration tones. | `0` |
| `--merge_overlapped_detections` | Merge consecutive detections that overlap in time (`True`/`False`) | `False` |
| `--merge_confidence_operation` | How to combine confidence when merging: `mean`, `max`, or `median` | `mean` |

### Examples

```bash
# Basic usage — convert all CSV files in a folder
python csv_to_raven.py ./my_detections

# Custom selection duration
python csv_to_raven.py ./my_detections --duration 2.0

# Shift start times and ignore the first 10 seconds of each recording
python csv_to_raven.py ./my_detections --start_time_offset 0.5 --first_seconds_to_ignore 10

# Merge overlapping detections and use the max confidence
python csv_to_raven.py ./my_detections --merge_overlapped_detections True --merge_confidence_operation max
```

## Keeping index.html in Sync

The browser tool (`index.html`) embeds the same processing logic as `csv_to_raven.py`. After modifying `csv_to_raven.py`, run the sync script to update `index.html` automatically:

```bash
python sync_html.py
```

This extracts `RAVEN_HEADER` and `_build_raven_rows()` (the code between the `# SYNC_START` / `# SYNC_END` markers in `csv_to_raven.py`) and injects them into `index.html` between the `// PYTHON_START` / `// PYTHON_END` markers.
