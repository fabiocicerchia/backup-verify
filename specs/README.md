# Specifications of backup-verify

What this code does, one atomic Gherkin scenario per behaviour, read from the code by code-atlas.
Tags: `@verified` a test asserts it · `@inferred` read from the code only · `@gap` an entry point no test covers · `@human` written or amended by a person, never rewritten.

## Alerting and history
Telling outside systems how a run went and keeping a record of past runs.

- **Failure notifications**: [Alerting and run history](alerting-history/failure-hook/alerting-and-history.feature) (4)

## Backup retrieval
Getting the latest backup into a working directory, either through a built-in backup tool or a custom command.

- **Working directory**: [Fetching the backup to verify](backup-retrieval/working-directory/backup-fetch.feature) (3)

## Distribution
How backup-verify is packaged and installed for operators.

- **Container image**: [Running backup-verify from its container image](distribution/container-image/container-image.feature) (4)

## Documentation site
The look of the project's published documentation.

- **Content styling**: [Styling documentation content](documentation-site/content-styling/docs-content-styling.feature) (1)
- **Site theme**: [Branding the documentation site](documentation-site/site-theme/docs-site-theme.feature) (4)

## Restore environments
Where the backup gets loaded and the plan's commands run: a disposable container, or the current machine.

- **In-place restore**: [Restoring in place](restore-environments/in-place-restore/in-place-restore.feature) (2)
- **Scratch containers**: [Restoring into a scratch container](restore-environments/scratch-container/scratch-container-restore.feature) (5)

## Run reporting
How the result of a verification run is shown to people and to scripts.

- **Exit codes**: [Telling run outcomes apart by exit status](run-reporting/exit-codes/exit-codes.feature) (2)
- **JSON output**: [Reporting the run's verdict](run-reporting/json-output/run-report.feature) (2)

## Smoke checks
Queries run against the restored data to prove it holds what it should.

- **Check results**: [Judging the restored backup with smoke checks](smoke-checks/check-results/smoke-checks.feature) (4)

## Verification plans
The YAML plan that describes one backup verification and how the tool reads and checks it before doing any work.

- **Plan validation**: [Rejecting restore settings that would run in the wrong place](verification-plans/plan-validation/plan-validation.feature) (1)
