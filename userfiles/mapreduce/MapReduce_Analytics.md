# MapReduce Analytics

## M1 Busiest Directed Bus Corridors

### Method
The job reads the prepared canonical bus OD data. Stage 1 sums
TOTAL_TRIPS across hours for each month, day type and directed
origin–destination pair. Stage 2 selects the top ten pairs,
breaking ties by origin and destination IDs, and attaches both
stop descriptions.

### Validation and Execution
The ten-record canonical sample matched the expected rankings
and preserved stop-ID leading zeroes. The full dataset was then
processed on YARN, with both stages reporting SUCCEEDED.

### Findings
For September 2026, the highest-volume directed pair in both
day-type groups was 46101 (W'lands Checkpt) to 46211
(Johor Bahru Checkpt).

| Day type | Total trips |
|---|---:|
| WEEKDAY | 516,385 |
| WEEKENDS/HOLIDAY | 194,090 |

Checkpoint-related pairs also occupied the second and third
positions in both rankings. This highlights these corridors
as candidates for further operational capacity review.

These are monthly totals aggregated within each day type.
Direction is preserved, and the results describe stop pairs.

### Data Limitations
Preparation retained 7,995 OD rows containing stop IDs absent
from the metadata. The final output discloses three unmatched
IDs in the weekday group and five in the weekend/holiday group.

Only September 2026 was analysed. Complete repeated-run timing
will be documented in the performance analysis.


## M2 Rainfall by Station and Day

### Method
The job reads the prepared canonical rainfall data. Stage 1 sums observed
rainfall and counts valid unique five-minute observations per station and
Singapore calendar date. Daily coverage is the observation count divided
by 288. Stage 2 ranks the top ten station-days with at least 260
observations, meeting the 90% coverage threshold. Rainfall is ranked
descending, with station ID and date used to break ties.

The output retains all daily summaries and a separate partial-results
category. Completely absent station-days within the reporting scope
have zero observations, zero coverage and null rainfall.

### Validation and Execution
A controlled sample used 807 actual readings from 22 September 2026.
S306 retained 288 observations, S904 retained 260 and S06 retained 259.
The deliberate omissions applied only to the sample.

The sample output matched the expected results. S306 ranked first with
130.6 mm and 100% coverage, and S904 ranked second with 123.2 mm and
90.28% coverage. S06 recorded 47.4 mm and 89.93% coverage and was retained
separately as a partial day. This checked the eligibility boundary.

The full canonical dataset contained 761,445 observations. Both YARN
stages completed successfully:

| Stage | Application ID | Final status |
|---|---|---|
| Daily aggregation | application_1795002805512_0004 | SUCCEEDED |
| Ranking and partial results | application_1795002805512_0005 | SUCCEEDED |

The first complete run took 55.78 seconds, including job submission and
output retrieval, with exit code 0. Further repeated runs are required
for the performance analysis.

The [results](../../evidence/m2-output.txt),
[execution logs](../../evidence/m2-yarn-log.txt) and
[timing](../../evidence/m2-run1-timing.txt) are saved under evidence/.

### Findings
The highest observed rainfall among eligible station-days was 130.6 mm
at S306, Murnane Service Reservoir, on 22 September 2026.

| Rank | Station | Date | Observed rainfall | Coverage |
|---|---|---|---:|---:|
| 1 | S306 Murnane Service Reservoir | 2026-09-22 | 130.6 mm | 100% |
| 2 | S904 Holland Grove Road | 2026-09-22 | 123.2 mm | 100% |
| 3 | S904 Holland Grove Road | 2026-09-27 | 121.0 mm | 100% |

Of 2,670 reported station-days, 2,631 met the coverage threshold.
The separate partial category contained 23 partially observed days and
16 days without readings. Rainfall values describe individual
station-days; readings from different stations are kept separate.

### Data Limitations
The reporting scope uses the station IDs present in the input and the
calendar window between its earliest and latest observations. Station
operating dates were unavailable, so a day without readings indicates
missing data within this reporting scope.

Daily totals sum available readings. Missing intervals remain missing,
and incomplete observations can underestimate rainfall even when a day
meets the 90% eligibility threshold.

The downloaded CSV lacks source-update and retrieval timestamps.
Those canonical fields are blank, and this limitation is recorded in
the rainfall preparation profile. Only September 2026 was analysed.
