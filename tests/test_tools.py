import pytest

from tools import update_readme


def test_validate_version_valid(capsys):
    """Test that valid version strings pass silently."""
    update_readme.validate_version("3.10")
    update_readme.validate_version("3.13.1")
    # No exception raised


def test_validate_version_invalid(capsys):
    """Test that invalid version strings trigger system exit."""
    with pytest.raises(SystemExit):
        update_readme.validate_version("3")
    captured = capsys.readouterr()
    assert "Error: Invalid version format" in captured.out


def test_update_readme_success(tmp_path, capsys):
    """Test updating a README file with a new version range."""
    # Create a dummy README in the temp directory
    d = tmp_path / "repo"
    d.mkdir()
    p = d / "README.md"
    original_text = "Some text.\n**Prerequisites:** Python 3.9\nMore text."
    p.write_text(original_text, encoding="utf-8")

    # Run update
    update_readme.update_readme("3.10", "3.12", file_path=str(p))

    # Verify content changed
    new_text = p.read_text(encoding="utf-8")
    assert "**Prerequisites:** Python 3.10 - 3.12" in new_text

    # Verify output
    captured = capsys.readouterr()
    assert "README.md updated successfully" in captured.out


def test_update_readme_preserves_suffix(tmp_path):
    """Test that 'or higher' suffix is preserved."""
    p = tmp_path / "README.md"
    p.write_text("**Prerequisites:** Python 3.9 or higher.", encoding="utf-8")

    update_readme.update_readme("3.11", "3.11", file_path=str(p))

    new_text = p.read_text(encoding="utf-8")
    # Should result in "Python 3.11 or higher."
    assert "**Prerequisites:** Python 3.11 or higher." in new_text
