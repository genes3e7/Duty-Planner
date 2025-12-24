import os
from unittest.mock import patch

import build


@patch("PyInstaller.__main__.run")
@patch("shutil.rmtree")
@patch("os.path.exists")
def test_build_execution(mock_exists, mock_rmtree, mock_pyinstaller):
    """
    Test that the build script:
    1. Cleans up old directories.
    2. Calls PyInstaller with the correct entry point (run.py) and data.
    """
    # Simulate that build/ and dist/ directories exist
    mock_exists.return_value = True

    build.build()

    # Assert cleanup was attempted for 'dist' and 'build'
    assert mock_rmtree.call_count == 2

    # Assert PyInstaller was triggered
    mock_pyinstaller.assert_called_once()

    # Verify arguments passed to PyInstaller
    args = mock_pyinstaller.call_args[0][0]
    assert "run.py" in args
    assert "--name=DutySchedulerPro" in args

    # Verify app package inclusion using the correct OS separator
    expected_arg = f"--add-data=app{os.pathsep}app"
    assert expected_arg in args
    assert "--clean" in args
