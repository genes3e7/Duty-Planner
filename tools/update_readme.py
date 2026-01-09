import os
import re
import sys
from typing import List


def get_passing_versions(artifacts_dir: str) -> List[str]:
    """Scans the directory for python_version_X.Y.txt files."""
    versions = []
    if not os.path.exists(artifacts_dir):
        return []

    for filename in os.listdir(artifacts_dir):
        match = re.match(r"python_version_(\d+\.\d+)\.txt", filename)
        if match:
            versions.append(match.group(1))

    return sorted(versions, key=lambda s: [int(u) for u in s.split(".")])


def update_readme(versions: List[str]):
    """Updates the badge in README.md."""
    if not versions:
        print("No passing versions found.")
        return

    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print("README.md not found.")
        return

    min_ver = versions[0]
    max_ver = versions[-1]

    if min_ver == max_ver:
        ver_str = min_ver
    else:
        ver_str = f"{min_ver}_to_{max_ver}"

    badge_pattern = r"(https://img\.shields\.io/badge/python-)([\d\._a-zA-Z]+)(-blue)"
    replacement = f"\\g<1>{ver_str}\\g<3>"

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(badge_pattern, replacement, content)

    if content != new_content:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated README.md with versions: {min_ver} - {max_ver}")
    else:
        print("README.md badge is already up to date.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_readme.py <artifacts_dir>")
        sys.exit(1)

    artifacts_dir = sys.argv[1]
    versions = get_passing_versions(artifacts_dir)
    update_readme(versions)
