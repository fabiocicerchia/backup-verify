@domain:restore-environments @area:in-place-restore @from:backup-verify/backup-verify
Feature: Restoring in place
  Lets operators whose job already runs in a throwaway pod or VM verify a backup there, without Docker.

  Background:
    Given a plan whose restore block has no image key

  @id:restore-environments.in-place-restore.001 @rule:restore-environments.in-place-restore.runs-in-workdir @verified @source:backup_verify.py#local_runner @test:tests/test_backup_verify.py#test_in_place_run_loads_and_checks_without_docker @test:tests/test_backup_verify.py#test_relative_workdir_is_resolved_before_anything_uses_it
  Scenario: Without an image the load and the checks run on this host in the working directory
    Given the load command is "cp rows.txt restored.txt" and there is no ready command
    When the operator runs the plan
    Then "backup-verify: restoring in place (<workdir>)" is shown
    And no container is started and no readiness wait happens
    And the load and every check run with the working directory as their current directory and as $BACKUP_VERIFY_WORKDIR
    And the restore block's env values are set for those commands

  @id:restore-environments.in-place-restore.002 @rule:restore-environments.in-place-restore.container-limits-ignored-with-warning @verified @source:backup_verify.py#run_plan @test:tests/test_backup_verify.py#test_in_place_ignores_container_only_limits
  Scenario Outline: Container-only limits are ignored with a warning when restoring in place
    Given the restore block sets <setting>
    When the operator runs the plan
    Then the warning "restore.<setting> needs a scratch container; ignored without restore.image" is shown
    And the run carries on without the limit

    Examples:
      | setting |
      | memory  |
      | cpus    |
