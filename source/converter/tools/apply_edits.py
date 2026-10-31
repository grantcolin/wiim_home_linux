"""Apply source edits with deleted text represented only by SHA-256 hashes.

No original QML is embedded. The tested installer is verified separately;
each edit additionally checks the exact bytes it is about to replace.
"""
import hashlib
import json
import sys
from pathlib import Path


def apply_edits(manifest, patch_name, root):
    for filename, hunks in manifest[patch_name].items():
        path = root / filename
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        changes = []
        for hunk in hunks:
            length = hunk["length"]
            matches = [i for i in range(len(lines) - length + 1)
                       if hashlib.sha256("".join(lines[i:i + length]).encode()).hexdigest() == hunk["sha256"]]
            if len(matches) != 1:
                raise SystemExit("Patch review required: %s / %s: expected one context hash match, got %d" % (patch_name, filename, len(matches)))
            changes.extend((matches[0] + edit["line"], edit) for edit in hunk["edits"])
        for start, edit in sorted(changes, key=lambda item: item[0], reverse=True):
            count = edit["remove"]
            insertion = edit.get("insert")
            if insertion is None:
                insertion = (Path(sys.argv[1]).parent / edit["insert_file"]).read_text(encoding="utf-8")
            lines[start:start + count] = insertion.splitlines(keepends=True)
        path.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    apply_edits(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2], Path(sys.argv[3]))
