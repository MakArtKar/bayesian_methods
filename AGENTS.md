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
- In a main file with solutions, start each problem on a new page: put
  `\clearpage` before each `\item` except the first.
- Put packages and macros in `sources/preamble.tex`. Each main file starts
  with `\input{preamble}`, then calls `\hidesolutions` (problems only) or
  `\showsolutions` (problems with solutions).
- To refer to another problem or a figure, use `\label` and `\ref`. Do not
  write problem numbers by hand.
- Use PDF for course materials, not Markdown.

## Solutions

Write the text in Simplified Technical English: short sentences, one fact
for each sentence, active voice, and one term for each concept. A solution
is mainly formulas and transitions. Use text only to explain a transition,
and keep it short.

### Parts of a solution

Start each part with `\solpart{<name>}`. It prints the name as a heading.
Use these parts, in this order:

1. `Interpretation` (optional). Add it only when the statement is in words.
   Define the random variables, give only the values from the statement,
   and state what to find. Do not calculate derived values here, for
   example complements. Calculate them in the step that needs them.
2. `Idea`. Explain the method with abstract variables. Give each general
   rule as a formula. Underline the most important rule with `\uline`.
   Put each example in a `solexample` block. Apply the method to the
   problem in the `Solution`, not in the `Idea`. If a problem extends the
   method of an earlier problem, say so.
3. `Solution`. Give the full derivation in steps:
   `\solstep{Step N. <action>.}`. If the `Idea` has numbered steps, name
   the step: `\solstep{Step 2 (Idea 2). Numerator: $G = \{P, T\}$.}`. If
   the problem asks several questions, make one subproblem for each
   question with `\solsubproblem{(a) Find X.}`. Put shared work, for
   example a joint distribution, in its own `\solsubproblem` before (a).
   Reuse the results of earlier subproblems.
4. `Conclusion` (optional). Give the practical meaning of the result or its
   relation to other problems. Use a list for several points.

### Derivations

- Write derivations as `align*` chains, one transition for each line: a
  rule, a complement ($1 - p$), a substitution of values, an arithmetic
  result, or a simplification. Show the products before their sum.
- Put the reason for a transition on the line that starts with its `=`:
  `&= ... && \text{(parent of $T$: $A$)}`. Do not put a reason on a
  continuation line. A line with a reason has only one `=`. Give a reason
  for each line, except for arithmetic.
- If a line uses an earlier result, name its step, for example
  `\text{(Step 3)}` or `\text{((b), Step 5)}`.
- If a line is too wide, put the left side on its own line
  (`&p(T = 1) \\ &= ...`) or continue it with `&\qquad \cdot ...`.
- Do not repeat in words what a formula already shows.

### Probabilities in a causal graph

To find a probability in a causal graph, use this method:

1. Reduce the question to joint distributions:
   `p(G_x | G_y) = p(G_x, G_y) / p(G_y)`.
2. For each joint distribution `p(G)`, write the joint distribution of all
   variables with the chain rule. The factor of a node `X` is
   `p(X | parents of X)`. Keep it if `X` is in `G` or a path goes from `X`
   to `G`. Else strike it out with `\strike`.
3. Sum the product of the kept factors over the kept variables that are
   not in `G`. Move the factors that do not depend on a summation variable
   out of its sum, then calculate.

Find each numerator and denominator separately with this method. Do not
calculate intermediate conditional probabilities.

### Figures and examples

- For each `p(G)` in the `Solution`, draw the graph of the problem before
  the formula. Fill the nodes of `G` with blue, and add a legend for them.
- Give each given factor its own color (`\colorlet` in `preamble.tex`).
  Use the same color for the factor in the formulas, for the border of the
  source, and for the arrows into the node.
- Mark a struck-out factor with a red cross: on the node for a source, or
  on the arrows into the node (`\edgecross`). Draw the crosses on top of
  the colors.
- Make a macro for a graph that the solution draws many times, for example
  `\crossgraph`.

### Macros

`sources/preamble.tex` of week 1 defines these macros:

| Macro | Use |
| --- | --- |
| `\showsolutions`, `\hidesolutions` | Show or hide the `solution` environments. |
| `\solpart`, `\solstep`, `\solsubproblem` | Parts, steps, and subproblems of a solution. |
| `solexample` | A pale block with a line on the left for an example. |
| `\strike` | A red strike over a factor, on top of its color. |
| `\edgecross` | A red cross on an arrow, in the frame of the arrow. |
| `\crossgraph` | The graph of Problem 2 with the state of each node. |
| `\uline` | Underline a key rule (package `ulem`). |

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
