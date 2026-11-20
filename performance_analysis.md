# MapReduce Performance Analysis

## Explanation

I ran M1 (bus corridors) and M2 (rainfall) three times each using unchanged inputs and cluster settings. Timings include submission, both stages and saving results. The cluster stayed running; I did not restart services or clear cached data between runs.

M1's median runtime was 124.97 seconds, with a range of 1.39 seconds. M2's median was 54.92 seconds, with a range of 0.97 seconds. These small ranges show similar timings across repeated runs.

M1 processed about 222 MB and shuffled 289.50 MB, compared with M2's 27 MB input and 0.62 MB shuffle. Shuffle transfers and groups mapper output for reducers. This additional work helps explain M1's longer runtime. Both analyses used two stages and one reducer per stage, limiting parallel reducer work. The single NodeManager's memory and CPU resources limited how many tasks could run together.

During troubleshooting, I corrected the commands to record both start and end times, then excluded interrupted attempts. All six outputs matched validated results. I did not change resources or test scaling. The results show runtime and variation on this cluster, but do not establish that adding nodes would improve performance or that input size alone caused the difference.

## Timing Results

All times are seconds. Median means the middle value after sorting the three
runtimes. Range means the longest runtime minus the shortest.

| Analysis | Run 1 | Run 2 | Run 3 | Median | Range |
|---|---:|---:|---:|---:|---:|
| M1 - Bus corridors | 124.97 | 123.90 | 125.29 | 124.97 | 1.39 |
| M2 - Rainfall | 54.92 | 55.24 | 54.27 | 54.92 | 0.97 |

## Run Evidence

Each run returned exit code 0 and both applications completed successfully.
All application IDs below use the prefix application_1795002805512_.

| Run | Application suffixes, stages 1 / 2 | Complete timing | Task and resource counters | Application status screenshot |
|---|---|---|---|---|
| M1 1 | 0014 / 0015 | [Timing](evidence/m1-benchmark-run1-timing.txt) | [Log](evidence/m1-benchmark-run1-log.txt) | [YARN](evidence/m1-benchmark1-yarn-applications.png) |
| M1 2 | 0016 / 0017 | [Timing](evidence/m1-benchmark-run2-timing.txt) | [Log](evidence/m1-benchmark-run2-log.txt) | [YARN](evidence/m1-benchmark2-yarn-applications.png) |
| M1 3 | 0018 / 0019 | [Timing](evidence/m1-benchmark-run3-timing.txt) | [Log](evidence/m1-benchmark-run3-log.txt) | [YARN](evidence/m1-benchmark3-yarn-applications.png) |
| M2 1 | 0020 / 0021 | [Timing](evidence/m2-benchmark-run1-timing.txt) | [Log](evidence/m2-benchmark-run1-log.txt) | [YARN](evidence/m2-benchmark1-yarn-applications.png) |
| M2 2 | 0022 / 0023 | [Timing](evidence/m2-benchmark-run2-timing.txt) | [Log](evidence/m2-benchmark-run2-log.txt) | [YARN](evidence/m2-benchmark2-yarn-applications.png) |
| M2 3 | 0024 / 0025 | [Timing](evidence/m2-benchmark-run3-timing.txt) | [Log](evidence/m2-benchmark-run3-log.txt) | [YARN](evidence/m2-benchmark3-yarn-applications.png) |

## Task and Container Evidence

The saved logs contain map/reduce counts, shuffle totals and allocated memory
and CPU resource-time counters for every stage of every run. All stages used
one reducer. The table below summarises the task and shuffle counters.
MB means 1,000,000 bytes.

| Run | Stage 1 map attempts | Stage 2 map attempts | Shuffled data across both stages (MB) |
|---|---:|---:|---:|
| M1 1 | 53 | 8 | 289.50 |
| M1 2 | 53 | 8 | 289.50 |
| M1 3 | 54 | 8 | 289.50 |
| M2 1 | 7 | 2 | 0.62 |
| M2 2 | 7 | 2 | 0.62 |
| M2 3 | 7 | 2 | 0.62 |

M1 run 3 recorded one killed map attempt and an extra launch. The job still
succeeded and its output matched the validated result. The log does not
establish why that attempt was killed. Attempt counts do not mean all tasks
ran at the same time.

