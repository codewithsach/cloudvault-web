# CI/CD Evidence

This page explains where to find CloudVault Web CI/CD telemetry, what each generated report proves, and how to interpret the security scan results.

## Workflow Links

- [CI/CD workflow](https://github.com/codewithsach/cloudvault-web/actions/workflows/ci-cd.yml)
- [CodeQL workflow](https://github.com/codewithsach/cloudvault-web/actions/workflows/codeql.yml)
- [All GitHub Actions runs](https://github.com/codewithsach/cloudvault-web/actions)
- [Code scanning alerts](https://github.com/codewithsach/cloudvault-web/security/code-scanning)

## Artifact Names

The CI/CD workflow uploads two artifact groups:

- `coverage-and-test-results`
- `security-scan-reports`

`coverage-and-test-results` contains:

- `coverage.xml`
- `test-results.xml`
- `coverage.svg`

`security-scan-reports` contains:

- `bandit-report.json`
- `pip-audit-report.json`

## What Each Report Proves

`coverage.xml` shows line coverage from the pytest suite. It is useful for reviewing which files and lines are covered by tests.

`test-results.xml` is a JUnit XML test report. It records test pass/fail status in a machine-readable format that CI tools can parse.

`coverage.svg` is a generated coverage badge from the latest CI coverage run.

`bandit-report.json` contains static analysis findings from Bandit. Bandit checks Python code for common security issues such as hardcoded secrets, risky subprocess usage, weak cryptography patterns, and unsafe temporary file handling.

`pip-audit-report.json` contains dependency vulnerability results from pip-audit. It checks packages in `requirements.txt` against known Python package vulnerability databases.

CodeQL results appear under GitHub code scanning alerts. CodeQL performs semantic code analysis and can identify security and quality issues that simpler linters may miss.

## How To Download Artifacts

1. Open the [CI/CD workflow](https://github.com/codewithsach/cloudvault-web/actions/workflows/ci-cd.yml).
2. Select the latest completed run.
3. Scroll to the `Artifacts` section.
4. Download `coverage-and-test-results` for coverage and JUnit results.
5. Download `security-scan-reports` for Bandit and pip-audit JSON reports.
6. Extract the downloaded ZIP files locally to inspect the report files.

## How To Interpret Bandit Results

Bandit reports findings by severity and confidence:

- `LOW` severity usually means informational or low-risk issues.
- `MEDIUM` severity should be reviewed and either fixed or documented.
- `HIGH` severity should be treated as a likely security issue.
- `HIGH` confidence means Bandit is more certain the finding is valid.

This repository generates the full Bandit JSON report for visibility, then separately enforces a CI gate for high-severity, high-confidence findings.

If Bandit reports findings in test files, review whether they are expected testing patterns, such as test assertions or test fixture passwords. Findings in application files should receive higher priority than findings in tests.

## How To Interpret pip-audit Results

`pip-audit-report.json` lists vulnerable dependencies, vulnerability IDs, affected versions, and fixed versions when available.

Recommended handling:

- If there are no vulnerabilities, the dependency audit passed.
- If vulnerabilities exist with fixed versions, update `requirements.txt` to a safe version and rerun tests.
- If no fixed version exists, document the risk and consider removing or replacing the dependency.
- Prioritize vulnerabilities in runtime dependencies over development-only tools.

The CI/CD workflow keeps the JSON report visible and also runs an enforcement step so known vulnerable dependencies fail the pipeline.
