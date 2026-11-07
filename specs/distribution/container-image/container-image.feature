@domain:distribution @area:container-image @from:backup-verify/dockerfile
Feature: Running backup-verify from its container image
  Serves operators who run backup verification from the published image instead of installing it on the host, so they know what the image runs, as which user, and what it can reach.

  Background:
    Given the operator has built the backup-verify container image

  @id:distribution.container-image.001 @rule:distribution.container-image.entrypoint-is-cli @inferred @source:Dockerfile#runtime stage
  Scenario: The image runs the backup-verify CLI with the operator's arguments
    Given a verification plan mounted into the container at /plans/backup-verify.yaml
    When the operator runs the image with the arguments "run /plans/backup-verify.yaml"
    Then the backup-verify "run" command executes that plan
    And the container's exit status is the run's exit status

  @id:distribution.container-image.002 @rule:distribution.container-image.runs-as-non-root @inferred @source:Dockerfile#runtime stage
  Scenario: The image runs as an unprivileged user, not root
    When the operator starts a container from the image without overriding the user
    Then the CLI runs as user "app" with uid 10001
    And files it writes to mounted volumes belong to uid 10001

  @id:distribution.container-image.003 @rule:distribution.container-image.no-container-client @inferred @source:Dockerfile#runtime stage @questionable
  Scenario: A plan that needs a scratch container cannot run from the image, even with the host socket mounted
    Given a verification plan with a restore image set
    And the host container runtime socket is mounted into the container
    When the operator runs the image with that plan
    Then the run fails with the error "docker is not on PATH"
    And no scratch container is started
    And the failure hook and run history record the run as an error

  @id:distribution.container-image.004 @rule:distribution.container-image.health-reflects-interpreter-only @inferred @source:Dockerfile#HEALTHCHECK
  Scenario: The container reports healthy as long as Python starts
    Given a container started from the image
    When the container runtime checks the container's health
    Then the container is reported healthy whenever the Python interpreter starts
    And the health status says nothing about whether backup verification passed
