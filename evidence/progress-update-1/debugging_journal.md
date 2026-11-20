# Debugging Journal

## Issue 1 — Windows could not find the Hadoop command

- **Symptom.** Running `hdfs dfs -mkdir -p /sg_mobility/demo` in Windows Command Prompt returned `'hdfs' is not recognized`.
- **Cause.** The Hadoop CLI was installed inside the Docker client container.
- **Fix and verification.** I prefixed the command with `docker compose exec client`, then uploaded, listed and read a test file in HDFS.

## Issue 2 — Rainfall CSV upload failed

- **Symptom.** The bulk upload reported three existing CSVs and an error involving the rainfall file's temporary `._COPYING_` path.
- **Check.** I listed `/sg_mobility/` and confirmed rainfall was the only CSV missing. The output did not establish why the temporary path disappeared.
- **Fix and verification.** I uploaded the rainfall CSV by itself. The listing showed 51,584,840 bytes, and the [full-folder fsck](evidence/hdfs-all-files-fsck.txt) reported all four CSVs healthy.

## Issue 3 — The client could not import mrjob

- **Symptom.** The bus stop count script returned `ModuleNotFoundError: No module named 'mrjob'`.
- **Cause.** The Python interpreter inside the client container needed its own installation of `mrjob`.
- **Fix.** I ran `docker compose exec client python3 -m pip install mrjob==0.7.4` and reran the bus stop count with the Hadoop runner.
- **Verification.** YARN reported `SUCCEEDED` for application `application_1794540434658_0001`. The job counted 5,209 data records after skipping the header. [YARN application report](screenshots/03-yarn-terminal.png)

## Issue 4 — The during-recovery report failed in run 1

- **Controlled test.** I stopped `datanode2` while it held one of the two replicas of the `bus_stops.csv` block. The client could still read the CSV from `datanode3`. [Read during the outage](screenshots/05-file-still-readable.png)
- **Evidence gap.** My attempt to save the during-recovery `fsck` returned a `-head` argument error. The next valid report already showed two replicas on `datanode1` and `datanode3` while `datanode2` was still stopped. [Command error](evidence/05-command-error.txt) · [Restored replicas](evidence/06-fsck-replication-restored.txt)
- **Why I ran it again.** Run 1 proved the file stayed readable and HDFS replaced the replica. I repeated the test to capture what the NameNode reported between stopping a node and restoring replication. I stopped `datanode1` in run 2 because the latest baseline showed it now held one of the replicas.

## Issue 5 — The NameNode took time to mark datanode1 dead in run 2

- **Symptom.** Docker showed `datanode1` had exited, but the early `fsck` still listed three DataNodes and two replicas at `172.21.0.5` and `172.21.0.6`. The NameNode needs time to detect the missed heartbeats. [Early fsck report](evidence/run2-fsck-check-01.txt)
- **During the outage.** A later `dfsadmin -report` listed `172.21.0.5` under dead DataNodes. It showed two live DataNodes, 90 under-replicated blocks across the cluster and zero missing blocks. The client read the CSV from `172.21.0.6`. [Dead DataNode](screenshots/run2-05-dfsadmin-dead-datanode.png) · [Under-replicated blocks](screenshots/run2-05-dfsadmin-under-replicated.png) · [Successful read](screenshots/run2-05-file-still-readable.png)
- **Re-replication.** The file-specific checks missed the one-replica moment. The later `fsck` showed two live replicas at `172.21.0.3` and `172.21.0.6` while `datanode1` was still stopped. The new address shows where HDFS placed the replacement. [Restored replica report](evidence/run2-fsck-replication-restored.txt)
- **Restart verification.** After I restarted `datanode1`, I checked that it appeared in the live list. The final `fsck` showed three DataNodes, healthy HDFS and zero under-replicated blocks. [DataNodes after restart](screenshots/run2-07-three-live-datanodes.png) · [Final fsck](evidence/run2-fsck-after-restart.txt)
