"""
sync_html.py - Sync Python logic from csv_to_raven.py into index.html.

Extracts two pieces from csv_to_raven.py:
  - RAVEN_HEADER constant
  - _build_raven_rows() function (the code between # SYNC_START and # SYNC_END)

Wraps them in a browser-compatible boilerplate (csv_to_raven_browser uses
io.StringIO instead of writing to disk) and injects the result into index.html
between the // PYTHON_START and // PYTHON_END markers.

Run this script whenever csv_to_raven.py is updated:
    python sync_html.py
"""

import re
import os

PY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csv_to_raven.py')
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')

# Browser wrapper template.  Placeholders <<RAVEN_HEADER>> and <<SYNC_BLOCK>> are
# replaced at runtime with the extracted content from csv_to_raven.py.
#
# Important: this is a raw string so backslashes are literal.  When injected into
# the JS template literal in index.html, the JS engine converts \\t -> \t and
# \\n -> \n, giving the Python code the correct escape sequences at runtime.
BROWSER_WRAPPER = r'''import csv
import io
import statistics
from collections import defaultdict

<<RAVEN_HEADER>>

<<SYNC_BLOCK>>

def csv_to_raven_browser(csv_content, csv_filename, duration, start_time_offset,
                          first_seconds_to_ignore, merge_overlapped_detections,
                          merge_confidence_operation):
    """Convert CSV content to Raven selection table strings (browser version).

    Browser-adapted version of csv_to_raven(): accepts CSV as a string and returns
    a list of (output_filename, content, num_selections) tuples instead of writing
    to disk.

    Args:
        csv_content: CSV file content as a string.
        csv_filename: Original CSV filename (used to determine the output prefix).
        duration: Duration in seconds of each detection box.
        start_time_offset: Offset (s) added to every detection's time_offset.
        first_seconds_to_ignore: Drop detections with time_offset below this value.
        merge_overlapped_detections: If True, merge overlapping detections.
        merge_confidence_operation: 'mean', 'max', or 'median'.

    Returns:
        List of (output_filename, content_string, num_selections) tuples.
    """
    if csv_filename.startswith("whistle_detections_"):
        prefix = "whistle_detections_"
    elif csv_filename.startswith("whistle_all_"):
        prefix = "whistle_all_"
    else:
        prefix = csv_filename.rsplit('.', 1)[0] + "_"

    rows_by_file = defaultdict(list)
    reader = csv.DictReader(io.StringIO(csv_content))
    for row in reader:
        rows_by_file[row['filename']].append(row)

    if not rows_by_file:
        return []

    results = []
    for audio_filename, rows in rows_by_file.items():
        rows = _build_raven_rows(rows, duration, start_time_offset,
                                  first_seconds_to_ignore,
                                  merge_overlapped_detections,
                                  merge_confidence_operation)
        output = io.StringIO()
        output.write('\\t'.join(RAVEN_HEADER) + '\\n')
        for i, row in enumerate(rows, start=1):
            raven_row = [
                str(i),
                "Spectrogram 1",
                "1",
                f"{row['begin_time']:.6f}",
                f"{row['end_time']:.6f}",
                "0",
                "22000",
                audio_filename,
                row['confidence'],
                "", "", "", ""
            ]
            output.write('\\t'.join(raven_row) + '\\n')
        output_name = f"{prefix}{audio_filename}.Table1.selection.txt"
        results.append((output_name, output.getvalue(), len(rows)))

    return results'''


def extract_raven_header(py_source):
    """Extract the RAVEN_HEADER list definition from csv_to_raven.py."""
    match = re.search(r'(RAVEN_HEADER\s*=\s*\[.*?\])', py_source, re.DOTALL)
    if not match:
        raise ValueError("RAVEN_HEADER not found in csv_to_raven.py")
    return match.group(1).strip()


def extract_sync_block(py_source):
    """Extract the code between # SYNC_START and # SYNC_END from csv_to_raven.py."""
    match = re.search(r'# SYNC_START\n(.*?)\n# SYNC_END', py_source, re.DOTALL)
    if not match:
        raise ValueError("# SYNC_START / # SYNC_END markers not found in csv_to_raven.py")
    return match.group(1).strip()


def inject_into_html(html_source, browser_python):
    """Replace the block between // PYTHON_START and // PYTHON_END in index.html."""
    marker_pattern = re.compile(
        r'([ \t]*// PYTHON_START\n).*?([ \t]*// PYTHON_END)',
        re.DOTALL
    )

    def replacement(m):
        indent = '                '  # 16 spaces — matches the surrounding JS indentation
        indented = '\n'.join(
            (indent + line) if line.strip() else ''
            for line in browser_python.splitlines()
        )
        return (
            m.group(1) +
            indent + 'await pyodide.runPythonAsync(`\n' +
            indented + '\n' +
            indent + '`);\n' +
            m.group(2)
        )

    new_html, count = marker_pattern.subn(replacement, html_source)
    if count == 0:
        raise ValueError("// PYTHON_START / // PYTHON_END markers not found in index.html")
    return new_html


def main():
    with open(PY_FILE, 'r', encoding='utf-8') as f:
        py_source = f.read()
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_source = f.read()

    raven_header = extract_raven_header(py_source)
    sync_block = extract_sync_block(py_source)

    browser_python = (
        BROWSER_WRAPPER
        .replace('<<RAVEN_HEADER>>', raven_header)
        .replace('<<SYNC_BLOCK>>', sync_block)
    )

    new_html = inject_into_html(html_source, browser_python)

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print("index.html updated successfully.")
    print(f"  Synced RAVEN_HEADER ({len(raven_header.splitlines())} lines)")
    print(f"  Synced _build_raven_rows ({len(sync_block.splitlines())} lines)")


if __name__ == '__main__':
    main()
