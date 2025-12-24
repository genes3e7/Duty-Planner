import os
import re
import sys


def validate_version(version_str):
    """
    Validate `version_str` is non-empty and matches "X.Y" or "X.Y.Z" format.

    If `version_str` is empty or does not match the expected pattern,
    an error message is printed and the process exits with status code 1.
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


def update_readme(min_version, max_version, file_path="README.md"):
    """
    Update README.md prerequisites with the supported Python version(s).

    Validates inputs, reads the README, locates the version definition line,
    and replaces it with the calculated range. Writes back only on change.
    Exits with status 1 on any error.
    """
    # 1. Validate Inputs
    validate_version(min_version)
    validate_version(max_version)

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        sys.exit(1)

    # 2. Safe File Reading
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print(f"Error reading {file_path}: {e}")
        sys.exit(1)

    # Determine version string format
    if min_version == max_version:
        version_string = min_version
    else:
        version_string = f"{min_version} - {max_version}"

    print(f"Updating README to support Python: {version_string}")

    # Regex captures:
    # Group 1: Prefix ("**Prerequisites:** Python ")
    # Group 2: Version Range (e.g. "3.10" or "3.10 - 3.12.1")
    # Group 3: Trailing text (e.g. " or higher.")
    pattern = (
        r"(\*\*Prerequisites:\*\* Python )"
        r"(\d+\.\d+(?:\.\d+)?(?: - \d+\.\d+(?:\.\d+)?)?)(.*)"
    )

    if not re.search(pattern, content):
        # Fallback check
        if not re.search(r"(Python )[\d\.]+", content):
            print("Critical: Could not find Python version definition in README.")
            sys.exit(1)

    # Insert new version string between Prefix (1) and Suffix (3)
    new_content = re.sub(
        pattern, lambda m: f"{m.group(1)}{version_string}{m.group(3)}", content
    )

    # 3. Safe File Writing
    if new_content != content:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("README.md updated successfully.")
        except OSError as e:
            print(f"Error writing to {file_path}: {e}")
            sys.exit(1)
    else:
        print("README.md already up to date.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python update_readme.py <min_version> <max_version>")
        sys.exit(1)

    update_readme(sys.argv[1], sys.argv[2])
