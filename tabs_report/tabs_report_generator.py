import os
import glob
from typing import Union

import nbformat
import subprocess
from datetime import datetime
from jinja2 import Template

from misc.config_loader import load_config


def convert_notebooks_to_html(notebook_files: Union[list[str], dict], output_folder: str, postfix: str, execute: bool = False):
    os.makedirs(output_folder, exist_ok=True)
    converted_html_files = []

    for notebook_file in notebook_files:
        notebook_name = os.path.splitext(os.path.basename(notebook_file))[0]
        html_output_path = os.path.join(output_folder, f"{notebook_name}_{postfix}.html")

        # Build nbconvert command
        nbconvert_cmd = ["jupyter", "nbconvert", "--to", "html", "--no-input", "--template", "lab"]

        # Add execute flag if enabled
        if execute:
            nbconvert_cmd.append("--execute")

        # Add output path and notebook file
        nbconvert_cmd.extend(["--output", html_output_path, notebook_file])

        # Run nbconvert command with error handling
        try:
            print(f"Converting notebook: {notebook_file}")
            result = subprocess.run(nbconvert_cmd, check=False, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Warning: Error executing notebook {notebook_file}. Converting without execution.")
                print(f"Error details: {result.stderr}")

                # If execution fails, try again without execution
                if execute:
                    # Remove --execute flag and related options
                    basic_cmd = ["jupyter", "nbconvert", "--to", "html", "--no-input", "--template", "lab",
                                "--output", html_output_path, notebook_file]
                    print("Retrying conversion without execution...")
                    subprocess.run(basic_cmd, check=True)
        except Exception as e:
            print(f"Error converting notebook {notebook_file}: {str(e)}")
            # Continue with next notebook
            continue

        converted_html_files.append(html_output_path)

    return converted_html_files


def _generate_nested_html_template(html_files, report_title, current_datetime):
    """Generate HTML template for nested tabs structure - Lab template compatible."""
    main_tabs = []
    main_contents = []

    for i, (topic_name, topic_html_files) in enumerate(html_files.items()):
        topic_id = f"topic{i}"
        is_active = i == 0

        # Create main tab
        main_tabs.append(
            f'<li class="nav-item"><a class="nav-link {"active" if is_active else ""}" '
            f'id="{topic_id}-tab" data-bs-toggle="tab" href="#{topic_id}" role="tab" '
            f'aria-controls="{topic_id}" aria-selected="{"true" if is_active else "false"}">'
            f'{topic_name}</a></li>'
        )

        # Generate sub-tabs for notebooks within this topic
        sub_tabs = []
        sub_contents = []

        for j, html_file in enumerate(topic_html_files):
            notebook_name = os.path.splitext(os.path.basename(html_file))[0].split(current_datetime)[0]
            notebook_name = notebook_name.replace("_", " ")
            sub_tab_id = f"{topic_id}_sub{j}"
            is_sub_active = j == 0

            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Sub-tab navigation
            sub_tabs.append(
                f'<li class="nav-item"><a class="nav-link {"active" if is_sub_active else ""}" '
                f'id="{sub_tab_id}-tab" data-bs-toggle="tab" href="#{sub_tab_id}" role="tab" '
                f'aria-controls="{sub_tab_id}" aria-selected="{"true" if is_sub_active else "false"}">'
                f'{notebook_name}</a></li>'
            )

            # Sub-tab content - wrap in isolation container
            sub_contents.append(
                f'<div class="tab-pane fade {"show active" if is_sub_active else ""}" '
                f'id="{sub_tab_id}" role="tabpanel" aria-labelledby="{sub_tab_id}-tab">'
                f'<div class="notebook-content-wrapper">{html_content}</div></div>'
            )

        # Create main tab content with nested tabs
        main_content = f'''
        <div class="tab-pane fade {"show active" if is_active else ""}" id="{topic_id}" role="tabpanel" aria-labelledby="{topic_id}-tab">
            <div class="nested-tabs-container">
                <ul class="nav nav-pills nav-justified mb-3" id="{topic_id}-subtabs" role="tablist">
                    {''.join(sub_tabs)}
                </ul>
                <div class="tab-content" id="{topic_id}-subtab-content">
                    {''.join(sub_contents)}
                </div>
            </div>
        </div>
        '''
        main_contents.append(main_content)

    # Enhanced CSS to handle lab template conflicts
    custom_css = """
    <style>
        /* Override JupyterLab CSS conflicts */
        .notebook-content-wrapper {
            all: initial;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            line-height: 1.5;
            color: #24292f;
        }

        .notebook-content-wrapper * {
            box-sizing: border-box;
        }

        /* Reset conflicting JupyterLab styles */
        .notebook-content-wrapper .jp-Cell,
        .notebook-content-wrapper .jp-CodeCell,
        .notebook-content-wrapper .jp-MarkdownCell {
            margin: 0 !important;
            padding: 10px !important;
            border: none !important;
        }

        /* Fix JupyterLab output styling conflicts */
        .notebook-content-wrapper .jp-OutputArea {
            margin: 10px 0 !important;
        }

        .notebook-content-wrapper .jp-OutputArea-output {
            background: transparent !important;
        }

        /* Ensure Bootstrap tabs work despite JupyterLab CSS */
        .nav-tabs .nav-link {
            background-color: #f8f9fa !important;
            color: #495057 !important;
            border: 1px solid #dee2e6 !important;
            font-weight: 500 !important;
            font-size: 1.1em !important;
            z-index: 1000 !important;
        }

        .nav-tabs .nav-link.active {
            background-color: #fff !important;
            color: #0d6efd !important;
            border-bottom-color: transparent !important;
            z-index: 1001 !important;
        }

        .nav-tabs .nav-link:hover {
            background-color: #e9ecef !important;
            border-color: #dee2e6 !important;
        }

        .nav-pills .nav-link {
            background-color: #f8f9fa !important;
            color: #495057 !important;
            margin: 0 2px !important;
            border-radius: 0.375rem !important;
            z-index: 1000 !important;
        }

        .nav-pills .nav-link.active {
            background-color: #0d6efd !important;
            color: white !important;
            z-index: 1001 !important;
        }

        .nav-pills .nav-link:hover {
            background-color: #e9ecef !important;
            color: #495057 !important;
        }

        .nav-pills .nav-link.active:hover {
            background-color: #0b5ed7 !important;
            color: white !important;
        }

        /* Tab content styling that overrides JupyterLab */
        .tab-content {
            background-color: white !important;
            border: 1px solid #dee2e6 !important;
            border-radius: 0.375rem !important;
            padding: 20px !important;
            margin-top: 10px !important;
            overflow-x: auto !important;
            position: relative !important;
            z-index: 999 !important;
        }

        .nested-tabs-container {
            margin-top: 20px !important;
        }

        .main-tabs .nav-tabs .nav-link {
            font-weight: 500 !important;
            font-size: 1.1em !important;
        }

        .nested-tabs-container .nav-pills .nav-link {
            font-size: 0.95em !important;
        }

        /* Container and body overrides */
        body {
            background-color: #f8f9fa !important;
            overflow-x: hidden !important;
        }

        .container {
            background-color: white !important;
            border-radius: 0.5rem !important;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075) !important;
            padding: 2rem !important;
            margin-top: 2rem !important;
            margin-bottom: 2rem !important;
            max-width: 100% !important;
            position: relative !important;
            z-index: 1 !important;
        }

        /* Responsive content overrides */
        .notebook-content-wrapper table {
            width: 100% !important;
            max-width: 100% !important;
            overflow-x: auto !important;
            display: block !important;
        }

        .notebook-content-wrapper img {
            max-width: 100% !important;
            height: auto !important;
        }

        .notebook-content-wrapper * {
            max-width: 100% !important;
        }

        .notebook-content-wrapper pre,
        .notebook-content-wrapper code {
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }

        /* Force Bootstrap tab functionality */
        .tab-pane {
            display: none !important;
        }

        .tab-pane.active {
            display: block !important;
        }

        .tab-pane.fade {
            transition: opacity 0.15s linear !important;
        }

        .tab-pane.fade:not(.show) {
            opacity: 0 !important;
        }

        .tab-pane.fade.show {
            opacity: 1 !important;
        }
    </style>
    """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>{report_title}</title>
        {custom_css}
    </head>

    <body>
        <div class="container">
            <div class="text-center mb-4">
                <h1 class="display-4">{report_title}</h1>
                <p class="text-muted">Generated on: {current_datetime}</p>
            </div>

            <div class="main-tabs">
                <ul class="nav nav-tabs nav-justified mb-3" id="mainTab" role="tablist">
                    {''.join(main_tabs)}
                </ul>
                <div class="tab-content" id="mainTabContent">
                    {''.join(main_contents)}
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>

        <!-- Force Bootstrap tab initialization -->
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Force reinitialize all tabs
            var tabs = document.querySelectorAll('[data-bs-toggle="tab"]');
            tabs.forEach(function(tab) {{
                new bootstrap.Tab(tab);
            }});

            // Add debugging
            console.log('Bootstrap tabs initialized for lab template');
        }});
        </script>
    </body>
    </html>
    """

def _generate_single_html_template(html_file, report_title, current_datetime):
    """Generate HTML template for a single notebook."""
    notebook_name = os.path.splitext(os.path.basename(html_file))[0].split(current_datetime)[0]
    notebook_name = notebook_name.replace("_", " ")

    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    custom_css = """
    <style>
        body {
            background-color: #f8f9fa;
        }

        .container {
            background-color: white;
            border-radius: 0.5rem;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
            padding: 2rem;
            margin-top: 2rem;
            margin-bottom: 2rem;
        }

        .content {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            padding: 20px;
            margin-top: 10px;
        }

        /* Prevent image overflow and horizontal scrolling */
        img {
            max-width: 100%;
            height: auto;
            display: block;
        }
    </style>
    """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>{report_title}</title>
        {custom_css}
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </head>

    <body>
        <div class="container">
            <div class="text-center mb-4">
                <h1 class="display-4">{report_title}</h1>
                <p class="text-muted">Generated on: {current_datetime}</p>
            </div>
            <div class="content">
                {html_content}
            </div>
        </div>
    </body>
    </html>
    """


def _generate_flat_html_template(html_files, report_title, current_datetime):
    """Generate HTML template for flat tabs structure - Lab template compatible."""
    html_tabs = []
    html_contents = []

    for i, html_file in enumerate(html_files):
        notebook_name = os.path.splitext(os.path.basename(html_file))[0].split(current_datetime)[0]
        notebook_name = notebook_name.replace("_", " ")
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Add HTML content to tab with isolation wrapper
        html_tabs.append(
            f'<li class="nav-item"><a class="nav-link {"active" if i == 0 else ""}" id="tab{i}-link" data-bs-toggle="tab" href="#tab{i}" role="tab" aria-controls="tab{i}" aria-selected="{"true" if i == 0 else "false"}">{notebook_name}</a></li>')
        html_contents.append(
            f'<div class="tab-pane fade {"show active" if i == 0 else ""}" id="tab{i}" role="tabpanel" aria-labelledby="tab{i}-link"><div class="notebook-content-wrapper">{html_content}</div></div>')

    # Enhanced CSS for lab template compatibility
    custom_css = """
    <style>
        /* Override JupyterLab CSS conflicts */
        .notebook-content-wrapper {
            all: initial;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            line-height: 1.5;
            color: #24292f;
        }

        .notebook-content-wrapper * {
            box-sizing: border-box;
        }

        /* Reset conflicting JupyterLab styles */
        .notebook-content-wrapper .jp-Cell,
        .notebook-content-wrapper .jp-CodeCell,
        .notebook-content-wrapper .jp-MarkdownCell {
            margin: 0 !important;
            padding: 10px !important;
            border: none !important;
        }

        /* Ensure Bootstrap tabs work */
        .nav-tabs .nav-link {
            background-color: #f8f9fa !important;
            color: #495057 !important;
            border: 1px solid #dee2e6 !important;
            z-index: 1000 !important;
        }

        .nav-tabs .nav-link.active {
            background-color: #fff !important;
            color: #0d6efd !important;
            border-bottom-color: transparent !important;
            z-index: 1001 !important;
        }

        .nav-tabs .nav-link:hover {
            background-color: #e9ecef !important;
            border-color: #dee2e6 !important;
        }

        body {
            background-color: #f8f9fa !important;
            overflow-x: hidden !important;
        }

        .container {
            background-color: white !important;
            border-radius: 0.5rem !important;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075) !important;
            padding: 2rem !important;
            margin-top: 2rem !important;
            margin-bottom: 2rem !important;
            max-width: 100% !important;
        }

        .tab-content {
            background-color: white !important;
            border: 1px solid #dee2e6 !important;
            border-top: none !important;
            border-radius: 0 0 0.375rem 0.375rem !important;
            padding: 20px !important;
            margin-top: 0 !important;
            overflow-x: auto !important;
        }

        /* Force Bootstrap tab functionality */
        .tab-pane {
            display: none !important;
        }

        .tab-pane.active {
            display: block !important;
        }

        .tab-pane.fade {
            transition: opacity 0.15s linear !important;
        }

        .tab-pane.fade:not(.show) {
            opacity: 0 !important;
        }

        .tab-pane.fade.show {
            opacity: 1 !important;
        }

        /* Responsive content */
        .notebook-content-wrapper table {
            width: 100% !important;
            max-width: 100% !important;
            overflow-x: auto !important;
            display: block !important;
        }

        .notebook-content-wrapper img {
            max-width: 100% !important;
            height: auto !important;
        }

        .notebook-content-wrapper * {
            max-width: 100% !important;
        }

        .notebook-content-wrapper pre,
        .notebook-content-wrapper code {
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }
    </style>
    """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>{report_title}</title>
        {custom_css}
    </head>

    <body>
        <div class="container">
            <div class="text-center mb-4">
                <h1 class="display-4">{report_title}</h1>
                <p class="text-muted">Generated on: {current_datetime}</p>
            </div>
            <ul class="nav nav-tabs nav-justified mb-3" id="myTab" role="tablist">
                {''.join(html_tabs)}
            </ul>
            <div class="tab-content">
                {''.join(html_contents)}
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>

        <!-- Force Bootstrap tab initialization -->
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Force reinitialize all tabs
            var tabs = document.querySelectorAll('[data-bs-toggle="tab"]');
            tabs.forEach(function(tab) {{
                new bootstrap.Tab(tab);
            }});

            console.log('Bootstrap tabs initialized for lab template');
        }});
        </script>
    </body>
    </html>
    """

# Generate final HTML report - now handles both flat and nested structures
def generate_final_report(html_files, report_title, output_folder, current_datetime: str):
    """Enhanced to support both flat list, nested dict structures, and single file."""

    if isinstance(html_files, dict):
        template_str = _generate_nested_html_template(html_files, report_title, current_datetime)
    elif isinstance(html_files, str):
        template_str = _generate_single_html_template(html_files, report_title, current_datetime)
    else:
        template_str = _generate_flat_html_template(html_files, report_title, current_datetime)

    # Write final report
    report_filename = f"{report_title.replace(' ', '_')}_{current_datetime}.html"
    report_path = os.path.join(output_folder, report_filename)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(template_str)

    print(f"Report saved to: {report_path}")


def _discover_notebooks_from_directory(notebook_dir: str):
    """
    Discover notebooks from directory structure and create nested dict.
    Only supports one level of subdirectories.

    Returns:
        dict: {subdirectory_name: [list_of_notebook_paths]} or
              list: [notebook_paths] if no subdirectories found
    """
    if not os.path.exists(notebook_dir):
        print(f"Directory does not exist: {notebook_dir}")
        return []

    # Get all .ipynb files in root directory
    root_notebooks = glob.glob(os.path.join(notebook_dir, "*.ipynb"))

    # Get all subdirectories
    subdirs = [d for d in os.listdir(notebook_dir)
               if os.path.isdir(os.path.join(notebook_dir, d)) and not d.startswith('.')]

    if not subdirs:
        # No subdirectories, return flat structure
        if root_notebooks:
            print(f"Found {len(root_notebooks)} notebooks in root directory")
            return root_notebooks
        else:
            print(f"No notebooks found in directory: {notebook_dir}")
            return []

    # Build nested structure from subdirectories
    nested_structure = {}

    # Add root notebooks if any (as "Main" category)
    if root_notebooks:
        nested_structure["Main"] = root_notebooks
        print(f"Found {len(root_notebooks)} notebooks in root directory (Main category)")

    # Process each subdirectory
    for subdir in subdirs:
        if subdir.startswith('.'):
            continue
        subdir_path = os.path.join(notebook_dir, subdir)
        subdir_notebooks = glob.glob(os.path.join(subdir_path, "*.ipynb"))

        if subdir_notebooks:
            # Use subdirectory name as topic name (clean it up)
            topic_name = subdir.replace('_', ' ').replace('-', ' ').title()
            nested_structure[topic_name] = subdir_notebooks
            print(f"Found {len(subdir_notebooks)} notebooks in '{subdir}' -> '{topic_name}' category")

    if not nested_structure:
        print(f"No notebooks found in {notebook_dir} or its subdirectories")
        return []

    return nested_structure
# Main function
def generate_report(config_path: str):
    config = load_config(config_path)
    notebook_files = config.get("notebook_files", [])
    current_datetime = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    if not notebook_files:
        notebook_dir = config.get("notebook_dir", ".")
        notebook_files = _discover_notebooks_from_directory(notebook_dir)
        if not notebook_files:
            return

    output_folder = config.get("output_folder", "./output")
    report_title = config.get("report_title", "Jupyter tabs Notebooks Report")
    execute = config.get("execute", False)

    if execute:
        print("Executing and converting notebooks to HTML...")
    else:
        print("Converting notebooks to HTML...")

    # Check if notebook_files is a dict (nested structure), string (single notebook), or list (flat structure)
    if isinstance(notebook_files, dict):
        # Nested structure
        html_files_dict = {}

        for topic_name, topic_notebooks in notebook_files.items():
            print(f"Processing topic: {topic_name}")
            html_files = convert_notebooks_to_html(topic_notebooks, output_folder, current_datetime, execute)
            html_files_dict[topic_name] = html_files

        print("Generating nested tabs HTML report...")
        generate_final_report(html_files_dict, report_title, output_folder, current_datetime)

    elif isinstance(notebook_files, str):
        # Single notebook
        print(f"Processing single notebook: {notebook_files}")
        html_files = convert_notebooks_to_html([notebook_files], output_folder, current_datetime, execute)
        if html_files:
            print("Generating single notebook HTML report...")
            generate_final_report(html_files[0], report_title, output_folder, current_datetime)

    else:
        # Flat structure - maintain backward compatibility
        html_files = convert_notebooks_to_html(notebook_files, output_folder, current_datetime, execute)
        print("Generating flat tabs HTML report...")
        generate_final_report(html_files, report_title, output_folder, current_datetime)

    print("Done!")


# Run the script
if __name__ == "__main__":
    config_file_path = "tabs_report\\config.json"  # Change this if necessary
    generate_report(config_file_path)
