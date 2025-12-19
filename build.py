"""
build.py
Packages the Python scripts into a standalone .exe file using PyInstaller.
"""
import PyInstaller.__main__
import customtkinter
import os
import shutil

# Clean
if os.path.exists('dist'): shutil.rmtree('dist')
if os.path.exists('build'): shutil.rmtree('build')

ctk_path = os.path.dirname(customtkinter.__file__)

PyInstaller.__main__.run([
    'gui.py',
    '--name=DutySchedulerPro',
    '--onefile',
    '--noconsole',
    f'--add-data={ctk_path};customtkinter',
    '--hidden-import=babel.numbers',
    '--clean'
])
