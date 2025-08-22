# generate_streamlit_project_summary.py

import ast
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
APP_FILE = PROJECT_ROOT / "app.py"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
OUTPUT_FILE = PROJECT_ROOT / "project_summary.json"

def extract_requirements():
    reqs = []
    if REQUIREMENTS_FILE.exists():
        with open(REQUIREMENTS_FILE, "r") as f:
            for line in f.readlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    reqs.append(line)
    return reqs

def parse_streamlit_app():
    with open(APP_FILE, "r") as f:
        tree = ast.parse(f.read())
    inputs = []
    openai_calls = []
    processing_functions = []
    output_keywords = []

    for node in ast.walk(tree):
        # Streamlit widget calls (main_only)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            parent = node.func.value
            if isinstance(parent, ast.Name) and parent.id == "st":
                widget = node.func.attr
                if widget in {
                    "file_uploader",
                    "text_input",
                    "number_input",
                    "text_area",
                    "selectbox",
                    "multiselect",
                    "date_input",
                }:
                    inputs.append(widget)

            # OpenAI calls
            if isinstance(parent, ast.Name) and parent.id.lower().startswith("openai"):
                openai_calls.append(ast.unparse(node))

        # Detect user-defined functions that may perform processing
        if isinstance(node, ast.FunctionDef):
            processing_functions.append(node.name)

        # Detect PDF or plot generation usage
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr.lower() in {"savefig", "to_pdf", "pdfwriter"}:
                output_keywords.append(ast.unparse(node))

    return {
        "inputs": list(set(inputs)),
        "openai_usage": list(set(openai_calls)),
        "processing_functions": processing_functions,
        "output_generation_calls": output_keywords,
    }

def main():
    summary = parse_streamlit_app()
    summary["dependencies"] = extract_requirements()

    with open(OUTPUT_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Project summary written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
