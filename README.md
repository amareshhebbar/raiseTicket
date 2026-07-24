# IssueLoop

Finds failing tests in a repo, splits each failure into independent
tickets, stores them, hands them out one at a time.

That's it. No fixing. No PRs. No auto-anything past detection. This is
the "notice the bug" half of a bigger pipeline — not the "fix the bug"
half.

![license](https://img.shields.io/badge/license-MIT-blue)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![status](https://img.shields.io/badge/status-alpha-orange)

---

## Why

Bugs in OSS sit unfixed because someone has to notice them first, then
write an issue, then wait for a maintainer to have time. That chain has
a weak first link — noticing.

IssueLoop skips it. It reads the test suite directly. A failing test
*is* the bug report. No human has to spot it or write it up.

## What it does

1. Runs a repo's test commands
2. Catches what fails
3. Asks one question per failure: is this one bug or several bundled
   together? Splits accordingly
4. Stores each as a ticket
5. Hands tickets out one at a time — claimed tickets don't get handed
   out twice

## What it doesn't do

- Doesn't propose a fix
- Doesn't touch a file
- Doesn't open a PR
- Doesn't run anything not already in your test manifest

Fixing is a separate system's job. This repo's only output is a clean,
prioritized ticket queue.