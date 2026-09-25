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

- After you clone the repository, run `pre-commit install` once. You also
  need TeX Live (`latexmk`).
- Commit only the sources. The pre-commit hook
  (`python3 scripts/pdf_freshness.py hook`) builds each stale document with
  `latexmk -pdf`, writes `<name>.pdf.stamp`, and adds the PDF and the stamp
  to the same commit. The stamp records the git blob IDs of the PDF and of
  every source file the build read (`.tex`, figures, `.bib`, style files).
- The hook builds from the staged sources only. Stage every file that a
  document reads, or the commit fails.
- If LaTeX fails, the commit fails. Fix the error and commit again.
- To build without a commit, run `python3 scripts/pdf_freshness.py build`.
- Never edit a PDF or a stamp by hand, and never commit a PDF without its
  sources.

GitHub Actions (`.github/workflows/pdf.yml`) runs on every push to `main` and
on every pull request. It catches commits that skipped the hook:

- `python3 scripts/pdf_freshness.py check` compares the stamps with the
  committed files. It fails if a PDF is stale, if a document has no PDF, or if
  a PDF has no source.
- A second job builds all documents to make sure that the sources compile.
