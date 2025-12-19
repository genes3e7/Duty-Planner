"""
build.py
Script to freeze the application into a standalone executable.
"""
import PyInstaller.__main__
import customtkinter
import os
import shutil

# Clean previous builds
if os.path.exists('dist'): shutil.rmtree('dist')
if os.path.exists('build'): shutil.rmtree('build')

ctk_path = os.path.dirname(customtkinter.__file__)

print("Building Duty Scheduler Pro...")

PyInstaller.__main__.run([
    'gui.py',
    '--name=DutySchedulerPro',
    '--onefile',
    '--noconsole',
    f'--add-data={ctk_path};customtkinter',
    '--hidden-import=babel.numbers',
    '--hidden-import=openpyxl.cell._writer',
    '--clean'
])

print("Build Complete. Check /dist folder.")
