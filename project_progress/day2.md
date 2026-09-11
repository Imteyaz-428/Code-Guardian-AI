# Day 02 — Repository & Configuration Foundation

## Objective

The second day focused on establishing a safe and controlled foundation for
repository analysis.

Two important areas were refined:

- Application configuration
- Repository management

---

## 1. Central Configuration

A central settings module was established for backend configuration.

The configuration contains:

- Project root
- Allowed analysis root
- Allowed frontend origins
- API title
- API description
- API version

Environment variables were introduced for values that may change between
development environments.

---

## 2. Analysis Root

The analysis system was designed to restrict repository access to an allowed
analysis directory.

This prevents the analyzer from freely accessing arbitrary locations on the
machine.

The configuration supports:

`CODE_GUARDIAN_ANALYSIS_ROOT`

This allows the analysis root to be changed for local development without
hardcoding the location in the analysis logic.

---

## 3. Repository Manager

`RepositoryManager` was implemented/refined to handle repository paths.

Its responsibilities include:

- Validate repository paths
- Resolve relative paths
- Resolve absolute paths
- Prevent paths outside the allowed analysis root
- Check whether the repository exists
- Find Python source files

---

## 4. Python File Discovery

Python files are discovered recursively using:

`rglob("*.py")`

Generated cache directories such as:

`__pycache__`

are excluded.

The resulting files are sorted to keep analysis deterministic.

---

## 5. Error Handling

Invalid repository paths now produce clear errors instead of silently
continuing.

Examples include:

- Empty repository path
- Repository outside the allowed directory
- Non-existent repository
- Invalid repository directory

---

## Result

The repository layer became responsible for controlled repository access and
Python file discovery.

This created the foundation required by the later AST and project analysis
modules.