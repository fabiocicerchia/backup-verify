@domain:run-reporting @area:json-output @from:backup-verify/backup-verify
Feature: Reporting the run's verdict
  Gives operators a readable summary line and automation a clean JSON document for each run.

  @id:run-reporting.json-output.001 @rule:run-reporting.console-summary.pass-fail-line @gap @source:backup_verify.py#main
  Scenario Outline: The run ends with a PASS or FAIL line counting passed checks and the duration
    Given a plan with <total> checks of which <passed> pass
    When the operator runs the plan
    Then the last line on stdout is "backup-verify: <verdict> (<passed>/<total> checks, 12.3s)"

    Examples:
      | total | passed | verdict |
      | 2     | 2      | PASS    |
      | 2     | 1      | FAIL    |

  @id:run-reporting.json-output.002 @rule:run-reporting.json-output.json-only-on-stdout @verified @source:backup_verify.py#main @test:tests/test_backup_verify.py#test_json_flag_writes_only_json_to_stdout
  Scenario: With --json, stdout carries only the result document
    Given a plan with a check "row count" that passes with output 2
    When the operator runs the plan with --json
    Then stdout is a single JSON document {"ok": true, "duration_seconds": 4.2, "checks": [{"name": "row count", "status": "pass", "output": "2"}]}
    And progress lines, ✓/✗ lines and the output of the fetch, load and check commands go to stderr
    And a failed check's output field holds its failure reason
