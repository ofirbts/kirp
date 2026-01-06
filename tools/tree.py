# python3 tools/tree.py

import os

EXCLUDE = {"venv", "__pycache__", ".git"}

def print_tree(start_path, prefix=""):
    items = [i for i in sorted(os.listdir(start_path)) if i not in EXCLUDE]
    for index, item in enumerate(items):
        path = os.path.join(start_path, item)
        connector = "└── " if index == len(items) - 1 else "├── "
        print(prefix + connector + item)
        if os.path.isdir(path):
            extension = "    " if index == len(items) - 1 else "│   "
            print_tree(path, prefix + extension)

if __name__ == "__main__":
    print_tree(".")
