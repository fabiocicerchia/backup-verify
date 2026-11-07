@domain:run-reporting @area:exit-codes @from:backup-verify/backup-verify
Feature: Telling run outcomes apart by exit status
  Gives schedulers and monitoring a status they can act on, so a passing restore, failed checks and a broken plan are not confused.

  @id:run-reporting.exit-codes.001 @rule:run-reporting.exit-codes.status-per-outcome @verified @source:backup_verify.py#main @test:tests/test_backup_verify.py#test_missing_plan_file_exits_noinput @test:tests/test_backup_verify.py#test_unparsable_plan_exits_dataerr @test:tests/test_backup_verify.py#test_json_flag_writes_only_json_to_stdout
  Scenario Outline: Each run outcome ends with its own exit status
    Given <situation>
    When the operator runs the plan
    Then backup-verify exits with status <status>

    Examples:
      | situation                                   | status |
      | a plan whose every smoke check passes       | 0      |
      | a plan where at least one smoke check fails | 1      |
      | a plan path that does not exist             | 66     |
      | a plan file that is not valid YAML          | 65     |

  @id:run-reporting.exit-codes.002 @rule:run-reporting.exit-codes.errored-run-crashes-with-status-1 @gap @source:backup_verify.py#main @questionable
  Scenario Outline: A run that errors ends in a traceback with the same status as failed checks
    Given <problem>
    When the operator runs the plan
    Then a Python traceback is printed instead of a PASS/FAIL summary
    And with --json no result document is written to stdout
    And backup-verify exits with status 1

    Examples:
      | problem                                                   | note              |
      | the plan's restore image is empty                         | plan defect       |
      | the fetch command exits non-zero                          | fetch failure     |
      | the ready command never succeeds within the ready timeout | readiness timeout |
      | docker is not installed and the plan names an image       | missing runtime   |
