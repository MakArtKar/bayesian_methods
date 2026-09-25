# AGENTS.md

This repository holds the materials for a course on Bayesian methods.

## Language

Write everything in English: LaTeX sources, PDFs, code, comments, file
names, commit messages, and documentation.

## Repository layout

```
lectures/week_NN/     # lecture materials
seminars/week_NN/     # seminar materials
homeworks/week_NN/    # homework assignments
```

- `NN` is a two-digit week number: `week_01`, `week_02`, ..., `week_12`.
- Put all files for one week (sources, figures, PDFs) in that week's
  directory. Do not share files between weeks through relative paths.
- Put figures in a `figures/` subdirectory of the week directory.

## Document format

- Use PDF for course materials, not Markdown.
- Keep the LaTeX source for every PDF in the repository, so the PDF can be
  rebuilt and updated.
- Put each PDF next to its main `.tex` file, with the same base name
  (`seminar.tex` -> `seminar.pdf`).
- A document must read only files from its own week directory.
- Do not use spaces in file names.
- Commit only the sources, the final PDF, and its `.pdf.stamp` file. Build
  artifacts (`.aux`, `.log`, and so on) are in `.gitignore`.

## Keeping PDFs up to date

Every committed PDF must be built from the committed version of its sources.

- Build PDFs only with `python3 scripts/pdf_freshness.py build`. It builds
  all stale documents with `latexmk -pdf` and writes `<name>.pdf.stamp`. The
  stamp records the git blob IDs of the PDF and of every source file the build
  read (`.tex`, figures, `.bib`, style files).
- Commit the source change, the rebuilt PDF, and the stamp in the same commit.
- Never edit a PDF or a stamp by hand, and never commit a PDF without its
  sources.

`python3 scripts/pdf_freshness.py check` compares the stamps with the git
index. It fails if a PDF is stale, if a document has no PDF, or if a PDF has
no source. It runs:

- as a pre-commit hook. After you clone the repository, run
  `pre-commit install` once.
- in GitHub Actions (`.github/workflows/pdf.yml`) on every push to `main` and
  on every pull request. A second job builds all documents to make sure that
  the sources compile.
