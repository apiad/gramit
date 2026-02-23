# Gemini Project Guidelines

This document outlines the conventions and procedures to be followed by the Gemini agent for this project.

## Project Overview

This is a Python 3.12 project.

## Environment and Dependency Management

- **Tooling:** We will use `uv` for all environment and package management tasks.
- **Running commands:** Any scripts or commands should be executed within the `uv` environment using `uv run`. For example: `uv run python my_script.py` or `uv run pytest`.
- **Adding dependencies:** Dependencies must be added using `uv add <package_name>`. For dev-only dependencies, use `uv add --dev <package_name>`.
- **Dependency file:** Do not manually edit the `dependencies` or `dev-dependencies` sections in `pyproject.toml`.

## Core Workflow

A strict, iterative, and well-documented workflow must be followed at all times. This ensures the project history is clear and documentation stays current with the code.

1.  **Iterate Step-by-Step**: Work in small, incremental steps. For new features or fixes, this typically follows the project's established development methodology (e.g., TDD).

2.  **Document as You Go**: After each step, immediately update all relevant documentation. This includes, but is not limited to:
    *   **Roadmap (`ROADMAP.md`)**: Mark tasks as complete as they are finished.
    *   **Changelog (`CHANGELOG.md`)**: Add a user-facing entry for the change.
    *   **Developer Journal (`journal/`)**: Add a detailed, chronological entry of the actions taken and decisions made.

3.  **Commit Often**: After each meaningful and atomic change (including its corresponding documentation updates), create a commit with a clear and descriptive message. This creates a clean and understandable project history.

## Development Methodology

- **Test-Driven Development (TDD):** We will strictly follow TDD.
    1.  Write a failing test that clearly defines the desired functionality.
    2.  Run the test to confirm that it fails as expected.
    3.  Write the minimum amount of code necessary to make the test pass.
    4.  Run all tests to confirm they all pass.
    5.  Refactor the code as needed, ensuring tests continue to pass.

## Documentation and Commenting

- **Public Functions:** All public functions must have clear and comprehensive docstrings explaining their purpose, arguments, and return values.
- **Inline Comments:** Avoid unnecessary inline comments. Code should be as self-documenting as possible.
- **Comment Style:** When comments are necessary, they should explain the *why* (the logic or reasoning) behind a piece of code, not the *what* (the implementation details).

## Changelog and Journaling

- **Changelog:** A high-level summary of features, fixes, and significant changes will be maintained in `CHANGELOG.md`.
- **Daily Journal:** A detailed, chronological log of all actions, thoughts, and decisions made during development will be kept in daily files under the `journal/` directory (e.g., `journal/YYYY-MM-DD.md`).
