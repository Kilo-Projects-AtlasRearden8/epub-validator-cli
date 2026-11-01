"""EPUB validator for KDP upload.

A local-only CLI that checks an EPUB file for structural integrity,
navigation correctness, and common errors that Amazon KDP rejects.

All processing happens on the local filesystem. No network access, no API
keys, no telemetry.
"""

__version__ = "1.0.0"
