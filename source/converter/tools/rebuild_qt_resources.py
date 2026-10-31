#!/usr/bin/env python3
"""Rebuild the PyQt resource module from the patched runtime QML tree."""
import importlib
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PySide6.QtCore import QDir, QFile, QIODevice


def resource_paths(directory=":/"):
    paths = []
    qdir = QDir(directory)
    flags = QDir.Filter.NoDotAndDotDot | QDir.Filter.AllEntries
    for name in qdir.entryList(flags, QDir.SortFlag.Name):
        resource_path = directory + "/" + name
        if QDir(resource_path).exists():
            paths.extend(resource_paths(resource_path))
        else:
            paths.append(resource_path)
    return paths


def relative_resource_path(resource_path):
    return resource_path[3:] if resource_path.startswith("://") else resource_path[2:]


def source_path(app, relative_path):
    if relative_path.startswith("qml/"):
        return app / "Qml" / relative_path[4:]
    return app / relative_path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: rebuild_qt_resources.py <app-dir>")
    app = Path(sys.argv[1]).resolve()
    resource_dir = app / "resources"
    sys.path.insert(0, str(resource_dir))
    importlib.import_module("app_rc")

    staging = resource_dir / ".qrc-rebuild"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    qrc_entries = []
    for qrc_path in resource_paths():
        relative = relative_resource_path(qrc_path)
        source = source_path(app, relative)
        if not source.is_file():
            source = staging / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            resource_file = QFile(qrc_path)
            if not resource_file.open(QIODevice.OpenModeFlag.ReadOnly):
                raise RuntimeError("cannot read original resource: %s" % qrc_path)
            source.write_bytes(bytes(resource_file.readAll()))
        qrc_entries.append((relative, source))

    qrc_file = staging / "app.qrc"
    lines = ["<RCC><qresource prefix=\"/\">"]
    for relative, source in qrc_entries:
        lines.append('<file alias="%s">%s</file>' % (escape(relative), escape(str(source))))
    lines.append("</qresource></RCC>")
    qrc_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    generated = staging / "app_rc.py"
    subprocess.run([os.environ.get("RCC", "rcc"), "-g", "python", "-o", str(generated), str(qrc_file)], check=True)
    source_text = generated.read_text(encoding="utf-8").replace("from PySide2 import QtCore", "from PyQt6 import QtCore")
    source_text = source_text.replace("from PySide6 import QtCore", "from PyQt6 import QtCore")
    generated.write_text(source_text, encoding="utf-8")
    py_compile.compile(str(generated), cfile=str(resource_dir / "app_rc.pyc"), doraise=True)
    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
