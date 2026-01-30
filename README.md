# whistleAnalyzer_tools

Tools to convert detections from whistleAnalyzer (D. Mann) to Raven selection tables.

## Live Web App

**Use the converter directly in your browser (no installation required):**

https://xaviermouy.github.io/whistleAnalyzer_tools/

The HTML file can also be [downloaded](index.html) and used offline - just open it in any modern browser.

## Features

- Converts CSV files to Raven Pro selection table format
- Creates one Raven file per unique audio file found in the CSV
- Works entirely in the browser (no server needed)
- Can be used offline after first load

## Output Format

The converter maps CSV fields to Raven columns as follows:

| CSV Field | Raven Column |
|-----------|--------------|
| `filename` | `Begin File` |
| `time_offset` | `Begin Time (s)` |
| `time_offset + 1` | `End Time (s)` |
| `confidence` | `confidence` |

Fixed values:
- `Sound type`: Dolphin_whistles
- `High Freq (Hz)`: 22000
- `Low Freq (Hz)`: 0
- `Channel`: 1

## Command Line Script

For batch processing, use the Python script directly:

### Requirements

- Python 3.6+

### Usage

```bash
python csv_to_raven.py <input_folder>
```

### Example

```bash
python csv_to_raven.py ./output
```

This will convert all CSV files in the `./output` folder and create Raven selection table files in the same folder.

### Output Naming

Output files are named based on the source CSV and audio filename:
- `whistle_detections_<audio_filename>.Table1.selection.txt`
- `whistle_all_<audio_filename>.Table1.selection.txt`
