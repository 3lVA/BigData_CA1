# Debugging Journal

This journal combines the original Progress Update 1 issues with the later
setup, preparation, MapReduce, Git and benchmarking work. Controlled failures
are labelled explicitly. A cause is stated only where the error or checks
support it; a successful recovery does not establish every underlying cause.

The [original Progress Update 1 journal](evidence/progress-update-1/debugging_journal.md)
and its linked evidence are preserved separately. That cluster used different
container IDs and IP addresses from the final project.

## Why I Repeated the Work After Progress Update 1

After submitting Progress Update 1, I started a fresh project folder and repeated
the cluster setup, HDFS uploads, YARN test and fault-tolerance demonstration.
I wanted to understand what each command did and why it was needed, rather than
only having a working setup. I documented the steps as I repeated them and used
the new evidence for the final project. This was a learning decision, not a claim
that the entire original setup had failed. The earlier issues remain relevant
and are recorded below alongside those encountered during the repeated work.

## Progress Update 1

### 1 Windows could not find the Hadoop command
- **Problem:** Running `hdfs dfs -mkdir -p /sg_mobility/demo` in Windows returned
  `'hdfs' is not recognized`.
- **Cause and fix:** Hadoop was installed inside the Docker client, not on the
  Windows command path. I ran Hadoop commands through `docker compose exec client`.
- **Verification:** I uploaded, listed and read a test file in HDFS. Later checks
  also confirmed that the [uploaded files were healthy](evidence/progress-update-1/evidence/hdfs-all-files-fsck.txt).

### 2 Rainfall upload failed during the bulk upload
- **Problem:** Three CSVs were present, but rainfall was missing. The upload
  reported an error involving its temporary `._COPYING_` path.
- **Investigation and fix:** I listed HDFS, identified the missing file and
  uploaded rainfall separately. The error did not establish why the temporary
  path disappeared, so I did not assign an unsupported cause.
- **Verification:** The rainfall file was 51,584,840 bytes, and the
  [folder-wide fsck](evidence/progress-update-1/evidence/hdfs-all-files-fsck.txt)
  reported all four CSVs healthy.

### 3 Python could not import mrjob
- **Problem:** The initial bus-stop count returned
  `ModuleNotFoundError: No module named 'mrjob'` inside the client.
- **Fix:** I installed the package in that environment using
  `docker compose exec client python3 -m pip install mrjob==0.7.4`, then reran
  the count with the Hadoop runner.
- **Verification:** [The original YARN report](evidence/progress-update-1/screenshots/03-yarn-terminal.png)
  showed application `application_1794540434658_0001` succeeded and counted
  5,209 records after skipping the header.
- **Later recurrence on Windows:** Clicking Run Python for M2 used my local
  Python 3.14 interpreter, which also lacked mrjob. I ran the analysis through
  the Docker client instead. The [M2 sample log](evidence/m2/m2-sample-log.txt)
  confirms both stages completed. Installing a package in one Python environment
  does not install it in every other environment.

### 4 The during-recovery evidence command failed
**Type: command error during a controlled fault test.**
- **Problem:** After deliberately stopping `datanode2`, the attempt to capture
  recovery evidence returned `-head: Too many arguments: expected 1 but got 11`.
  The saved output confirms an argument error, not loss of the HDFS file.
- **Fix:** I ran a valid fsck command. By then, replication had already recovered,
  so I repeated the controlled test using a node holding a current replica.
- **Verification:** The [read check](evidence/progress-update-1/screenshots/05-file-still-readable.png)
  showed the file remained readable. The [command error](evidence/progress-update-1/evidence/05-command-error.txt)
  and [restored-replica report](evidence/progress-update-1/evidence/06-fsck-replication-restored.txt)
  preserve both the failed capture and successful recovery.

### 5 A stopped DataNode did not immediately appear dead
**Type: expected behaviour investigated during a controlled fault test.**
- **Problem:** Docker showed the node stopped, while an early NameNode report
  still listed three DataNodes and two replicas.
- **Explanation and action:** Failure detection depends on missed heartbeats;
  stopping a container does not instantly update the NameNode. I allowed time,
  repeated the checks and read the file without deleting storage volumes.
- **Verification:** The [early report](evidence/progress-update-1/evidence/run2-fsck-check-01.txt),
  [dead-node report](evidence/progress-update-1/screenshots/run2-05-dfsadmin-dead-datanode.png),
  [under-replicated blocks](evidence/progress-update-1/screenshots/run2-05-dfsadmin-under-replicated.png)
  and [successful read](evidence/progress-update-1/screenshots/run2-05-file-still-readable.png)
  show the sequence. The file-specific checks missed the one-replica moment;
  the [later report](evidence/progress-update-1/evidence/run2-fsck-replication-restored.txt)
  showed replacement replication. After restarting the node, the
  [live-node screenshot](evidence/progress-update-1/screenshots/run2-07-three-live-datanodes.png)
  and [final fsck](evidence/progress-update-1/evidence/run2-fsck-after-restart.txt)
  confirmed recovery.

## Restarted Final Project

### 6 Port 9870 was already allocated
- **Problem:** `docker compose up -d` failed with
  `Bind for 0.0.0.0:9870 failed: port is already allocated`.
- **Cause and fix:** Another running container/project was using the host port.
  I stopped the conflicting old setup and started the final project again.
  No DataNode volumes were deleted.
- **Verification:** Later checks showed all seven services running. The
  [final cluster fsck](evidence/fault-tolerance-demo/hdfs-fsck.txt) and successful MapReduce
  applications confirm the recovered setup. This was separate from the
  hostname startup error below.

### 7 NameNode and ResourceManager exited during startup
- **Problem:** Only five services stayed running. `docker compose ps -a` showed
  the NameNode exited with code 1 and ResourceManager with code 255.
- **Investigation:** `docker compose logs --tail 80 namenode resourcemanager`
  showed `UnknownHostException` and `Temporary failure in name resolution`
  for the containers' hostnames. The message mentioning a Kerberos principal
  appeared within that hostname failure; it did not establish a need to set up
  a Kerberos cluster.
- **Recovery and verification:** The affected containers were recreated and
  checked again. The exact reason their hostname resolution failed was not
  established. The [original log excerpt](evidence/troubleshooting/startup-name-resolution-log.txt)
  preserves the failure, while the [healthy fsck](evidence/fault-tolerance-demo/hdfs-fsck.txt)
  and [successful M1 applications](evidence/m1/m1-yarn-applications.png)
  support recovery.

### 8 The final replication test needed current replica locations
**Type: controlled fault-tolerance demonstration, not an accidental outage.**
- **Method:** I checked the selected bus-stop file with `fsck -files -blocks
  -locations` and matched its replica IP addresses to Docker service names.
  I stopped `datanode2`, which held a replica, and checked that the file stayed
  readable using `hdfs dfs -head`. I waited for re-replication before restarting
  the stopped node.
- **Observed sequence:** The reports show two live replicas, then one remaining
  replica, then two replicas on the other available nodes. After restart, HDFS
  was healthy with three DataNodes. The final test captured the transition that
  the earlier Progress Update 1 file-specific checks had missed.

| Check | Saved evidence |
|---|---|
| Before failure | [Two replicas](evidence/fault-tolerance-demo/replication-before.txt) |
| During recovery | [One live replica](evidence/fault-tolerance-demo/replication-during.txt) |
| After replacement | [Two live replicas while the stopped node remained down](evidence/fault-tolerance-demo/replication-after.txt) |
| After restart | [Healthy cluster](evidence/fault-tolerance-demo/replication-after-restart.txt) |

Replication preserved a surviving block copy. It did not provide a standby
NameNode; a single NameNode remains a separate availability limitation.

## File Locations and Data Preparation

### 9 Local files were confused with container and HDFS files
- **Problem:** CSVs existed in VS Code, but the HDFS browser initially appeared
  empty. Later, the terminal listed four raw files while the browser showed
  only a folder called `raw`.
- **Cause and fix:** Local files are not automatically uploaded to HDFS. The
  browser was also displaying `/sg_mobility`, while the terminal listed
  `/sg_mobility/raw`. I uploaded the files and opened the matching HDFS directory.
- **Related path check:** `/home/user/mapreduce` is a container path. The
  `userfiles:/home/user` mount makes its host counterpart
  `userfiles/mapreduce`; the container itself does not appear as a VS Code folder.
- **Verification:** The [HDFS check](evidence/fault-tolerance-demo/hdfs-fsck.txt) and
  [prepared bus listing](evidence/data-preparation/bus-prepared-hdfs-files.txt)
  show the files were present. A broad rainfall-directory listing also included
  bus files; I changed it to list the relevant rainfall files, rather than treating
  unrelated directory entries as incorrect uploads.

### 10 M1 initially used raw inputs instead of the canonical schema
- **Problem:** The early M1 prototype read raw OD columns and included duplicate
  handling within the analysis. Reviewing Appendix A showed that preparation
  and canonical inputs needed a consistent shared approach.
- **Correction:** I centralised validation and duplicate handling in
  `prepare_data.py`, produced canonical bus and stop CSVs, and updated M1 to read
  those inputs. I replaced the old raw sample with a canonical sample.
- **Verification:** The [sample output](evidence/m1/m1-sample-output.txt)
  preserved leading zeroes, totals, ranking order and descriptions. The
  [completed full output](evidence/m1/m1-output.txt) disclosed unmatched stop IDs.
  This correction did not require rebuilding the Hadoop cluster.

Preparation also exposed real source-data limitations. These were quality
findings, not invented program failures:

| Finding | Handling and verification |
|---|---|
| 7,995 valid OD rows referenced stops absent from metadata | Retained the rows; M1 disclosed unmatched IDs rather than silently dropping trips. |
| Rainfall source-update and retrieval times were unavailable | Left those canonical fields blank and recorded the limitation in the [preparation profile](evidence/data-preparation/rainfall-profile.json). |
| 3,908 invalid parking records and 14,096 repeats | Quarantined rejected records with reasons and accepted 1,727,688 unique observations from 1,745,692 inputs. Valid non-C lot types were preserved during preparation. |
| Parking source dates predated September despite September API responses | Preserved source and response timestamps separately. M3 used source dates; M4 explicitly filtered source dates to September. |
| No verified individual carpark coordinates in the supplied observations | Chose a date-based regional-weather comparison for M4 and disclosed that it is not a local spatial rainfall join. No coordinates were guessed. |

The [preparation script](userfiles/prepare_data.py) and
[analysis methods and limitations](userfiles/mapreduce/MapReduce_Analytics.md)
record these decisions. No conflicting versions were reported in the supplied
accepted records; conflict-handling safeguards are not claimed as encountered errors.

## Git and Project Organisation

GitHub was not a required assignment deliverable. I chose to use Git and GitHub
to track my changes and practise commits, branches, pull requests and merging.
The Git issues below describe problems encountered while using that optional
workflow, alongside the required Hadoop and MapReduce work.

### 11 Commit and push did not include new files
- **Problem:** Git reported `no changes added to commit`; a later push said
  `Everything up-to-date` while the new evidence remained untracked.
- **Cause and fix:** The files had not been staged. I used `git add` for the
  intended code, results and logs, then committed and pushed again.
- **Verification:** The selected files appeared in the commits and remote branch.
  Word working documents and storage folders remained excluded by `.gitignore`.
  A push alone does not stage or commit local files.

### 12 M3 appeared missing after switching to the M4 branch
- **Problem:** M4 showed the older M2 version of the project even though M3 had
  been pushed and merged on GitHub.
- **Investigation and fix:** Fetching showed remote main contained M3 merge
  commit `946e8be`, while local M4 still started at `4a5c879`. I updated M4 with
  `git fetch origin` followed by `git merge --ff-only origin/main`.
- **Verification:** M3's script, results, screenshots, preparation changes and
  write-up appeared again. The work had not been deleted; the local branch
  had not yet received the newer commits.

## Timing and YARN Evidence

### 13 The original M1 timing recorded only a start time
- **Problem:** The initial timing file had a start timestamp but no end time,
  so it could not establish a complete run duration.
- **Fix:** I used a Windows Command Prompt block with delayed expansion enabled
  by `cmd /V:ON`. It recorded `!date! !time!` before and after the job, captured
  the job exit code immediately, and saved output and logs separately. The end
  was recorded only after final output retrieval.
- **Verification:** The retained [M1 run-1 timing](evidence/performance%20analysis/m1/m1-benchmark-run1-timing.txt)
  contains start, end and exit code 0. I kept the
  [original incomplete timing](evidence/m1/m1-run1-timing.txt) as evidence and
  excluded it from the performance summary.

### 14 Reusing filenames and closing the terminal damaged benchmark evidence
- **Problem:** I reran M1 without changing the filenames, so `>` overwrote the
  earlier files. I also closed a terminal during an attempt and found incomplete
  or empty evidence had already been committed and pushed.
- **Fix:** I checked for active YARN applications before another run, waited for
  completed commands to return to the prompt and used separate run-1, run-2 and
  run-3 filenames. I replaced invalid evidence with completed runs and committed
  corrections normally instead of rewriting remote history.
- **Verification:** The reported M1 run 1 is the completed replacement from
  10:39:12.39 to 10:41:17.36 (124.97 seconds), applications ending 0014 and 0015.
  It replaces earlier attempts in the final benchmark table. All six retained
  runs returned exit code 0 and matched the validated outputs; see the
  [performance analysis](performance_analysis.md). Closing a client terminal
  alone does not prove that an already submitted YARN application stopped.

### 15 A browser could not open the YARN tracking hostname
- **Problem:** The browser showed `DNS_PROBE_FINISHED_NXDOMAIN` for a tracking
  URL beginning `http://resourcemanager:8088/`.
- **Cause and response:** `resourcemanager` is a Docker-network service name that
  the Windows browser could not resolve. Replacing it with `localhost:8088` was
  suggested for the published ResourceManager port, but successful History-page
  access was not confirmed. I did not change the cluster during benchmarking.
- **Evidence and outcome:** I retained the ResourceManager screenshots and used
  the saved job counters for task/resource evidence. Log aggregation was disabled,
  and mrjob also printed `Can't fetch history log; missing job ID` after jobs had
  completed. That warning did not cancel the successful applications or saved
  results. The [M1 benchmark log](evidence/performance%20analysis/m1/m1-benchmark-run1-log.txt)
  contains task counts and shuffle/resource counters; all runs are linked in
  [the performance write-up](performance_analysis.md).

### 16 M1 run 3 logged one killed map attempt
**Type: non-fatal observation; not a failed benchmark.**
- **Observation:** Stage 1 had 53 input splits, 54 launched map attempts and one
  killed map task. The log does not establish why the extra attempt was killed.
- **Check and outcome:** I checked application success, exit code 0 and output
  correctness. The result matched the validated M1 output, so I retained the run
  and disclosed the attempt count rather than claiming a clean task history.
- **Evidence:** [Run-3 log](evidence/performance%20analysis/m1/m1-benchmark-run3-log.txt),
  [timing](evidence/performance%20analysis/m1/m1-benchmark-run3-timing.txt) and
  [YARN status](evidence/performance%20analysis/m1/m1-benchmark3-yarn-applications.png).

## Final Evidence Organisation

During final review, I grouped the existing evidence by setup, preparation,
analysis, performance and troubleshooting. File contents were hash-checked after
moving, and current Markdown links were updated. Earlier Word screenshots and
commands still show the paths used at the time. The
[evidence folder guide](evidence/README.md) explains the final layout and records
this organisation decision for the reflection. The original Progress Update 1
project and its persistent storage directories were not duplicated into the
final submission; only relevant historical evidence was preserved.
