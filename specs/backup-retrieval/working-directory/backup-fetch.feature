@domain:backup-retrieval @area:working-directory @from:backup-verify/backup-verify
Feature: Fetching the backup to verify
  Lets operators pull the backup under test with restic, pgBackRest or their own command into a working directory the restore can read.

  @id:backup-retrieval.working-directory.001 @rule:backup-retrieval.native-fetch.restore-into-workdir @verified @source:backup_verify.py#build_fetch_command @test:tests/test_backup_verify.py#test_build_fetch_command_restic @test:tests/test_backup_verify.py#test_build_fetch_command_pgbackrest
  Scenario Outline: Native fetchers restore the backup into the working directory
    Given the plan's fetch type is <type> with <settings>
    When the operator runs the plan
    Then "backup-verify: fetching latest backup" is shown
    And backup-verify runs <command>

    Examples:
      | type       | settings                                                                                     | command                                                                                                    |
      | restic     | repository s3:s3.example.com/backups and no snapshot                                         | restic -r s3:s3.example.com/backups restore latest --target <workdir>                                      |
      | restic     | repository s3:s3.example.com/backups, snapshot abc123 and password file /etc/restic/password | restic -r s3:s3.example.com/backups restore abc123 --target <workdir> --password-file /etc/restic/password |
      | pgbackrest | stanza main and extra args --delta                                                           | pgbackrest --stanza=main --pg1-path=<workdir> restore --delta                                              |

  @id:backup-retrieval.working-directory.002 @rule:backup-retrieval.custom-fetch.workdir-in-environment @verified @source:backup_verify.py#fetch_backup @test:tests/test_backup_verify.py#test_in_place_run_loads_and_checks_without_docker
  Scenario: A custom fetch command is told where to put the backup
    Given the plan has no fetch type and its fetch command is 'printf "alpha\nbeta\n" > "$BACKUP_VERIFY_WORKDIR/rows.txt"'
    When the operator runs the plan
    Then the command runs through the shell with $BACKUP_VERIFY_WORKDIR set to the run's working directory
    And rows.txt is in the working directory for the load to read

  @id:backup-retrieval.working-directory.003 @rule:backup-retrieval.working-directory.absolute-fresh-by-default @verified @source:backup_verify.py#run_plan @test:tests/test_backup_verify.py#test_relative_workdir_is_resolved_before_anything_uses_it
  Scenario Outline: The working directory is a fresh temporary directory unless chosen, and is always absolute
    Given the operator <choice>
    When the operator runs the plan
    Then the backup is fetched into <directory>, created if missing
    And every command sees it as an absolute path

    Examples:
      | choice                          | directory                                 |
      | passes no --workdir             | a new backup-verify-* temporary directory |
      | passes --workdir work from /srv | /srv/work                                 |
