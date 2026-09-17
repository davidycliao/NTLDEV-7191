# Take-home lab

Complete this lab independently at home: work through the examples, then attempt the **11 practice exercises**. Questions can be discussed **before class if time permits, or during TA hours**. In class, we only check the setup and open the first section.

The lab uses a supplied sample of **5,000 House of Commons speech contributions from 1945–2025**. No earlier lab is required; the data and variables needed for this exercise are provided here.

## Choose one format

- [Lab_Session_W2.R](Lab_Session_W2.R): open in RStudio or Positron and run the code section by section. The original explanations appear as comments, with space for your exercise answers.
- [Lab_Session_W2.qmd](Lab_Session_W2.qmd): the student handout, with explanations and executable R chunks. Open in RStudio or Positron and run the chunks in order.

The two files contain the same worked examples and unsolved exercises. Choose one file to keep your work in; you do not need to complete both. **Rendering the Quarto file is not required.** You can also [read the rendered student handout](Lab_Session_W2.md).

## Answer key

The answer key contains worked solutions to all **11 practice exercises**. Use it to check your work after attempting the exercises.

- [Read the answer key](Lab_Session_W2_Answers.md)
- [Quarto answer key](Lab_Session_W2_Answers.qmd)
- [R answer key](Lab_Session_W2_Answers.R)

Both executable answer-key files use the same packages, data, and working directory as the student versions.

## Install the R packages once

Use an R console, with R 4.1 or later (the examples use the native `|>` pipe):

```r
install.packages(c(
  "dplyr", "stringr", "ggplot2", "quanteda",
  "quanteda.textstats", "quanteda.textplots"
))
```

The `.R` companion does not require `knitr`. If running the `.qmd` setup chunk, also install `knitr` with `install.packages("knitr")`. To render the handout, install Quarto and both R packages with `install.packages(c("knitr", "rmarkdown"))`. Python, UDPipe, language models, and Wordfish are not needed for this lab.

## Open the folder and check the data path

Keep this folder structure together when moving or downloading the lab:

```text
W2/lab/
  README.md
  Lab_Session_W2.R
  Lab_Session_W2.qmd
  Lab_Session_W2.md
  Lab_Session_W2_Answers.R
  Lab_Session_W2_Answers.qmd
  Lab_Session_W2_Answers.md
  Lab_Session_W2_files/
  Lab_Session_W2_Answers_files/
  Data/
    hc_sample_1945_2025.rds
```

Set the **R working directory to `W2/lab`**, the folder containing the lab files and `Data/`. Opening a script alone does not necessarily change the working directory.

- In **RStudio**, use **Session → Set Working Directory → Choose Directory…** and select the `lab` folder inside `W2`.
- In **Positron**, open `W2/lab` as a folder and start/select an R session. Check the R working directory; if needed, use `setwd("/full/path/to/W2/lab")`, replacing the example with your actual folder path. The same `setwd()` command also works in RStudio. On Windows, use forward slashes, for example `setwd("C:/Users/YourName/Downloads/W2/lab")`.

Check the setup in the R console before starting:

```r
getwd()
file.exists("Data/hc_sample_1945_2025.rds")  # should return TRUE
```

Open your chosen `.R` or `.qmd` file. Run the package-loading and data-loading sections first, then continue in order. In a `.R` file, select a few complete lines and press **Command+Enter** on macOS or **Ctrl+Enter** on Windows/Linux. In a `.qmd` file, run one R chunk at a time. Read the output and inspect the plots before continuing; running the whole file at once does not complete the exercises for you.

## Workflow and questions

The worked examples cover string operations and regular expressions; metadata cleaning; corpus creation, subsetting and sentence reshaping; tokenization and multiword expressions; KWIC; collocations; DFMs and trimming; frequency plots, keyness, and a feature's frequency over time. The practice exercises ask you to reuse and adapt these operations.

Keep a short note of the section or exercise you reached and any choices or results you want to discuss. If you need help, bring the relevant code, the exact error or output, and what you expected to happen. Before-class discussion is subject to available time; TA hours are another opportunity to ask questions.

## Source and local packaging

Adapted for **National Taiwan University**, *Text as Data: Computational Methods for Social Science Research*, Week 2. Original teaching material: **Schoonvelde (2026)**, *QTA Lab 02: String Operations and Inspecting the House of Commons Corpus*. The source materials also acknowledge earlier lab materials by Stefan Müller. See the [course acknowledgments](../../README.md) for the full attribution.

The student and answer-key versions preserve the supplied analytical code, with course labels and introductory wording adapted for this course. The dataset is in `Data/`. The `.R` companions convert prose to comments and make rendering-only `knitr` setup conditional. Student exercises remain blank; the answer key provides the solutions. The rendered Markdown versions use figures in their corresponding `_files/` folders, which should be kept alongside the handouts.
