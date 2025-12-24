import os
import re
import sys


def validate_version(version_str):
    """
    Validate that `version_str` is non-empty and matches the "X.Y" or "X.Y.Z" version format.
    
    If `version_str` is empty or does not match the expected pattern, an error message is printed and the process exits with status code 1.
    
    Parameters:
        version_str (str): Version string to validate (e.g., "3.10" or "3.10.1").
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
    """
    Update README.md's Python prerequisites line to the specified version or range.
    
    Validates the provided version strings, reads README.md, locates a line beginning with "**Prerequisites:** Python " (with a fallback search for any "Python <version>" occurrence), and replaces the existing version text with either a single version or a range "min_version - max_version". Writes the file back only if changes are made.
    
    Parameters:
        min_version (str): Minimum Python version string in the form "X.Y" or "X.Y.Z".
        max_version (str): Maximum Python version string in the form "X.Y" or "X.Y.Z".
    
    Errors:
        Exits with status code 1 (via sys.exit(1)) on invalid version formats, missing README.md, unreadable or unwritable README.md, or when no Python version definition can be found in the file.
    """
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