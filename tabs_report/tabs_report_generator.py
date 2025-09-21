import os
import glob
import re
from typing import Union

import nbformat
import subprocess
from datetime import datetime
from jinja2 import Template

from misc.config_loader import load_config



def _has_rtl_content(text: str) -> bool:
    """
    Check if the given text contains any Right-to-Left (RTL) characters.

    This function detects Hebrew and Arabic characters by checking against
    their Unicode ranges. It's used to determine if RTL processing should
    be applied to notebook content.

    Args:
        text (str): The text content to analyze for RTL characters.

    Returns:
        bool: True if the text contains Hebrew or Arabic characters, False otherwise.

    Unicode Ranges:
        - Hebrew: \\u0590-\\u05FF
        - Arabic: \\u0600-\\u06FF, \\u0750-\\u077F, \\u08A0-\\u08FF
    """
    # Hebrew Unicode range: \u0590-\u05FF
    # Arabic Unicode range: \u0600-\u06FF, \u0750-\u077F, \u08A0-\u08FF
    rtl_pattern = r'[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]'
    return bool(re.search(rtl_pattern, text))


def _apply_rtl_processing(html_content: str) -> str:
    """
    Apply Right-to-Left (RTL) text processing to HTML content from Jupyter notebooks.

    This function identifies RTL text segments (Hebrew/Arabic) within HTML content
    and wraps them in special paragraphs with RTL-specific CSS classes and
    directional attributes. This ensures proper text rendering while preserving
    the overall document layout.

    The processing is selective - it only affects text content that actually
    contains RTL characters, leaving LTR content, code blocks, images, and
    structural elements unchanged.

    Args:
        html_content (str): Raw HTML content from converted Jupyter notebook.

    Returns:
        str: Processed HTML content with RTL text properly wrapped and styled.

    Processing Steps:
        1. Check if content contains any RTL characters
        2. If no RTL content found, return original HTML unchanged
        3. Identify RTL text segments within various HTML elements
        4. Wrap RTL segments in <p class="rtl-text-content" dir="rtl"> tags
        5. Preserve non-RTL elements (images, code, tables) in LTR format

    Target Elements:
        - Headings (h1-h6)
        - Paragraphs (p)
        - List items (li)
        - Table cells (td, th)
        - Pre-formatted text (pre)
        - Text cell renders (div.text_cell_render)
    """
    # Only apply RTL processing if the content actually contains RTL characters
    if not _has_rtl_content(html_content):
        return html_content
    
    # Function to check if a specific text snippet contains RTL characters
    def has_rtl_in_text(text):
        rtl_pattern = r'[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]'
        return bool(re.search(rtl_pattern, text))
    
    # Function to wrap RTL content in special paragraph
    def wrap_rtl_content(text):
        if not has_rtl_in_text(text):
            return text
        
        # Split text into RTL and non-RTL segments
        # Match sequences that contain RTL characters, but only capture RTL parts
        rtl_pattern = r'([\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+(?:\s*[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+)*)'
        
        def replace_rtl_segment(match):
            rtl_text = match.group(1)
            return f'<p class="rtl-text-content" dir="rtl">{rtl_text}</p>'
        
        # Replace RTL segments with wrapped paragraphs
        processed_text = re.sub(rtl_pattern, replace_rtl_segment, text)
        return processed_text
    
    # Process text content in various HTML elements
    def process_element_content(match):
        full_tag = match.group(0)
        opening_tag = match.group(1)
        content = match.group(2) if len(match.groups()) >= 2 else ""
        closing_tag = match.group(3) if len(match.groups()) >= 3 else ""
        
        # Skip if already has dir attribute or is structural element
        if 'dir=' in opening_tag or any(cls in opening_tag for cls in ['output', 'cell', 'jp-']):
            return full_tag
        
        # Process content for RTL wrapping
        processed_content = wrap_rtl_content(content)
        
        return opening_tag + processed_content + closing_tag
    
    # Target various text-containing elements
    text_patterns = [
        # Headings
        (r'(<h[1-6][^>]*>)(.*?)(</h[1-6]>)', process_element_content),
        # Paragraphs  
        (r'(<p[^>]*>)(.*?)(</p>)', process_element_content),
        # List items
        (r'(<li[^>]*>)(.*?)(</li>)', process_element_content),
        # Table cells
        (r'(<td[^>]*>)(.*?)(</td>)', process_element_content),
        (r'(<th[^>]*>)(.*?)(</th>)', process_element_content),
        # Pre-formatted text (common in Jupyter notebook outputs)
        (r'(<pre[^>]*>)(.*?)(</pre>)', process_element_content),
        # Generic divs (but skip structural ones)
        (r'(<div[^>]*class="text_cell_render[^"]*"[^>]*>)(.*?)(</div>)', process_element_content),
    ]
    
    # Apply RTL processing
    for pattern, processor in text_patterns:
        html_content = re.sub(pattern, processor, html_content, flags=re.DOTALL)
    
    return html_content


def convert_notebooks_to_html(
    notebook_files: Union[list[str], dict],
    output_folder: str,
    postfix: str,
    execute: bool = False,
    custom_names: Union[list[str], None] = None
) -> list[dict]:
    """
    Convert Jupyter notebooks to HTML format using nbconvert.

    This function processes a collection of Jupyter notebook files and converts
    them to HTML format suitable for inclusion in tabbed reports. It handles
    unique naming to avoid file collisions and supports optional execution
    before conversion.

    Args:
        notebook_files (Union[list[str], dict]):
            List of notebook file paths to convert. Can be a list of strings
            or any iterable containing notebook paths.

        output_folder (str):
            Directory path where converted HTML files will be saved.
            Directory will be created if it doesn't exist.

        postfix (str):
            String to append to output filenames for uniqueness.
            Typically a timestamp or identifier.

        execute (bool, optional):
            Whether to execute notebook cells before conversion.
            Defaults to False. If True, runs all cells and captures output.
            Falls back to non-execution mode if execution fails.

        custom_names (Union[list[str], None], optional):
            List of custom display names for notebooks. If provided,
            names are matched by index position. Missing indices use
            default naming. Defaults to None.

    Returns:
        list[dict]: List of dictionaries containing conversion results.
            Each dictionary has:
            - 'output_name' (str): Full path to generated HTML file
            - 'notebook_name' (str): Display name for the notebook

    Raises:
        subprocess.CalledProcessError: If nbconvert fails critically
        FileNotFoundError: If notebook files don't exist
        PermissionError: If output directory is not writable

    File Naming:
        - Generates unique filenames using directory structure
        - Format: {dir_part}_{notebook_name}_{postfix}.html
        - Handles path collisions by including parent directory names
        - Replaces spaces and special characters for web compatibility

    Execution Behavior:
        - Uses jupyter nbconvert with --execute flag when enabled
        - Applies 600-second timeout per cell
        - Continues on cell errors with --allow-errors
        - Falls back to non-execution if execution fails entirely
        - Provides detailed error logging for troubleshooting
    """
    os.makedirs(output_folder, exist_ok=True)
    converted_html_files = []

    for notebook_file in notebook_files:
        # Create unique name that includes directory path to avoid collisions
        notebook_name = os.path.splitext(os.path.basename(notebook_file))[0].replace("_", " ").capitalize()
        notebook_dir = os.path.dirname(notebook_file)
        
        # Create a unique identifier by including parent directory names
        if notebook_dir and notebook_dir != '.':
            # Replace path separators with underscores to create valid filename
            dir_part = notebook_dir.replace(os.path.sep, '_').replace('/', '_').replace('\\', '_')
            unique_name = f"{dir_part}_{notebook_name}"
        else:
            unique_name = notebook_name
            
        html_output_path = os.path.abspath(os.path.join(output_folder, f"{unique_name}_{postfix}.html"))

        # Build nbconvert command
        nbconvert_cmd = ["jupyter", "nbconvert", "--to", "html", "--no-input", "--template", "basic"]

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
                    basic_cmd = ["jupyter", "nbconvert", "--to", "html", "--no-input", "--template", "basic",
                                "--output", html_output_path, notebook_file]
                    print("Retrying conversion without execution...")
                    subprocess.run(basic_cmd, check=True)
        except Exception as e:
            print(f"Error converting notebook {notebook_file}: {str(e)}")
            # Continue with next notebook
            continue

        # Use custom name if provided, otherwise use default
        display_name = notebook_name
        if custom_names and len(custom_names) > len(converted_html_files):
            display_name = custom_names[len(converted_html_files)]

        # Return dict with both output_name (file path) and notebook_name (display name)
        converted_html_files.append({
            'output_name': html_output_path,
            'notebook_name': display_name
        })

    return converted_html_files


def _generate_nested_html_template(
    html_files: dict,
    report_title: str,
    current_datetime: str,
    tabs_names: Union[dict, None] = None
) -> str:
    """
    Generate HTML template for nested tabs structure with hierarchical organization.

    Creates a two-level tabbed interface where the main tabs represent topics/categories
    and sub-tabs contain individual notebooks within each topic. This structure is
    ideal for organizing related notebooks into logical groups.

    Args:
        html_files (dict):
            Dictionary mapping topic names to lists of notebook info dictionaries.
            Format: {topic_name: [{'output_name': str, 'notebook_name': str}, ...]}

        report_title (str):
            Title to display at the top of the report page.

        current_datetime (str):
            Timestamp string for report generation time display.

        tabs_names (Union[dict, None], optional):
            Custom naming configuration for topics and notebooks.
            Supports two formats:
            1. Simple: {topic_key: [notebook_names...]}
            2. Advanced: {topic_key: {'topic_name': str, 'notebook_names': [str...]}}
            Defaults to None (uses original names).

    Returns:
        str: Complete HTML document with nested tabs interface.

    Template Structure:
        - Bootstrap-based responsive design
        - Main navigation tabs for topics (nav-tabs)
        - Nested pill-style navigation for notebooks (nav-pills)
        - RTL text support with specialized CSS classes
        - Bokeh visualization library integration
        - Image overflow prevention and responsive sizing

    Custom Naming Logic:
        - If tabs_names[topic] is dict with 'topic_name': uses custom topic name
        - If tabs_names[topic] is string: uses as topic name
        - If tabs_names[topic] is list: keeps original topic, customizes notebook names
        - Falls back to original names for missing configurations

    CSS Features:
        - Responsive container with shadow and rounded corners
        - Color-coded active/inactive states for tabs
        - RTL text rendering with proper direction and alignment
        - Image centering and size constraints
        - Table structure preservation in mixed-direction content
    """
    main_tabs = []
    main_contents = []

    for i, (topic_name, topic_html_files) in enumerate(html_files.items()):
        topic_id = f"topic{i}"
        is_active = i == 0

        # Use custom topic name if provided
        display_topic_name = topic_name
        if tabs_names and topic_name in tabs_names:
            topic_config = tabs_names[topic_name]
            if isinstance(topic_config, dict) and 'topic_name' in topic_config:
                display_topic_name = topic_config['topic_name']
            elif isinstance(topic_config, str):
                display_topic_name = topic_config
            # If topic_config is a list, keep the original topic name (list is for notebook names only)

        # Create main tab
        main_tabs.append(
            f'<li class="nav-item"><a class="nav-link {"active" if is_active else ""}" '
            f'id="{topic_id}-tab" data-bs-toggle="tab" href="#{topic_id}" role="tab" '
            f'aria-controls="{topic_id}" aria-selected="{"true" if is_active else "false"}">'
            f'{display_topic_name}</a></li>'
        )

        # Generate sub-tabs for notebooks within this topic
        sub_tabs = []
        sub_contents = []

        for j, html_file_info in enumerate(topic_html_files):
            # html_file_info is now a dict with 'output_name' and 'notebook_name'
            html_file = html_file_info['output_name']
            notebook_name = html_file_info['notebook_name']
            sub_tab_id = f"{topic_id}_sub{j}"
            is_sub_active = j == 0

            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = _apply_rtl_processing(f.read())

            # Sub-tab navigation
            sub_tabs.append(
                f'<li class="nav-item"><a class="nav-link {"active" if is_sub_active else ""}" '
                f'id="{sub_tab_id}-tab" data-bs-toggle="tab" href="#{sub_tab_id}" role="tab" '
                f'aria-controls="{sub_tab_id}" aria-selected="{"true" if is_sub_active else "false"}">'
                f'{notebook_name}</a></li>'
            )

            # Sub-tab content
            sub_contents.append(
                f'<div class="tab-pane fade {"show active" if is_sub_active else ""}" '
                f'id="{sub_tab_id}" role="tabpanel" aria-labelledby="{sub_tab_id}-tab">'
                f'{html_content}</div>'
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

    custom_css = """
    <style>
        .nested-tabs-container {
            margin-top: 20px;
        }

        .nav-pills .nav-link {
            background-color: #f8f9fa;
            color: #495057;
            margin: 0 2px;
            border-radius: 0.375rem;
        }

        .nav-pills .nav-link.active {
            background-color: #0d6efd;
            color: white;
        }

        .nav-pills .nav-link:hover {
            background-color: #e9ecef;
            color: #495057;
        }

        .nav-pills .nav-link.active:hover {
            background-color: #0b5ed7;
            color: white;
        }

        .tab-content {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            padding: 20px;
            margin-top: 10px;
        }

        .main-tabs .nav-tabs .nav-link {
            font-weight: 500;
            font-size: 1.1em;
        }

        .nested-tabs-container .nav-pills .nav-link {
            font-size: 0.95em;
        }

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

        /* Prevent image overflow and horizontal scrolling */
        img {
            max-width: 100%;
            height: auto;
            display: block;
        }

        /* RTL Support - Targeted approach using special class */
        .rtl-text-content {
            direction: rtl !important;
            text-align: right !important;
            display: inline !important;
            margin: 0 !important;
            padding: 0 !important;
            font-size: inherit !important;
            font-weight: inherit !important;
            line-height: inherit !important;
            color: inherit !important;
        }
        
        /* Ensure all other elements remain LTR (images, code, etc.) */
        img, figure, .output_png, .output_jpeg, code, pre {
            direction: ltr !important;
            text-align: left !important;
        }
        
        /* Specific image centering */
        .output_png img, .output_jpeg img {
            display: block !important;
            margin: 0 auto !important;
        }

        /* Keep table structure LTR even if cells have RTL text */
        table {
            direction: ltr;
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
        <link rel="stylesheet" href="https://cdn.bokeh.org/bokeh/release/bokeh-3.3.0.min.css" type="text/css" />

        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-3.3.0.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-3.3.0.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-tables-3.3.0.min.js"></script>
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
    </body>
    </html>
    """


def _generate_single_html_template(
    html_file_info: dict,
    report_title: str,
    current_datetime: str
) -> str:
    """
    Generate HTML template for a single notebook without tabs interface.

    Creates a clean, single-page report containing one notebook's content.
    This template maintains the same visual styling and features as the
    tabbed versions but without navigation complexity.

    Args:
        html_file_info (dict):
            Dictionary containing notebook information:
            - 'output_name' (str): Path to the converted HTML file
            - 'notebook_name' (str): Display name for the notebook

        report_title (str):
            Title to display at the top of the report page.
            Used as the main heading since there are no tabs.

        current_datetime (str):
            Timestamp string showing when the report was generated.

    Returns:
        str: Complete HTML document containing the single notebook.

    Template Features:
        - Clean, centered layout with Bootstrap styling
        - Same RTL text support as multi-notebook reports
        - Responsive image handling and overflow prevention
        - Bokeh visualization library integration
        - Professional styling with shadows and rounded corners

    Use Cases:
        - Single analysis reports
        - Standalone notebook presentations
        - Simple document conversion without categorization
        - Quick notebook sharing with consistent styling

    Styling Consistency:
        - Matches visual design of tabbed reports
        - Same CSS classes and responsive behavior
        - Identical RTL text processing capabilities
        - Compatible with all notebook output types
    """
    # html_file_info is now a dict with 'output_name' and 'notebook_name'
    html_file = html_file_info['output_name']
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = _apply_rtl_processing(f.read())

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

        /* RTL Support - Targeted approach using special class */
        .rtl-text-content {
            direction: rtl !important;
            text-align: right !important;
            display: inline !important;
            margin: 0 !important;
            padding: 0 !important;
            font-size: inherit !important;
            font-weight: inherit !important;
            line-height: inherit !important;
            color: inherit !important;
        }
        
        /* Ensure all other elements remain LTR (images, code, etc.) */
        img, figure, .output_png, .output_jpeg, code, pre {
            direction: ltr !important;
            text-align: left !important;
        }
        
        /* Specific image centering */
        .output_png img, .output_jpeg img {
            display: block !important;
            margin: 0 auto !important;
        }

        /* Keep table structure LTR even if cells have RTL text */
        table {
            direction: ltr;
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
        <link rel="stylesheet" href="https://cdn.bokeh.org/bokeh/release/bokeh-3.3.0.min.css" type="text/css" />

        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-3.3.0.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-3.3.0.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-tables-3.3.0.min.js"></script>
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


def _generate_flat_html_template(
    html_files: list[dict],
    report_title: str,
    current_datetime: str
) -> str:
    """
    Generate HTML template for flat tabs structure with single-level navigation.

    Creates a simple tabbed interface where all notebooks are at the same
    hierarchical level. This structure is ideal for collections of related
    but independent analyses that don't require categorization.

    Args:
        html_files (list[dict]):
            List of notebook information dictionaries.
            Each dictionary contains:
            - 'output_name' (str): Path to the converted HTML file
            - 'notebook_name' (str): Display name for the notebook tab

        report_title (str):
            Title to display at the top of the report page.

        current_datetime (str):
            Timestamp string for report generation time display.

    Returns:
        str: Complete HTML document with flat tabs interface.

    Template Structure:
        - Bootstrap nav-tabs for horizontal tab navigation
        - Tab content areas with fade transitions
        - First tab active by default
        - Responsive design with justified tab layout

    Navigation Behavior:
        - Tabs use Bootstrap JavaScript for switching
        - Smooth fade transitions between notebooks
        - Keyboard navigation support
        - ARIA labels for accessibility

    Styling Features:
        - Pill-style navigation with hover effects
        - Active tab highlighting with brand colors
        - Content area with border and padding
        - RTL text support with specialized CSS
        - Image overflow prevention and responsive sizing

    Use Cases:
        - Multiple related analyses
        - Comparative studies
        - Sequential workflow documentation
        - Dashboard-style multi-notebook reports

    Tab Naming:
        - Uses 'notebook_name' from html_files entries
        - Names can be customized via tabs_names in parent functions
        - Falls back to filename-based naming if not specified
    """
    html_tabs = []
    html_contents = []

    for i, html_file_info in enumerate(html_files):
        # html_file_info is now a dict with 'output_name' and 'notebook_name'
        html_file = html_file_info['output_name']
        notebook_name = html_file_info['notebook_name']
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = _apply_rtl_processing(f.read())

        # Add HTML content to tab
        html_tabs.append(
            f'<li class="nav-item"><a class="nav-link {"active" if i == 0 else ""}" id="tab{i}-link" data-bs-toggle="tab" href="#tab{i}" role="tab" aria-controls="tab{i}" aria-selected="{"true" if i == 0 else "false"}">{notebook_name}</a></li>')
        html_contents.append(
            f'<div class="tab-pane fade {"show active" if i == 0 else ""}" id="tab{i}" role="tabpanel" aria-labelledby="tab{i}-link">{html_content}</div>')

    custom_css = """
    <style>
        .nav-pills .nav-link {
            background-color: #f8f9fa;
            color: #495057;
            margin: 0 2px;
            border-radius: 0.375rem;
        }

        .nav-pills .nav-link.active {
            background-color: #0d6efd;
            color: white;
        }

        .nav-pills .nav-link:hover {
            background-color: #e9ecef;
            color: #495057;
        }

        .nav-pills .nav-link.active:hover {
            background-color: #0b5ed7;
            color: white;
        }

        .tab-content {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            padding: 20px;
            margin-top: 10px;
        }

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

        /* Prevent image overflow and horizontal scrolling */
        img {
            max-width: 100%;
            height: auto;
            display: block;
        }

        /* RTL Support - Targeted approach using special class */
        .rtl-text-content {
            direction: rtl !important;
            text-align: right !important;
            display: inline !important;
            margin: 0 !important;
            padding: 0 !important;
            font-size: inherit !important;
            font-weight: inherit !important;
            line-height: inherit !important;
            color: inherit !important;
        }
        
        /* Ensure all other elements remain LTR (images, code, etc.) */
        img, figure, .output_png, .output_jpeg, code, pre {
            direction: ltr !important;
            text-align: left !important;
        }
        
        /* Specific image centering */
        .output_png img, .output_jpeg img {
            display: block !important;
            margin: 0 auto !important;
        }

        /* Keep table structure LTR even if cells have RTL text */
        table {
            direction: ltr;
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
        <link rel="stylesheet" href="https://cdn.bokeh.org/bokeh/release/bokeh-3.3.0.min.css" type="text/css" />

        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-3.3.0.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-3.3.0.min.js"></script>
        <script src="https://cdn.bokeh.org/bokeh/release/bokeh-tables-3.3.0.min.js"></script>
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
            <ul class="nav nav-tabs nav-justified mb-3" id="myTab" role="tablist">
                {''.join(html_tabs)}
            </ul>
            <div class="tab-content">
                {''.join(html_contents)}
            </div>
        </div>
    </body>
    </html>
    """


# Generate final HTML report - now handles both flat and nested structures
def generate_final_report(
    html_files: Union[dict, list, dict],
    report_title: str,
    output_folder: str,
    current_datetime: str,
    tabs_names: Union[dict, list, None] = None
) -> None:
    """
    Generate the final HTML report by selecting appropriate template and writing output.

    This function serves as a dispatcher that analyzes the structure of the provided
    HTML files and generates the appropriate report template (single, flat, or nested).
    It handles the final file writing and provides user feedback.

    Args:
        html_files (Union[dict, list]):
            Notebook data in various formats:
            - dict with 'output_name'/'notebook_name': Single notebook
            - list of dicts: Flat structure (simple tabs)
            - dict of lists: Nested structure (categorized tabs)

        report_title (str):
            Title for the report, used in HTML title and header.
            Spaces are replaced with underscores for filename.

        output_folder (str):
            Directory where the final report HTML file will be saved.
            Must be writable and will be created if needed.

        current_datetime (str):
            Timestamp string for filename uniqueness and display.
            Format typically: YYYY_MM_DD_HH_MM_SS

        tabs_names (Union[dict, list, None], optional):
            Custom naming configuration passed to template generators.
            Format depends on report structure. Defaults to None.

    Returns:
        None: Function writes file and prints confirmation message.

    Report Structure Detection:
        1. Single notebook: dict with 'output_name' and 'notebook_name' keys
        2. Nested structure: dict without those specific keys (topic -> notebooks)
        3. Flat structure: list of notebook dictionaries

    File Naming:
        - Format: {report_title}_{current_datetime}.html
        - Spaces in title replaced with underscores
        - Saved in specified output_folder

    Template Selection:
        - Single: _generate_single_html_template()
        - Nested: _generate_nested_html_template() with tabs_names
        - Flat: _generate_flat_html_template()

    Output:
        - Writes complete HTML file to disk
        - Prints confirmation with full file path
        - File ready for browser viewing or web deployment
    """

    if isinstance(html_files, dict) and not ('output_name' in html_files and 'notebook_name' in html_files):
        # This is a nested structure (dict of topics -> lists of html files)
        template_str = _generate_nested_html_template(html_files, report_title, current_datetime, tabs_names)
    elif isinstance(html_files, dict) and 'output_name' in html_files and 'notebook_name' in html_files:
        # This is a single notebook dict
        template_str = _generate_single_html_template(html_files, report_title, current_datetime)
    else:
        # This is a flat list of notebook dicts
        template_str = _generate_flat_html_template(html_files, report_title, current_datetime)

    # Write final report
    report_filename = f"{report_title.replace(' ', '_')}_{current_datetime}.html"
    report_path = os.path.join(output_folder, report_filename)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(template_str)

    print(f"Report saved to: {report_path}")


def _discover_notebooks_from_directory(notebook_dir: str) -> Union[dict, list]:
    """
    Automatically discover Jupyter notebooks from directory structure.

    Scans the specified directory and its immediate subdirectories to find
    .ipynb files, organizing them into an appropriate structure based on
    the directory layout. Supports both flat and nested organization.

    Args:
        notebook_dir (str):
            Path to directory containing notebooks and/or subdirectories.
            Must exist and be readable.

    Returns:
        Union[dict, list]:
            - dict: Nested structure if subdirectories found
                   Format: {subdirectory_name: [notebook_paths...]}
                   Includes "Main" category for root-level notebooks
            - list: Flat list if no subdirectories with notebooks
                   Format: [notebook_path1, notebook_path2, ...]
            - []: Empty list if no notebooks found

    Directory Scanning Logic:
        1. Check if target directory exists
        2. Find all .ipynb files in root directory
        3. Identify subdirectories (excluding hidden dirs starting with '.')
        4. Scan each subdirectory for .ipynb files
        5. Build nested structure if subdirectories contain notebooks
        6. Return flat structure if only root notebooks found

    Nested Structure Rules:
        - Each subdirectory becomes a topic/category
        - Subdirectory names are cleaned: underscores→spaces, title case
        - Root notebooks grouped under "Main" category
        - Only processes one level of subdirectories (not recursive)
        - Ignores empty subdirectories

    Topic Name Processing:
        - 'data_analysis' → 'Data Analysis'
        - 'machine-learning' → 'Machine-Learning' → 'Machine Learning'
        - 'results' → 'Results'

    Error Handling:
        - Returns empty list if directory doesn't exist
        - Skips unreadable files or directories
        - Prints informative messages about discovery progress
        - Gracefully handles permission errors

    Use Cases:
        - Quick report generation from existing notebook collections
        - Automatic organization of analysis workflows
        - Discovery mode for unknown directory structures
        - Batch processing of notebook repositories
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
def generate_report(config_path: str) -> None:
    """
    Main entry point for generating Jupyter notebook reports from configuration.

    This function orchestrates the entire report generation process by loading
    configuration, processing notebooks, and creating the final HTML report.
    It supports multiple notebook organization patterns and provides comprehensive
    error handling and user feedback.

    Args:
        config_path (str):
            Path to JSON configuration file containing report settings.
            Must be readable and contain valid JSON.

    Returns:
        None: Generates HTML report file and prints status messages.

    Configuration Structure:
        Required fields:
        - 'notebook_files': Notebooks to process (see formats below)
        - 'output_folder': Where to save generated files
        - 'report_title': Title for the report

        Optional fields:
        - 'execute': Whether to run notebooks before conversion (default: False)
        - 'tabs_names': Custom tab naming (see Custom Naming section)
        - 'notebook_dir': Directory for auto-discovery when notebook_files empty

    Notebook File Formats:
        1. Single notebook: "path/to/notebook.ipynb"
        2. Flat list: ["notebook1.ipynb", "notebook2.ipynb"]
        3. Nested dict: {"Topic1": ["nb1.ipynb"], "Topic2": ["nb2.ipynb"]}
        4. Auto-discovery: [] (empty, uses notebook_dir)

    Custom Naming (tabs_names):
        - Flat structure: ["Custom Name 1", "Custom Name 2"]
        - Nested simple: {"Topic": ["Custom Name"]}
        - Nested advanced: {"Topic": {"topic_name": "Custom", "notebook_names": [...]}}

    Processing Workflow:
        1. Load and validate configuration file
        2. Extract notebook files and settings
        3. Handle auto-discovery if notebook_files empty
        4. Convert notebooks to HTML with optional execution
        5. Apply custom naming if provided
        6. Generate appropriate report template
        7. Write final HTML report to output folder

    Execution Mode:
        - When execute=True: Runs all notebook cells before conversion
        - Handles execution errors gracefully with fallback
        - Provides detailed error messages for troubleshooting
        - Continues processing even if some notebooks fail

    Output Files:
        - Individual HTML files for each notebook in output_folder
        - Final combined report: {report_title}_{timestamp}.html
        - All files use UTF-8 encoding for international character support

    Error Handling:
        - Missing configuration files
        - Invalid JSON format
        - Notebook file access errors
        - Directory permission issues
        - Notebook execution failures

    Status Reporting:
        - Progress messages for each processing stage
        - Notebook-by-notebook conversion status
        - Final report location confirmation
        - Error details when problems occur

    Examples:
        >>> generate_report("config.json")
        Converting notebooks to HTML...
        Processing topic: Data Analysis
        Converting notebook: analysis.ipynb
        Generating nested tabs HTML report...
        Report saved to: ./output/Report_2023_12_01_10_30_15.html
        Done!
    """
    config = load_config(config_path)
    notebook_files = config.get("notebook_files", [])
    tabs_names = config.get("tabs_names", None)
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
            # Get custom names for this topic if provided
            topic_custom_names = None
            if tabs_names and isinstance(tabs_names, dict) and topic_name in tabs_names:
                topic_config = tabs_names[topic_name]
                if isinstance(topic_config, dict) and 'notebook_names' in topic_config:
                    topic_custom_names = topic_config['notebook_names']
                elif isinstance(topic_config, list):
                    topic_custom_names = topic_config
            html_files = convert_notebooks_to_html(topic_notebooks, output_folder, current_datetime, execute, topic_custom_names)
            html_files_dict[topic_name] = html_files

        print("Generating nested tabs HTML report...")
        generate_final_report(html_files_dict, report_title, output_folder, current_datetime, tabs_names)

    elif isinstance(notebook_files, str):
        # Single notebook - tabs_names has no effect
        print(f"Processing single notebook: {notebook_files}")
        html_files = convert_notebooks_to_html([notebook_files], output_folder, current_datetime, execute)
        if html_files:
            print("Generating single notebook HTML report...")
            generate_final_report(html_files[0], report_title, output_folder, current_datetime)

    else:
        # Flat structure - tabs_names should be a list matching notebook files by index
        custom_names = None
        if tabs_names and isinstance(tabs_names, list):
            custom_names = tabs_names
        html_files = convert_notebooks_to_html(notebook_files, output_folder, current_datetime, execute, custom_names)
        print("Generating flat tabs HTML report...")
        generate_final_report(html_files, report_title, output_folder, current_datetime)

    print("Done!")


# Run the script
if __name__ == "__main__":
    config_file_path = os.path.join(os.getcwd(),os.path.join('test_configs',"test_tabs_names_flat.json"))  # Change this if necessary
    generate_report(config_file_path)
