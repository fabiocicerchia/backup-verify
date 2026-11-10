@domain:alerting-history @area:failure-hook @from:backup-verify/backup-verify
Feature: Alerting and run history
  Lets operators be told when a backup does not restore, have silence on success alert a dead-man's switch, and track restore time over runs.

  @id:alerting-history.failure-hook.001 @rule:alerting-history.heartbeat.ping-only-on-pass @verified @source:backup_verify.py#_ping_heartbeat @test:tests/test_backup_verify.py#test_success_pings_heartbeat_and_skips_on_failure
  Scenario Outline: The heartbeat URL is pinged only after a passing run
    Given the plan's heartbeat URL is <url>
    And the run <outcome>
    When the operator runs the plan
    Then <heartbeat>

    Examples:
      | url                                 | outcome            | heartbeat                                                                                          |
      | https://hc-ping.example.com/abc     | passes every check | a GET request is sent to https://hc-ping.example.com/abc                                           |
      | https://hc-ping.example.com/abc     | fails a check      | no request is sent                                                                                 |
      | https://hc-ping.example.com/abc     | errors             | no request is sent                                                                                 |
      | ftp://hc.example.com/abc            | passes every check | no request is sent and the warning "notify.heartbeat_url is not an http(s) URL, skipping" is shown |
      | https://unreachable.example.com/abc | passes every check | the warning "heartbeat ping failed: ..." is shown and the run still passes                         |

  @id:alerting-history.failure-hook.002 @rule:alerting-history.failure-hook.fires-with-context @verified @source:backup_verify.py#run_failure_hook @test:tests/test_backup_verify.py#test_failed_check_runs_on_failure_with_check_name @test:tests/test_backup_verify.py#test_fetch_failure_records_history_and_runs_on_failure @test:tests/test_backup_verify.py#test_success_pings_heartbeat_and_skips_on_failure
  Scenario Outline: The failure command fires on failed checks or a run error, with the context in its environment
    Given the plan's failure command is ./page-oncall.sh
    And the run <outcome>
    When the operator runs the plan
    Then ./page-oncall.sh runs once with BACKUP_VERIFY_STATUS=<status>
    And BACKUP_VERIFY_FAILED_CHECKS=<failed>, BACKUP_VERIFY_ERROR=<error> and BACKUP_VERIFY_DURATION set to the run's seconds

    Examples:
      | outcome                                  | status | failed    | error             |
      | fails the check "row count"              | fail   | row count | (empty)           |
      | errors because the fetch command exits 1 | error  | (empty)   | the error message |

  @id:alerting-history.failure-hook.003 @rule:alerting-history.failure-hook.never-changes-outcome @verified @source:backup_verify.py#run_failure_hook @test:tests/test_backup_verify.py#test_on_failure_nonzero_exit_does_not_change_outcome @test:tests/test_backup_verify.py#test_unspawnable_notifier_is_logged_as_a_warning
  Scenario Outline: A broken failure command never changes the run's outcome
    Given a check fails
    And the plan's failure command <problem>
    When the operator runs the plan
    Then the run still reports FAIL with the failed check
    And <extra>

    Examples:
      | problem             | extra                                                       |
      | exits with status 3 | no warning is shown                                         |
      | cannot be started   | the warning "could not run notify.on_failure: ..." is shown |

  @id:alerting-history.failure-hook.004 @rule:alerting-history.run-history.one-line-per-run @verified @source:backup_verify.py#append_run_history @test:tests/test_backup_verify.py#test_append_history_writes_one_json_line_per_call @test:tests/test_backup_verify.py#test_fetch_failure_records_history_and_runs_on_failure
  Scenario Outline: Every run adds one line to the history file
    Given the plan's history file is /var/lib/backup-verify/history.jsonl
    And the run <outcome>
    When the operator runs the plan
    Then one JSON line is added with timestamp, duration_seconds and ok <ok>
    And <error field>

    Examples:
      | outcome                                  | ok    | error field                             |
      | passes every check                       | true  | it has no error field                   |
      | fails a check                            | false | it has no error field                   |
      | errors because the fetch command exits 1 | false | its error field holds the error message |
