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

## Custom Tab Names

You can customize the names of tabs using the optional `tabs_names` parameter. This allows you to provide more user-friendly names instead of using the default names derived from notebook filenames.

### Flat Structure with Custom Tab Names

```json
{
  "notebook_files": [
    "test_notebooks/data_analysis/sales_analysis.ipynb",
    "test_notebooks/machine_learning/model_performance.ipynb",
    "test_notebooks/visualization/dashboard.ipynb"
  ],
  "tabs_names": [
    "Sales Report",
    "ML Performance",
    "Custom Dashboard"
  ],
  "output_folder": "./test_output/tabs_names_flat",
  "report_title": "Flat Structure with Custom Tab Names",
  "execute": false
}
```

In flat structure, `tabs_names` should be a list where each element corresponds to a notebook file by index. If you provide fewer names than notebooks, the remaining tabs will use default names.

### Nested Structure with Custom Notebook Names

```json
{
  "notebook_files": {
    "Language Tests": [
      "test_notebooks/hebrew_arabic_test.ipynb"
    ],
    "Data Analysis": [
      "test_notebooks/data_analysis/sales_analysis.ipynb"
    ],
    "Machine Learning": [
      "test_notebooks/machine_learning/model_performance.ipynb"
    ]
  },
  "tabs_names": {
    "Language Tests": ["Hebrew & Arabic Testing"],
    "Data Analysis": ["Sales Performance Report"],
    "Machine Learning": ["Model Evaluation Results"]
  },
  "output_folder": "./test_output/tabs_names_nested_simple",
  "report_title": "Nested Structure with Simple Custom Tab Names",
  "execute": false
}
```

In nested structure, `tabs_names` is a dictionary where each key matches a topic from `notebook_files`. The values are lists of custom names for the notebooks within that topic. Topic names remain unchanged in this format.

### Nested Structure with Custom Topic and Notebook Names

```json
{
  "notebook_files": {
    "Language Tests": [
      "test_notebooks/hebrew_arabic_test.ipynb"
    ],
    "Data Analysis": [
      "test_notebooks/data_analysis/sales_analysis.ipynb"
    ],
    "Machine Learning": [
      "test_notebooks/machine_learning/model_performance.ipynb"
    ]
  },
  "tabs_names": {
    "Language Tests": {
      "topic_name": "Language Testing Suite",
      "notebook_names": ["Hebrew & Arabic Testing"]
    },
    "Data Analysis": {
      "topic_name": "Data Analytics",
      "notebook_names": ["Sales Performance Report"]
    },
    "Machine Learning": {
      "topic_name": "ML Models",
      "notebook_names": ["Model Evaluation Results"]
    }
  },
  "output_folder": "./test_output/tabs_names_nested",
  "report_title": "Nested Structure with Custom Tab Names",
  "execute": false
}
```

For maximum customization, you can provide both custom topic names and notebook names using the advanced format with `topic_name` and `notebook_names` properties.

### Partial Custom Names with Fallback

```json
{
  "notebook_files": [
    "test_notebooks/data_analysis/sales_analysis.ipynb",
    "test_notebooks/machine_learning/model_performance.ipynb",
    "test_notebooks/visualization/dashboard.ipynb",
    "test_notebooks/statistics_report.ipynb"
  ],
  "tabs_names": [
    "Sales Report",
    "ML Performance"
  ],
  "output_folder": "./test_output/tabs_names_partial",
  "report_title": "Partial Tab Names Test",
  "execute": false
}
```

If you provide fewer custom names than notebooks, the system gracefully falls back to default naming for the remaining tabs. In this example, the first two tabs will be "Sales Report" and "ML Performance", while the remaining tabs will use default names like "Dashboard" and "Statistics report".

### Single Notebook (No Effect)

For single notebook configurations, the `tabs_names` parameter has no effect since there are no tabs to customize. The report title comes from the `report_title` configuration.

## Usage

```python
from tabs_report.tabs_report_generator import generate_report

# Generate report using a config file
generate_report("path/to/config.json")
```
