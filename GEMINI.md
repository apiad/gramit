# Gemini Project Guidelines

This document outlines the conventions and procedures to be followed by the Gemini agent for this project.

## Core Workflow

A strict, iterative, and well-documented workflow must be followed for all projects. This ensures the project history is clear and documentation stays current with the code.

The following files are central to this workflow and must be kept in sync with all development activities:

- **`ROADMAP.md`**: Outlines the high-level development plan. It should be updated as major phases or tasks are completed.
- **`CHANGELOG.md`**: Contains a user-facing summary of notable changes. An entry should be added for every significant feature, fix, or improvement.
- **`journal/`**: A directory containing detailed, chronological logs of all actions, thoughts, and decisions made during development, with one file per day (e.g., `journal/YYYY-MM-DD.md`).

The development process is as follows:

1.  **Iterate Step-by-Step**: Work in small, incremental steps, following the project's specific development methodology.
2.  **Document as You Go**: After each step, immediately update all relevant documentation (`ROADMAP.md`, `CHANGELOG.md`, `journal/`).
3.  **Commit Often**: After each meaningful and atomic change (including its documentation), create a commit with a clear message.

---

## Project-Specific Guidelines

This section details the specific tooling and methodologies for the **gramit** project.

### Project Overview
This is a Python 3.12 project.

### Environment and Dependency Management
- **Tooling:** We will use `uv` for all environment and package management tasks.
- **Running commands:** Any scripts or commands should be executed within the `uv` environment using `uv run`. For example: `uv run python my_script.py` or `uv run pytest`.
- **Adding dependencies:** Dependencies must be added using `uv add <package_name>`. For dev-only dependencies, use `uv add --dev <package_name>`.
- **Dependency file:** Do not manually edit the `dependencies` or `dev-dependencies` sections in `pyproject.toml`.

### Development Methodology
- **Test-Driven Development (TDD):** We will strictly follow TDD.
    1.  Write a failing test that clearly defines the desired functionality.
    2.  Run the test to confirm that it fails as expected.
    3.  Write the minimum amount of code necessary to make the test pass.
    4.  Run all tests to confirm they all pass.
    5.  Refactor the code as needed, ensuring tests continue to pass.

---

## General Coding Standards

### Documentation and Commenting
- **Public Functions:** All public functions must have clear and comprehensive docstrings explaining their purpose, arguments, and return values.
- **Inline Comments:** Avoid unnecessary inline comments. Code should be as self-documenting as possible.
- **Comment Style:** When comments are necessary, they should explain the *why* (the logic or reasoning) behind a piece of code, not the *what* (the implementation details).
