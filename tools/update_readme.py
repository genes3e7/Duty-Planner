import os
import re
import sys


def validate_version(version_str):
    """
    Ensures the version string is present and follows a pattern like X.Y or X.Y.Z.
    """
    if not version_str:
        print("Error: Version argument is empty.")
        sys.exit(1)

    # Matches "3.10", "3.10.1", etc.
    pattern = r"^\d+\.\d+(?:\.\d+)?$"
    if not re.match(pattern, version_str):
        print(
            f"Error: Invalid version format '{version_str}'. "
            "Expected format like '3.10' or '3.10.1'."
        )
        sys.exit(1)


def update_readme(min_version, max_version):
    # 1. Validate Inputs
    validate_version(min_version)
    validate_version(max_version)

    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print(f"Error: {readme_path} not found.")
        sys.exit(1)

    # 2. Safe File Reading
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print(f"Error reading {readme_path}: {e}")
        sys.exit(1)

    # Determine version string format
    if min_version == max_version:
        version_string = min_version
    else:
        version_string = f"{min_version} - {max_version}"

    print(f"Updating README to support Python: {version_string}")

    # Regex to find: "**Prerequisites:** Python 3.10 or higher."
    pattern = r"(\*\*Prerequisites:\*\* Python ).*"

    if not re.search(pattern, content):
        # Fallback search if the line has changed slightly
        if not re.search(r"(Python )[\d\.]+", content):
            print("Critical: Could not find Python version definition in README.")
            sys.exit(1)

    # Use lambda to avoid backslash escaping issues in replacement string
    new_content = re.sub(pattern, lambda m: f"{m.group(1)}{version_string}", content)

    # 3. Safe File Writing
    if new_content != content:
        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("README.md updated successfully.")
        except OSError as e:
            print(f"Error writing to {readme_path}: {e}")
            sys.exit(1)
    else:
        print("README.md already up to date.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python update_readme.py <min_version> <max_version>")
        sys.exit(1)

    update_readme(sys.argv[1], sys.argv[2])
