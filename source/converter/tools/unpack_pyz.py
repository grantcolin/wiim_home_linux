#!/usr/bin/env python3
"""Extract a PyInstaller PYZ into normal Python 3.9 .pyc paths."""
import pathlib, sys
from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

PY39_MAGIC = b'\x61\x0d\x0d\x0a' + b'\0' * 12
source, target = map(pathlib.Path, sys.argv[1:3])
carchive = CArchiveReader(str(source))
main = carchive.extract('main')
(target / 'main.pyc').parent.mkdir(parents=True, exist_ok=True)
(target / 'main.pyc').write_bytes(main if main.startswith(b'\x61\x0d\x0d\x0a') else PY39_MAGIC + main)
pyz_path = target.parent / 'PYZ.pyz'
pyz_path.parent.mkdir(parents=True, exist_ok=True)
pyz_path.write_bytes(carchive.extract('PYZ.pyz'))
pyz = ZlibArchiveReader(str(pyz_path), check_pymagic=False)
for name, entry in pyz.toc.items():
    data = pyz.extract(name, raw=True)
    if data is None:
        continue
    typecode = entry[0]
    rel = name.replace('.', '/')
    out = target / rel / '__init__.pyc' if typecode == 1 else target / (rel + '.pyc')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data if data.startswith(b'\x61\x0d\x0d\x0a') else PY39_MAGIC + data)
print(f'extracted {len(pyz.toc)} modules to {target}')
