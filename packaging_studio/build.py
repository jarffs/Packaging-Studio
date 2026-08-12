"""Download and register Python wheels for a Blender extension build.

Optional: SVG import works with only the standard library. PDF import needs
PyMuPDF. Run inside Blender::

    blender -b -P packaging_studio/build.py

Adapted from the MolecularNodes / blender_enhanced_svg build scripts.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Union

import bpy

ADDON_NAME = "packaging_studio"
TOML_PATH = f"./{ADDON_NAME}/blender_manifest.toml"
WHL_PATH = f"./{ADDON_NAME}/wheels"

# PyMuPDF enables PDF import. lxml is optional (stdlib XML is the default).
required_packages = ["pymupdf"]


def run_python(args: Union[str, List[str]]):
    if isinstance(args, str):
        args = args.split(" ")
    subprocess.run([sys.executable, *args], check=True)


@dataclass
class Platform:
    pypi_suffix: str
    metadata: str


windows_x64 = Platform(pypi_suffix="win_amd64", metadata="windows-x64")
linux_x64 = Platform(pypi_suffix="manylinux2014_x86_64", metadata="linux-x64")
macos_arm = Platform(pypi_suffix="macosx_12_0_arm64", metadata="macos-arm64")

build_platforms = [windows_x64, linux_x64, macos_arm]


def download_whls(platforms, packages=required_packages, python_version="3.11"):
    if isinstance(platforms, Platform):
        platforms = [platforms]
    os.makedirs(WHL_PATH, exist_ok=True)
    for platform in platforms:
        run_python(
            f"-m pip download {' '.join(packages)} --dest {WHL_PATH} "
            f"--only-binary=:all: --python-version {python_version} "
            f"--platform {platform.pypi_suffix}"
        )


def build_extension(split: bool = True) -> None:
    command = (
        f"{bpy.app.binary_path} --command extension build "
        f"--source-dir {ADDON_NAME} --output-dir ."
    )
    if split:
        command += " --split-platforms"
    subprocess.run(command.split(" "), check=True)


def main():
    download_whls(build_platforms)
    build_extension()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Build failed: {e}", file=sys.stderr)
        sys.exit(1)
