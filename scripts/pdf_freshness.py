#!/usr/bin/env python3
"""Build LaTeX documents and check that committed PDFs match their sources.

A document is a `.tex` file with `\\documentclass` under one of the content
directories. `build` compiles `<dir>/<name>.tex` into `<dir>/<name>.pdf` and
writes `<dir>/<name>.pdf.stamp`. The stamp records the git blob ID of the PDF
and of every source file in the repository that the build read.

`check` compares the stamps with the git index. It does not run LaTeX, so it
is fast and works in CI.

`hook` is the pre-commit hook. It builds the stale documents that are in the
git index, stages their PDFs and stamps, and then runs `check`.

Usage:
    python3 scripts/pdf_freshness.py build          # build stale documents
    python3 scripts/pdf_freshness.py build --all    # build all documents
    python3 scripts/pdf_freshness.py build FILE.tex [FILE.tex ...]
    python3 scripts/pdf_freshness.py check
    python3 scripts/pdf_freshness.py hook
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

CONTENT_DIRS = ("lectures", "seminars", "homeworks")
STAMP_SUFFIX = ".stamp"
DOCUMENTCLASS_RE = re.compile(rb"^[ \t]*\\documentclass", re.MULTILINE)

ROOT = Path(
    subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
)


def git(*args: str, input: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, input=input
    ).stdout


def index_blobs() -> dict[str, str]:
    """Map each path in the git index (stage 0) to its blob ID."""
    blobs = {}
    for entry in git("ls-files", "-s", "-z").split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        _mode, blob, stage = meta.split()
        if stage == b"0":
            blobs[path.decode()] = blob.decode()
    return blobs


def in_content_dir(path: str) -> bool:
    return PurePosixPath(path).parts[0] in CONTENT_DIRS


def is_document(content: bytes) -> bool:
    return DOCUMENTCLASS_RE.search(content) is not None


def stamp_path(tex: str) -> str:
    return str(PurePosixPath(tex).with_suffix(".pdf")) + STAMP_SUFFIX


def read_stamp(content: str) -> dict[str, str]:
    """Parse stamp lines `<blob>  <path relative to the stamp directory>`."""
    entries = {}
    for line in content.splitlines():
        if line.strip():
            blob, path = line.split(maxsplit=1)
            entries[path] = blob
    return entries


def check() -> int:
    blobs = index_blobs()
    tracked = [p for p in blobs if in_content_dir(p)]
    tex_files = [p for p in tracked if p.endswith(".tex")]
    contents = dict(
        zip(tex_files, cat_blobs([blobs[p] for p in tex_files]))
    )
    documents = [p for p in tex_files if is_document(contents[p])]

    errors = []
    expected_pdfs = set()
    expected_stamps = set()
    for tex in documents:
        tex_path = PurePosixPath(tex)
        pdf = str(tex_path.with_suffix(".pdf"))
        stamp = stamp_path(tex)
        expected_pdfs.add(pdf)
        expected_stamps.add(stamp)
        if pdf not in blobs or stamp not in blobs:
            errors.append(f"{tex}: PDF or stamp is not committed")
            continue
        entries = read_stamp(git("cat-file", "blob", blobs[stamp]).decode())
        stale = []
        for rel, blob in entries.items():
            path = str(tex_path.parent / rel)
            if path not in blobs:
                stale.append(f"{path} is not committed")
            elif blobs[path] != blob:
                stale.append(path)
        if tex_path.name not in entries or PurePosixPath(pdf).name not in entries:
            stale.append(stamp)
        if stale:
            errors.append(f"{tex}: PDF is stale ({', '.join(sorted(stale))})")

    for path in tracked:
        if path.endswith(".pdf") and path not in expected_pdfs:
            errors.append(f"{path}: PDF has no LaTeX source")
        if path.endswith(STAMP_SUFFIX) and path not in expected_stamps:
            errors.append(f"{path}: stamp has no LaTeX source")

    if errors:
        print("PDFs do not match their sources:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        print(
            "Stage the missing sources. Then run "
            "`python3 scripts/pdf_freshness.py build` and stage the PDFs and "
            "stamps, or commit again to let the pre-commit hook do it.",
            file=sys.stderr,
        )
        return 1
    print(f"All {len(documents)} PDFs match their sources.")
    return 0


def cat_blobs(blob_ids: list[str]) -> list[bytes]:
    """Read many blobs with one `git cat-file --batch` call."""
    if not blob_ids:
        return []
    out = git("cat-file", "--batch", input="\n".join(blob_ids).encode() + b"\n")
    contents = []
    pos = 0
    for _ in blob_ids:
        header_end = out.index(b"\n", pos)
        size = int(out[pos:header_end].split()[2])
        contents.append(out[header_end + 1 : header_end + 1 + size])
        pos = header_end + 1 + size + 1
    return contents


def parse_deps(deps_file: Path, cwd: Path) -> list[Path]:
    """Return the repository files listed in a `latexmk -deps-out` file."""
    deps = []
    for line in deps_file.read_text().splitlines():
        line = line.strip().removesuffix("\\").strip()
        if not line or line.startswith("#") or line.endswith(":"):
            continue
        path = (cwd / line).resolve()
        if path.is_relative_to(ROOT) and path.is_file():
            deps.append(path)
    return deps


def build_one(tex: Path) -> None:
    cwd = tex.parent
    pdf = tex.with_suffix(".pdf")
    print(f"Building {tex.relative_to(ROOT)}")
    if shutil.which("latexmk") is None:
        raise SystemExit("latexmk is not installed; install TeX Live")
    with tempfile.TemporaryDirectory() as tmp:
        deps_file = Path(tmp) / "deps.mk"
        result = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-deps-out={deps_file}",
                tex.name,
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            raise SystemExit(f"latexmk failed for {tex.relative_to(ROOT)}")
        deps = set(parse_deps(deps_file, cwd))
    deps.update({tex, pdf})

    lines = []
    for dep in sorted(deps):
        if not dep.is_relative_to(cwd):
            raise SystemExit(
                f"{tex.relative_to(ROOT)} reads {dep.relative_to(ROOT)}, "
                "which is outside its directory"
            )
        blob = git("hash-object", str(dep)).decode().strip()
        lines.append(f"{blob}  {dep.relative_to(cwd).as_posix()}\n")
    Path(str(pdf) + STAMP_SUFFIX).write_text("".join(lines))


def working_tree_documents(include_untracked: bool = True) -> list[Path]:
    """Return tracked and, optionally, untracked (not ignored) documents."""
    args = ["ls-files", "--cached", "-z"]
    if include_untracked:
        args += ["--others", "--exclude-standard"]
    files = git(*args).decode()
    documents = []
    for path in sorted(set(files.split("\0"))):
        full = ROOT / path
        if (
            path.endswith(".tex")
            and in_content_dir(path)
            and full.is_file()
            and is_document(full.read_bytes())
        ):
            documents.append(full)
    return documents


def is_stale(tex: Path) -> bool:
    stamp = Path(str(tex.with_suffix(".pdf")) + STAMP_SUFFIX)
    if not stamp.is_file():
        return True
    for rel, blob in read_stamp(stamp.read_text()).items():
        path = tex.parent / rel
        if not path.is_file() or git("hash-object", str(path)).decode().strip() != blob:
            return True
    return False


def build(files: list[str], build_all: bool) -> int:
    if files:
        documents = [Path(f).resolve() for f in files]
    else:
        documents = working_tree_documents()
        if not build_all:
            documents = [tex for tex in documents if is_stale(tex)]
    if not documents:
        print("Nothing to build.")
    for tex in documents:
        build_one(tex)
    return 0


def hook() -> int:
    documents = [
        tex
        for tex in working_tree_documents(include_untracked=False)
        if is_stale(tex)
    ]
    for tex in documents:
        build_one(tex)
        pdf = tex.with_suffix(".pdf")
        git("add", "--", str(pdf), str(pdf) + STAMP_SUFFIX)
    return check()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build", help="build PDFs and write stamps")
    build_parser.add_argument("files", nargs="*", help="documents to build")
    build_parser.add_argument(
        "--all", action="store_true", help="build all documents, not only stale"
    )
    sub.add_parser("check", help="check that committed PDFs are up to date")
    sub.add_parser("hook", help="build and stage stale PDFs, then check")
    args = parser.parse_args()
    if args.command == "check":
        return check()
    if args.command == "hook":
        return hook()
    return build(args.files, args.all)


if __name__ == "__main__":
    sys.exit(main())
