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

`NN` is a two-digit week number: `week_01`, `week_02`, ..., `week_12`.

Students see only the PDFs. Keep every other file in the `sources/`
subdirectory of the week. Example of a week with problems and solutions:

```
seminars/week_01/
  problems.pdf                  # built PDFs, the only files outside sources/
  solutions.pdf
  sources/
    preamble.tex                # packages, macros, and the solution toggle
    problems.tex                # main file of problems.pdf
    problems.pdf.stamp          # stamp of problems.pdf (see below)
    solutions.tex               # main file of solutions.pdf
    solutions.pdf.stamp
    problems/
      01_medical_test.tex       # one file per problem
      02_student_network.tex
    figures/                    # images
```

- A main file is a `.tex` file with `\documentclass`. Put it directly in
  `sources/`. Its PDF goes to the week directory with the same base name
  (`sources/problems.tex` -> `problems.pdf`).
- A document must read only files from the `sources/` directory of its own
  week. Do not share files between weeks.
- Do not use spaces in file names.

## LaTeX structure

- Put each problem in its own file `sources/problems/NN_short_name.tex`.
  `NN` is the problem number in the problem sheet.
- A problem file holds the problem statement and, optionally, the solution
  in a `solution` environment:

  ```latex
  \label{prob:poisson-mle}
  Let $x_1, \ldots, x_N$ be an independent sample from $\Poiss(\lambda)$.
  Find the maximum likelihood estimate of $\lambda$.

  \begin{solution}
  ...
  \end{solution}
  ```

- A problem file has no preamble and no `\item`. Main files include it
  inside an `enumerate` list: `\item \input{problems/04_poisson_mle}`.
- Put packages and macros in `sources/preamble.tex`. Each main file starts
  with `\input{preamble}`, then calls `\hidesolutions` (problems only) or
  `\showsolutions` (problems with solutions).
- To refer to another problem or a figure, use `\label` and `\ref`. Do not
  write problem numbers by hand.
- Use PDF for course materials, not Markdown.

## Keeping PDFs up to date

Every committed PDF must be built from the committed version of its sources.

- After you clone the repository, run `pre-commit install` once. You also
  need TeX Live (`latexmk`).
- Commit only the sources. The pre-commit hook
  (`python3 scripts/pdf_freshness.py hook`) builds each stale document with
  `latexmk -pdf`, writes `sources/<name>.pdf.stamp`, and adds the PDF and the
  stamp to the same commit. The stamp records the git blob IDs of the PDF and of
  every source file the build read (`.tex`, figures, `.bib`, style files).
- The hook builds from the staged sources only. Stage every file that a
  document reads, or the commit fails.
- If LaTeX fails, the commit fails. Fix the error and commit again.
- To build without a commit, run `python3 scripts/pdf_freshness.py build`.
  For documents that are already tracked, it also stages the PDF and the
  stamp.
- Stage files with `git add` and then run `git commit` without paths.
  `git commit <paths>` commits through a temporary index, and the hook can
  fail with a stash conflict.
- Never edit a PDF or a stamp by hand, and never commit a PDF without its
  sources.

GitHub Actions (`.github/workflows/pdf.yml`) runs
`python3 scripts/pdf_freshness.py check` on every push to `main` and on every
pull request. It catches commits that skipped the hook. The check compares the
stamps with the committed files. It fails if a PDF is stale, if a document has
no PDF, if a PDF has no source, or if a file other than a built PDF is outside
`sources/`. CI does not run LaTeX.
