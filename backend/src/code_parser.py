import os
import tempfile
import shutil
import ast
import csv
import json
from typing import Tuple, Dict, List

try:
    from git import Repo
except ImportError:
    raise ImportError("Please install gitpython: pip install gitpython")

def parse_python_imports(file_path: str, base_dir: str) -> List[str]:
    """Parse a Python file and return a list of relative file paths it imports from the same repo."""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            node = ast.parse(f.read(), filename=file_path)
        for n in ast.walk(node):
            if isinstance(n, ast.Import):
                for alias in n.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    imports.add(n.module.split('.')[0])
    except Exception:
        pass  # Ignore parse errors for now
    # Map import names to file paths
    rel_path = os.path.relpath(file_path, base_dir)
    rel_dir = os.path.dirname(rel_path)
    imported_files = []
    for imp in imports:
        # Try to resolve to a .py file in the repo
        possible = os.path.join(base_dir, rel_dir, imp + '.py')
        if os.path.isfile(possible):
            imported_files.append(os.path.relpath(possible, base_dir))
        else:
            # Try top-level
            possible = os.path.join(base_dir, imp + '.py')
            if os.path.isfile(possible):
                imported_files.append(os.path.relpath(possible, base_dir))
    return imported_files

def walk_repo_files(base_dir: str) -> List[str]:
    """Return a list of all .py files in the repo (relative paths)."""
    py_files = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.relpath(os.path.join(root, f), base_dir))
    return py_files

def analyze_repo(repo_url: str) -> Tuple[dict, str, dict]:
    """
    Clone the repo, analyze file structure and imports, and return:
    1. JSON structure of file usage
    2. CSV string with file path and code
    3. Lookup dict: file -> list of files that use it
    """
    temp_dir = tempfile.mkdtemp()
    try:
        Repo.clone_from(repo_url, temp_dir)
        py_files = walk_repo_files(temp_dir)
        file_structure = {}
        usage_lookup = {f: [] for f in py_files}
        imports_map = {}
        # Build import relationships
        for f in py_files:
            abs_path = os.path.join(temp_dir, f)
            imported = parse_python_imports(abs_path, temp_dir)
            imports_map[f] = imported
            for imp in imported:
                if imp in usage_lookup:
                    usage_lookup[imp].append(f)
        # Build file structure JSON
        for f in py_files:
            file_structure[f] = {
                'imports': imports_map[f],
                'used_by': usage_lookup[f]
            }
        # Build CSV
        csv_rows = [['relative_path', 'code']]
        for f in py_files:
            abs_path = os.path.join(temp_dir, f)
            try:
                with open(abs_path, 'r', encoding='utf-8') as code_file:
                    code = code_file.read()
            except Exception:
                code = ''
            csv_rows.append([f, code])
        csv_str = ''
        for row in csv_rows:
            csv_str += '"' + row[0].replace('"', '""') + '","' + row[1].replace('"', '""') + '"\n'
        return file_structure, csv_str, usage_lookup
    finally:
        shutil.rmtree(temp_dir)

# Example usage:
file_structure, csv_str, usage_lookup = analyze_repo('https://github.com/Red-Hat-AI-Innovation-Team/mini_trainer.git')
# print(json.dumps(file_structure, indent=2))
# print(csv_str)
# print(json.dumps(usage_lookup, indent=2))
# Save the file_structure, csv_str, and usage_lookup to disk
with open("file_structure.json", "w", encoding="utf-8") as f_json:
    json.dump(file_structure, f_json, indent=2)

with open("repo_code.csv", "w", encoding="utf-8") as f_csv:
    f_csv.write(csv_str)

with open("usage_lookup.json", "w", encoding="utf-8") as f_lookup:
    json.dump(usage_lookup, f_lookup, indent=2)
