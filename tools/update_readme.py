import os
import re
import sys


def update_readme(min_version, max_version):
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print(f"Error: {readme_path} not found.")
        sys.exit(1)

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Format: "3.10 - 3.13" or just "3.10" if they are the same
    if min_version == max_version:
        version_string = min_version
    else:
        version_string = f"{min_version} - {max_version}"
        
    print(f"Updating README to support Python: {version_string}")

    # Regex to find: "**Prerequisites:** Python 3.10 or higher."
    # We capture the prefix to preserve bolding/formatting.
    pattern = r"(\*\*Prerequisites:\*\* Python ).*"

    if not re.search(pattern, content):
        print("Critical: Could not find 'Prerequisites: Python ...' line in README.")
        sys.exit(1)

    # Replace with: "**Prerequisites:** Python 3.10 - 3.13"
    new_content = re.sub(pattern, lambda m: f"{m.group(1)}{version_string}", content)

    if new_content != content:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md updated successfully.")
    else:
        print("README.md already up to date.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python update_readme.py <min_version> <max_version>")
        sys.exit(1)

    update_readme(sys.argv[1], sys.argv[2])
