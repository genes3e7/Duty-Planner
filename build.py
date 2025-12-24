"""
build.py
Script to freeze the application into a standalone executable.
"""
import os
import shutil
import PyInstaller.__main__
import customtkinter

# Clean previous builds
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

ctk_path = os.path.dirname(customtkinter.__file__)

# Determine the correct separator for --add-data (semicolon for Windows, colon for POSIX)
# os.pathsep returns ':' on Linux/Mac and ';' on Windows
separator = os.pathsep

print("Building Duty Scheduler Pro...")

PyInstaller.__main__.run([
    'gui.py',
    '--name=DutySchedulerPro',
    '--onefile',
    '--noconsole',
    # Fix: Use dynamic separator for cross-platform compatibility
    f'--add-data={ctk_path}{separator}customtkinter',
    '--hidden-import=babel.numbers',
    '--hidden-import=openpyxl.cell._writer',
    '--clean'
])

print("Build Complete. Check /dist folder.")
