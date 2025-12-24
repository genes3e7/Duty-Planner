"""
build.py
Script to freeze the application into a standalone executable.
"""

import os
import shutil

import customtkinter
import PyInstaller.__main__


def build():
    # Clean previous builds
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")

    ctk_path = os.path.dirname(customtkinter.__file__)
    separator = os.pathsep

    print("Building Duty Scheduler Pro...")

    PyInstaller.__main__.run(
        [
            "run.py",
            "--name=DutySchedulerPro",
            "--onefile",
            "--noconsole",
            f"--add-data={ctk_path}{separator}customtkinter",
            "--add-data=app:app",
            "--hidden-import=babel.numbers",
            "--hidden-import=openpyxl.cell._writer",
            "--clean",
        ]
    )

    print("Build Complete. Check /dist folder.")


if __name__ == "__main__":
    build()
