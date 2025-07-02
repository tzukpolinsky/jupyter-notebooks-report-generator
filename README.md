# Jupyter Notebooks Report Generator

A tool for generating HTML reports from Jupyter notebooks in python. It converts multiple notebooks into a single HTML report with a tabbed interface, making it easy to organize and present multiple analyses. The tool supports both flat and nested tab structures, allowing for hierarchical organization of notebooks.

## Configuration Examples

### Nested Structure (Categories with Notebooks)

```json
{
  "notebook_dir": "",
  "notebook_files": {
    "Category 1": [
      "/path/to/notebook1.ipynb",
      "/path/to/notebook2.ipynb"
    ],
    "Category 2": [
      "/path/to/notebook3.ipynb",
      "/path/to/notebook4.ipynb"
    ]
  },
  "output_folder": "/path/to/output",
  "report_title": "My Analysis Report"
}
```

This configuration creates a two-level tab structure with categories as the top level and individual notebooks as the second level.

If there is no subdirs in the root dir given in the notebook_dir attribute, then it creates a flat structure instead

### Flat Structure (Simple List of Notebooks)

```json
{
  "notebook_dir": "",
  "notebook_files": [
    "/path/to/notebook1.ipynb",
    "/path/to/notebook2.ipynb",
    "/path/to/notebook3.ipynb"
  ],
  "output_folder": "/path/to/output",
  "report_title": "My Analysis Report"
}
```

This configuration creates a simple tab structure with all notebooks at the same level.

### Single Notebook

```json
{
  "notebook_dir": "",
  "notebook_files": "/path/to/notebook.ipynb",
  "output_folder": "/path/to/output",
  "report_title": "My Analysis Report"
}
```

This configuration creates a simple HTML report with a single notebook, without any tabs. It preserves the same qualities as the nested and flat reports, including title, generation date, and the design that prevents side scrolling.

### Using a Directory of Notebooks

```json
{
  "notebook_dir": "/path/to/notebooks/directory",
  "notebook_files": [],
  "output_folder": "/path/to/output",
  "report_title": "My Analysis Report"
}
```

This configuration will use all `.ipynb` files found in the specified directory.

### Automatic Nested Structure from Directory Tree

```json
{
  "notebook_dir": "/path/to/notebooks/directory",
  "notebook_files": {},
  "output_folder": "/path/to/output",
  "report_title": "My Analysis Report",
  "execute": true
}
```

This configuration automatically creates a nested structure based on the subdirectories in the notebook_dir. Each subdirectory becomes a category, and the notebooks within each subdirectory are grouped under that category. Notebooks in the root directory are placed in a "Main" category.

## Notebook Execution

You can optionally execute notebooks before converting them to HTML by adding the `execute` option to your configuration:

```json
{
  "execute": true
}
```

When `execute` is set to `true`, the tool will:
1. Run all cells in each notebook before converting to HTML
2. Set a timeout of 600 seconds per cell to prevent hanging on problematic cells
3. Continue execution even if some cells fail (using the `--allow-errors` flag)
4. If execution fails completely (e.g., due to missing dependencies), fall back to converting without execution
5. Provide detailed error messages to help diagnose issues

This feature is useful for ensuring that your report contains the latest outputs from your notebooks. If a notebook requires packages that aren't available in your environment, the tool will gracefully handle the error and still include the notebook in the report (without execution).

## Usage

```python
from tabs_report.tabs_report_generator import generate_report

# Generate report using a config file
generate_report("path/to/config.json")
```
