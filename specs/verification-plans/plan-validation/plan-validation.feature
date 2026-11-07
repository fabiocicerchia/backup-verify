@domain:verification-plans @area:plan-validation @from:backup-verify/backup-verify
Feature: Rejecting restore settings that would run in the wrong place
  Protects operators from a plan that would quietly load and check the backup somewhere other than the scratch environment they meant, by refusing it before any backup is fetched.

  Background:
    Given a verification plan with a fetch step, a restore block and smoke checks

  @id:verification-plans.plan-validation.001 @rule:verification-plans.plan-validation.restore-environment-must-be-unambiguous @verified @source:backup_verify.py#validate_restore @test:tests/test_backup_verify.py#test_empty_image_is_a_plan_error_not_a_request_to_restore_in_place @test:tests/test_backup_verify.py#test_image_without_ready_command_is_a_plan_error
  Scenario Outline: A plan whose restore environment is ambiguous is refused before anything is fetched
    Given the plan's restore block <defect>
    When the operator runs the plan
    Then no backup is fetched
    And the run stops with the error "<message>"
    And the run is recorded as an error in the run history and failure notification

    Examples:
      | defect                                                  | message                                                           |
      | has an image key with an empty value                    | restore.image is empty; omit the key entirely to restore in place |
      | names the image postgres:16-alpine but no ready command | restore.ready_command is required alongside restore.image         |
