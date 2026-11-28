"""Mastery-only source build.

The cleanup removed the per-module wheel split, so there is no ownership
filter and no generated extra set any more. ``pyproject.toml`` owns all
metadata; this shim exists only because the source tree still uses a
``setup.py`` entry point.
"""

from setuptools import setup

setup()
