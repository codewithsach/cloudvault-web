# Testing and CI

This project uses `pytest` with Flask's `test_client`.

The test suite uses a temporary SQLite database and a temporary upload directory for each test. It does not use `instance/cloudvault.db` and does not write encrypted test files to the real `uploads/` folder.

## Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## Run tests

```powershell
python -m pytest -q
```

## Run tests with coverage

```powershell
python -m pytest --cov=. --cov-report=term-missing
```

## Export CI test telemetry locally

```powershell
python -m pytest --cov=. --cov-report=term-missing --cov-report=xml --junitxml=test-results.xml
```

This generates:

- `coverage.xml`
- `test-results.xml`

## Quality and security checks

Run the same checks used by CI:

```powershell
ruff check .
black --check .
bandit -r . -x tests -f json -o bandit-report.json
pip-audit -r requirements.txt -f json -o pip-audit-report.json
```

On Windows, if the command scripts are not on PATH, use:

```powershell
python -m ruff check .
python -m black --check .
python -m bandit -r . -x tests -f json -o bandit-report.json
python -m pip_audit -r requirements.txt -f json -o pip-audit-report.json
```

Note: run Bandit from a clean checkout or make sure local virtual environment folders such as `venv/` and `.venv/` are not scanned.

## GitHub Actions CI/CD

The repository includes `.github/workflows/ci-cd.yml`.

It runs automatically on:

- pushes to `main`, `master`, `dev`, and `dev-adrian`
- pull requests into `main`, `master`, and `dev`
- manual runs from the GitHub Actions tab

The workflow:

- installs dependencies from `requirements.txt`
- runs `python -m pytest -q` on Python 3.11 and 3.12
- runs a build/smoke check with `compileall`, Flask import, endpoint registration checks, database creation, and a homepage request
- runs coverage with `python -m pytest --cov=. --cov-report=term-missing --cov-report=xml --junitxml=test-results.xml`
- uploads `coverage.xml`, `test-results.xml`, and `coverage.svg`
- runs Ruff, Black, Bandit, and pip-audit
- uploads `bandit-report.json` and `pip-audit-report.json`
- writes Markdown telemetry to `$GITHUB_STEP_SUMMARY`
- includes a deployment placeholder that runs only after tests, coverage, and quality/security checks pass on `main` or `master`

Uploaded artifact names:

- `coverage-and-test-results`
- `security-scan-reports`

## CodeQL

The repository includes `.github/workflows/codeql.yml`.

CodeQL runs on:

- pushes to `main`, `dev`, and `dev-adrian`
- pull requests into `main` and `dev`
- a weekly scheduled scan
- manual runs from the GitHub Actions tab

The CodeQL workflow scans Python with `security-extended` and `security-and-quality` query packs.
