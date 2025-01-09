import os
import glob
import nbformat
import subprocess
from datetime import datetime
from jinja2 import Template

from misc.config_loader import load_config


def convert_notebooks_to_html(notebook_files: [str], output_folder: str, postfix: str):
    os.makedirs(output_folder, exist_ok=True)
    converted_html_files = []

    for notebook_file in notebook_files:
        notebook_name = os.path.splitext(os.path.basename(notebook_file))[0]
        html_output_path = os.path.join(output_folder, f"{notebook_name}_{postfix}.html")

        # Use nbconvert to convert notebook to HTML without input code
        subprocess.run([
            "jupyter", "nbconvert", "--to", "html", "--no-input","--template", "basic",
            "--output", html_output_path, notebook_file
        ], check=True)

        converted_html_files.append(html_output_path)

    return converted_html_files


# Generate final HTML report
def generate_final_report(html_files, report_title, output_folder, current_datetime: str):
    html_tabs = []
    html_contents = []
    for i, html_file in enumerate(html_files):
        notebook_name = os.path.splitext(os.path.basename(html_file))[0].split(current_datetime)[0]
        notebook_name = notebook_name.replace("_", " ")
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Add HTML content to tab
        html_tabs.append(
            f'<li class="nav-item"><a class="nav-link { "active" if i == 0 else "" }" id="tab{i}-link" data-bs-toggle="tab" href="#tab{i}" role="tab" aria-controls="tab{i}" aria-selected="{ "true" if i == 0 else "false" }">{notebook_name}</a></li>')
        html_contents.append(
            f'<div class="tab-pane fade { "show active" if i == 0 else "" }" id="tab{i}" role="tabpanel" aria-labelledby="tab{i}-link">{html_content}</div>')
    # Load HTML template
    template_str = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>{report_title}</title>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.min.js"></script>
    </head>
    
    <body>
        <div class="container mt-4">
            <h1>{report_title}</h1>
            <h5 class="text-muted">Generated on: {current_datetime}</h5>
            <ul class="nav nav-tabs" id="myTab" role="tablist">
                {''.join(html_tabs)}
            </ul>
            <div class="tab-content">
                {''.join(html_contents)}
            </div>
        </div>
        
        
    </body>
    </html>
    """

    # Write final report
    report_filename = f"{report_title.replace(' ', '_')}_{current_datetime}.html"
    report_path = os.path.join(output_folder, report_filename)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(template_str)

    print(f"Report saved to: {report_path}")


# Main function
def generate_tabs_report(config_path: str):
    config = load_config(config_path)
    notebook_files = config.get("notebook_files", [])
    current_datetime = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    if not notebook_files:
        notebook_dir = config.get("notebook_dir", ".")
        notebook_files = glob.glob(os.path.join(notebook_dir, "*.ipynb"))
        if not notebook_files:
            print(f"No notebooks found in directory: {notebook_dir} and no files specified in config.")
            return
    output_folder = config.get("output_folder", "./output")
    report_title = config.get("report_title", "Jupyter tabs Notebooks Report")
    print("Converting notebooks to HTML...")
    html_files = convert_notebooks_to_html(notebook_files, output_folder, current_datetime)

    print("Generating final HTML report...")
    generate_final_report(html_files, report_title, output_folder, current_datetime)
    print("Done!")


# Run the script
if __name__ == "__main__":
    config_file_path = "config.json"  # Change this if necessary
    generate_tabs_report(config_file_path)
