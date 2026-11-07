@domain:restore-environments @area:scratch-container @from:backup-verify/backup-verify
Feature: Restoring into a scratch container
  Lets operators prove a backup restores by loading it into a throwaway, isolated container that is cleaned up afterwards.

  Background:
    Given a plan whose restore block names the image postgres:16-alpine and a ready command

  @id:restore-environments.scratch-container.001 @rule:restore-environments.scratch-container.container-from-plan @verified @source:backup_verify.py#build_run_args @test:tests/test_backup_verify.py#test_build_run_args_attaches_network_and_no_limits_by_default @test:tests/test_backup_verify.py#test_build_run_args_applies_resource_limits
  Scenario: The scratch container runs the plan's image with the backup at /work and the plan's settings
    Given the restore block sets env POSTGRES_PASSWORD=example, memory 512m and cpus 1.5
    When the operator runs the plan
    Then a container is started from postgres:16-alpine
    And the fetched backup is mounted at /work inside it
    And it has POSTGRES_PASSWORD=example, a 512m memory limit and a 1.5 CPU limit

  @id:restore-environments.scratch-container.002 @rule:restore-environments.network-isolation.private-internal-network-per-run @verified @source:backup_verify.py#run_plan @test:tests/test_backup_verify.py#test_build_run_args_attaches_network_and_no_limits_by_default
  Scenario: Each run gets its own network with no outside access
    Given two runs of the plan happen at the same time
    When the operator runs the plan
    Then each run's container is attached to its own network named after the run
    And that network is internal, with no route to the outside

  @id:restore-environments.scratch-container.003 @rule:restore-environments.readiness-wait.retry-until-ready-or-timeout @gap @source:backup_verify.py#wait_until_ready
  Scenario Outline: The restore waits for the service to answer and fails once the ready timeout runs out
    Given the plan's ready command is pg_isready -U postgres with a ready timeout of <timeout>
    And the service <behaviour>
    When the operator runs the plan
    Then <outcome>

    Examples:
      | timeout                       | behaviour                | outcome                                                                          |
      | 30 seconds                    | answers after 10 seconds | the dump is loaded and the checks run                                            |
      | 30 seconds                    | never answers            | the run errors with "restore.ready_command never succeeded within ready_timeout" |
      | unset (60 seconds by default) | never answers            | the run errors after about 60 seconds                                            |

  @id:restore-environments.scratch-container.004 @rule:restore-environments.teardown.removed-unless-kept @gap @source:backup_verify.py#run_plan
  Scenario Outline: The scratch container and network are removed after every run unless --keep is given
    Given the restored service <run result>
    When the operator runs the plan <flag>
    Then the scratch container and its network are <state> afterwards
    And a failure to remove them does not change the run's result

    Examples:
      | run result          | flag           | state         |
      | passes every check  | without --keep | gone          |
      | fails a check       | without --keep | gone          |
      | never becomes ready | without --keep | gone          |
      | fails a check       | with --keep    | left in place |

  @id:restore-environments.scratch-container.005 @rule:restore-environments.teardown.failed-start-leaks-network @gap @source:backup_verify.py#run_plan @questionable
  Scenario: A container that fails to start leaves its run's network behind
    Given the image cannot be started, for example registry.example.com/missing:1 does not exist
    When the operator runs the plan without --keep
    Then the run errors
    And the run's internal network is still there afterwards
