#!/usr/bin/env python3
"""Build LaTeX documents and check that committed PDFs match their sources.

Each week directory (`<content dir>/week_NN/`) has this layout:

    week_NN/<name>.pdf                  # built PDFs, the only files for students
    week_NN/sources/<name>.tex          # main file of a document
    week_NN/sources/<name>.pdf.stamp    # stamp of <name>.pdf
    week_NN/sources/...                 # all other sources

A document is a `.tex` file with `\\documentclass` directly in `sources/`.
`build` compiles `sources/<name>.tex` into `<name>.pdf` and writes
`sources/<name>.pdf.stamp`. The stamp records the git blob ID of the PDF and
of every source file that the build read. If the `.tex` file is tracked,
`build` also stages the PDF and the stamp.

`check` compares the stamps with the git index and checks the layout. It does
not run LaTeX, so it is fast and works in CI.

`hook` is the pre-commit hook. It builds the stale documents that are in the
git index, and then runs `check`.

Usage:
    python3 scripts/pdf_freshness.py build          # build stale documents
    python3 scripts/pdf_freshness.py build --all    # build all documents
    python3 scripts/pdf_freshness.py build FILE.tex [FILE.tex ...]
    python3 scripts/pdf_freshness.py check
    python3 scripts/pdf_freshness.py hook
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

CONTENT_DIRS = ("lectures", "seminars", "homeworks")
SOURCES_DIR = "sources"
STAMP_SUFFIX = ".pdf.stamp"
WEEK_RE = re.compile(r"week_\d{2}")
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


def blob_id(path: Path) -> str:
    return git("hash-object", "--", str(path)).decode().strip()


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


def in_content_dir(path: str) -> bool:
    return PurePosixPath(path).parts[0] in CONTENT_DIRS


def is_document(content: bytes) -> bool:
    return DOCUMENTCLASS_RE.search(content) is not None


def in_sources(path: PurePosixPath) -> bool:
    """Return True if the path is inside `<content>/week_NN/sources/`."""
    parts = path.parts
    return (
        len(parts) > 3
        and parts[0] in CONTENT_DIRS
        and WEEK_RE.fullmatch(parts[1]) is not None
        and parts[2] == SOURCES_DIR
    )


def is_main_file(path: PurePosixPath) -> bool:
    """Return True if the path has the form `<content>/week_NN/sources/*.tex`."""
    return in_sources(path) and len(path.parts) == 4 and path.suffix == ".tex"


# The functions below take the path of a main file,
# `<content>/week_NN/sources/<name>.tex`, as a Path or a PurePosixPath.


def week_dir(tex):
    return tex.parent.parent


def pdf_path(tex):
    return week_dir(tex) / (tex.stem + ".pdf")


def stamp_path(tex):
    return tex.parent / (tex.stem + STAMP_SUFFIX)


def read_stamp(content: str) -> dict[str, str]:
    """Parse stamp lines `<blob>  <path relative to the week directory>`."""
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
    contents = dict(zip(tex_files, cat_blobs([blobs[p] for p in tex_files])))

    errors = []
    documents = []
    for path in tex_files:
        if not is_document(contents[path]):
            continue
        if is_main_file(PurePosixPath(path)):
            documents.append(PurePosixPath(path))
        else:
            errors.append(
                f"{path}: a main file must be in <content>/week_NN/sources/"
            )

    expected = set()
    for tex in documents:
        pdf, stamp = str(pdf_path(tex)), str(stamp_path(tex))
        expected.update({pdf, stamp})
        if pdf not in blobs or stamp not in blobs:
            errors.append(f"{tex}: PDF or stamp is not committed")
            continue
        entries = read_stamp(git("cat-file", "blob", blobs[stamp]).decode())
        stale = []
        for rel, blob in entries.items():
            path = str(week_dir(tex) / rel)
            if path not in blobs:
                stale.append(f"{path} is not committed")
            elif blobs[path] != blob:
                stale.append(path)
        required = {str(tex.relative_to(week_dir(tex))), pdf_path(tex).name}
        if not required <= entries.keys():
            stale.append(stamp)
        if stale:
            errors.append(f"{tex}: PDF is stale ({', '.join(sorted(stale))})")

    for path in tracked:
        if path in expected:
            continue
        if path.endswith(STAMP_SUFFIX):
            errors.append(f"{path}: stamp has no main file")
        elif not in_sources(PurePosixPath(path)):
            errors.append(
                f"{path}: only built PDFs can be outside "
                "<content>/week_NN/sources/"
            )

    if errors:
        print("PDF check failed:", file=sys.stderr)
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


def parse_deps(deps_file: Path, cwd: Path) -> set[Path]:
    """Return the repository files listed in a `latexmk -deps-out` file.

    Files that git ignores are build artifacts (for example, `comment.cut`),
    not sources, so they are skipped.
    """
    deps = set()
    for line in deps_file.read_text().splitlines():
        line = line.strip().removesuffix("\\").strip()
        if not line or line.startswith("#") or line.endswith(":"):
            continue
        path = (cwd / line).resolve()
        if path.is_relative_to(ROOT) and path.is_file():
            deps.add(path)
    if deps:
        ignored = subprocess.run(
            ["git", "check-ignore", "--stdin", "-z"],
            cwd=ROOT,
            input="\0".join(str(p) for p in deps).encode(),
            capture_output=True,
        ).stdout.decode()
        deps -= {Path(p) for p in ignored.split("\0") if p}
    return deps


def build_one(tex: Path) -> None:
    name = tex.relative_to(ROOT)
    if not is_main_file(PurePosixPath(name.as_posix())):
        raise SystemExit(f"{name}: a main file must be in <content>/week_NN/sources/")
    if shutil.which("latexmk") is None:
        raise SystemExit("latexmk is not installed; install TeX Live")
    print(f"Building {name}")
    sources, pdf = tex.parent, pdf_path(tex)
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
            cwd=sources,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            raise SystemExit(f"latexmk failed for {name}")
        deps = parse_deps(deps_file, sources)
    # latexmk writes the PDF next to the main file. Move it out of sources/.
    os.replace(sources / pdf.name, pdf)
    deps.discard(sources / pdf.name)

    lines = [f"{blob_id(pdf)}  {pdf.name}\n"]
    for dep in sorted(deps | {tex}):
        if not dep.is_relative_to(sources):
            raise SystemExit(
                f"{name} reads {dep.relative_to(ROOT)}, which is outside "
                f"{sources.relative_to(ROOT)}"
            )
        rel = dep.relative_to(week_dir(tex)).as_posix()
        lines.append(f"{blob_id(dep)}  {rel}\n")
    stamp = stamp_path(tex)
    stamp.write_text("".join(lines))
    # Stage the outputs of tracked documents. Otherwise the pre-commit hook
    # stashes them as unstaged changes, and the stash conflicts with the PDF
    # that the hook builds.
    if git("ls-files", "--", str(tex)):
        git("add", "--", str(pdf), str(stamp))


def working_tree_documents(include_untracked: bool = True) -> list[Path]:
    """Return tracked and, optionally, untracked (not ignored) main files."""
    args = ["ls-files", "--cached", "-z"]
    if include_untracked:
        args += ["--others", "--exclude-standard"]
    documents = []
    for path in sorted(set(git(*args).decode().split("\0"))):
        full = ROOT / path
        if (
            path
            and is_main_file(PurePosixPath(path))
            and full.is_file()
            and is_document(full.read_bytes())
        ):
            documents.append(full)
    return documents


def is_stale(tex: Path) -> bool:
    stamp = stamp_path(tex)
    if not stamp.is_file():
        return True
    for rel, blob in read_stamp(stamp.read_text()).items():
        path = week_dir(tex) / rel
        if not path.is_file() or blob_id(path) != blob:
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
    for tex in working_tree_documents(include_untracked=False):
        if is_stale(tex):
            build_one(tex)
    return check()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build", help="build PDFs and write stamps")
    build_parser.add_argument("files", nargs="*", help="main files to build")
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
