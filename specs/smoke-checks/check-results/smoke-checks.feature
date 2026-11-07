@domain:smoke-checks @area:check-results @from:backup-verify/backup-verify
Feature: Judging the restored backup with smoke checks
  Lets operators state what a good restore looks like and see, check by check, whether the backup meets it.

  Background:
    Given a plan whose backup has been loaded into the restore environment

  @id:smoke-checks.check-results.001 @rule:smoke-checks.exact-match.trimmed-output-equals-expected @verified @source:backup_verify.py#evaluate @test:tests/test_backup_verify.py#test_exact_expectation
  Scenario Outline: An exact-match check passes only when its trimmed output equals the expected value
    Given a check "row count" expecting "<expected>"
    When the operator runs the plan and the check prints "<output>"
    Then the check is a <result>
    And the line "<line>" is shown

    Examples:
      | expected | output | result | line                                 |
      | 3        | 3\n    | pass   |   ✓ row count (3)                    |
      | 3        | 2      | fail   |   ✗ row count: expected '3', got '2' |

  @id:smoke-checks.check-results.002 @rule:smoke-checks.numeric-bounds.number-within-min-max @verified @source:backup_verify.py#evaluate @test:tests/test_backup_verify.py#test_min_max_bounds @test:tests/test_backup_verify.py#test_non_numeric_output_for_numeric_check
  Scenario Outline: A numeric check passes only when its output is a number within the bounds
    Given a check "orders" with <bounds>
    When the operator runs the plan and the check prints "<output>"
    Then the check is a <result> with reason "<reason>"

    Examples:
      | bounds       | output                         | result | reason                                                  |
      | minimum 1000 | 1500                           | pass   |                                                         |
      | maximum 48   | 12.5                           | pass   |                                                         |
      | minimum 1000 | 999                            | fail   | 999.0 < min 1000                                        |
      | maximum 48   | 72                             | fail   | 72.0 > max 48                                           |
      | minimum 1    | ERROR: relation does not exist | fail   | expected a number, got 'ERROR: relation does not exist' |

  @id:smoke-checks.check-results.003 @rule:smoke-checks.check-results.erroring-check-aborts-run @gap @source:backup_verify.py#run_checks @questionable
  Scenario: A check command that exits with an error aborts the run instead of failing the check
    Given a check "orders" whose query exits non-zero because the table does not exist
    And a later check "users"
    When the operator runs the plan
    Then no ✗ line is shown for "orders" and "users" never runs
    And the run errors with a traceback and status 1 instead of a FAIL summary

  @id:smoke-checks.check-results.004 @rule:smoke-checks.check-results.no-checks-passes @verified @source:backup_verify.py#run_plan @test:tests/test_backup_verify.py#test_in_place_ignores_container_only_limits @questionable
  Scenario: A plan with no checks passes
    Given the plan lists no checks and has a heartbeat URL
    When the operator runs the plan and the dump loads
    Then "backup-verify: PASS (0/0 checks, <seconds>s)" is shown
    And the heartbeat is pinged and the exit status is 0
