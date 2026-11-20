# Data Provenance and Preparation

## Scope and Source Files

I used the original CSVs retained from Progress Update 1 and prepared local
canonical teaching tables with [prepare_data.py](userfiles/prepare_data.py).
The original files remain unchanged in userfiles/ca1-data/. No new observation
data, simulated readings or external carpark locations were added for M4.
The acquisition scripts in the supplied CA1_Dataset_Instructions.zip identify
the source endpoints below. Their presence does not establish the exact time
when each original request was made; that information was not retained.

| Data | Original source | Use |
|---|---|---|
| Bus OD and bus stops | [LTA DataMall dynamic datasets](https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html); PV/ODBus and BusStops endpoints | M1 directed corridors and endpoint descriptions |
| Rainfall and station metadata | [NEA rainfall through data.gov.sg](https://data.gov.sg/datasets/d_6580738cdd7db79374ed3152159fbd69/view); api-open.data.gov.sg/v2/real-time/api/rainfall | M2 daily rainfall and M4 regional weather categories |
| Parking availability | [HDB carpark availability through data.gov.sg](https://data.gov.sg/datasets/d_ca933a644e55d34fe21f28b8052fac63/view); api.data.gov.sg/v1/transport/carpark-availability | M3 parking pressure and M4 daily occupancy |

The rainfall API documentation identifies millimetres and five-minute interval
totals. The supplied script writes those values to rainfall_mm. Original JSON
responses, reading-type fields and API retrieval timestamps were not retained,
so they cannot be rechecked response by response from these CSVs. LTA credentials
and temporary signed download URLs are not included in the provenance files.

## Actual Periods and Grain

All prepared timestamps use Asia/Singapore with explicit UTC+08:00. Filenames
and download dates are not used as substitutes for observation dates.

| Dataset or timestamp | Actual period or interpretation |
|---|---|
| Bus OD | 2026-09 only; aggregate by month, day type, hour and directed stop pair |
| Rainfall observed_at | 2026-09-01T00:00:00+08:00 to 2026-09-30T23:55:00+08:00 |
| Parking observed_at | 2025-11-01T13:45:00+08:00 to 2026-09-30T23:01:04+08:00 |
| Parking response_at | 2026-09-01T00:00:37+08:00 to 2026-09-30T23:00:36+08:00 |
| Bus-stop metadata | Source snapshot date and official validity dates unavailable |
| Weather-station metadata | Derived from rainfall observations; official location-validity dates unavailable |

Bus records are monthly aggregates, not dated journeys. M1 sums total_trips and
preserves direction. Bus data is not joined to daily weather. M3 groups by the
actual source update date, including older source dates. M4 retains September
source dates only, then joins rainfall and parking summaries by the same date.

## Accepted and Excluded Records

Counts below exclude CSV headers and were checked against the current files.
For each source, input equals accepted plus excluded.

| Source | Input rows | Accepted rows | Excluded rows | Exclusion details |
|---|---:|---:|---:|---|
| Bus stops | 5,209 | 5,209 | 0 | No exclusions |
| Bus OD | 5,863,920 | 5,863,920 | 0 | No exclusions; 7,995 accepted rows contain unmatched stop IDs |
| Rainfall | 761,445 | 761,445 | 0 | No exclusions or duplicates; 89 stations |
| Parking | 1,745,692 | 1,727,688 | 18,004 | 3,908 invalid-capacity/availability rows; 14,096 repeated source observations |

The accepted parking data contains 1,426,957 C, 151,085 H and 149,646 Y records.
All lot types are validated before M3/M4 select C. Rejected records are preserved
with reason and raw_record fields in the quarantine CSVs. The parking reason
codes are invalid_capacity_or_availability and repeated_source_observation.
The other quarantine files contain only their headers, consistent with zero
exclusions. Missing stop metadata does not make otherwise valid OD trips invalid.

## Source-to-Canonical Field Mapping

These renamings, metadata selections and derived summaries are teaching
transformations. The source APIs do not expose these exact canonical CSV layouts.

| Canonical table | Source field to canonical field |
|---|---|
| bus_od.csv | YEAR_MONTH to year_month; DAY_TYPE to day_type; TIME_PER_HOUR to hour; ORIGIN_PT_CODE to origin_stop_id; DESTINATION_PT_CODE to destination_stop_id; TOTAL_TRIPS to total_trips. PT_TYPE validates BUS and is omitted from output. |
| bus_stops.csv | BusStopCode to bus_stop_id; Description to description; RoadName to road_name; Latitude to latitude; Longitude to longitude. |
| rainfall.csv | timestamp to observed_at; station_id and rainfall_mm retained; source_updated_at and retrieved_at unavailable and left blank. |
| weather_stations.csv | station_id, station_name, latitude and longitude from rainfall rows; one selected metadata row per station. |
| carpark.csv | carpark_number to carpark_id; lot_type retained; update_datetime to observed_at; total_lots and lots_available retained; snapshot_time to response_at; retrieved_at unavailable and left blank. |

Identifiers remain strings, preserving leading zeroes. Naive per-carpark source
update times are interpreted as Singapore local time. Rainfall observation and
parking response timestamps require explicit offsets before normalisation.
response_at is the API response timestamp, not the request/retrieval time.

## Validation and Duplicate Rules

| Input | Validation and duplicate/conflict handling |
|---|---|
| Bus stops | Require an ID and valid coordinates. Exact repeated metadata is retained once; conflicting metadata for one ID stops preparation. |
| Bus OD | Validate BUS, month, day type, hour 0-23, non-empty IDs and non-negative integer trips. Key: month/day type/hour/origin/destination. Agreeing repeats count once; conflicts are logged and stop processing for investigation. |
| Rainfall | Require station ID, finite non-negative rainfall, valid coordinates and offset-aware timestamps on the five-minute grid. Key: station/time. Agreeing repeats count once. Conflicts stop for investigation because version timestamps are unavailable; no arbitrary latest version is claimed. |
| Parking | Require ID/lot type, parseable times, positive capacity and 0 <= availability <= capacity. Key: carpark/lot type/source update time. Agreeing repeats count once, retaining the latest response timestamp. Conflicting values stop because retrieval timestamps needed for version ordering are unavailable. |

No conflicting OD, rainfall or parking values were reported in these accepted
inputs. Conflict safeguards describe the implemented rules, not errors invented
for this submission. Quarantine records preserve the original rejected row.

## Cadence, Slots and Missing Data

Rainfall timestamps align exactly to :00, :05, :10 and the other five-minute
positions, with zero seconds. The sorted canonical station/time keys were checked
for uniqueness. No rounding or interpolation of off-grid readings was needed.
The ordinary daily denominator is 288; an hourly denominator would be 12,
although no hourly analysis is used here. Recorded zero rainfall remains valid.

Within the stated 89-station by 30-day reporting scope, there are 2,670 possible
station-days and 7,515 absent five-minute slots. Of the 2,654 observed station-days,
2,631 meet the 260-slot threshold and 23 are partial. Another 16 station-days have
no observations. M2 keeps incomplete days separately and reports null rainfall
for absent days. Station operating dates are unavailable, so this reporting scope
is not proof that every station should have operated on every date.

Parking has 720 distinct API response snapshots. Their median spacing is 3,600
seconds, with observed gaps of 3,596-3,604 seconds, consistent with the supplied
hourly sampling script. This is not a five-minute parking archive. Per-carpark
source update times are irregular; repeated updates are collapsed. Parking is
not forced onto a five-minute grid or assigned invented observations. Daily
occupancy is sample-weighted, so irregular sampling can affect the mean and
high-pressure fraction. Neither means vehicle arrivals or parking duration.

M4 uses the proportion of eligible stations reporting rain to classify dates.
It does not sum rainfall depths across stations or claim rainfall at each
carpark. Its 50% weather threshold and three-day-per-group minimum are declared
analysis choices. Days without eligible stations are excluded. Even a station-day
meeting 90% coverage can have missing readings, so no recorded rain does not
prove no rainfall occurred.

## Metadata Versions and Missing Information

The exact prepared bus-stop and weather-station snapshots are identified by their
SHA-256 values in the manifest. No publisher-issued version or historical
validity date was available. The weather-station name is selected from the latest
observation, with equal-time ties resolved alphabetically; alternate names are
recorded in the rainfall profile. A changed station coordinate stops preparation.

Original source-update/retrieval timestamps are unavailable for rainfall, and
retrieval timestamps are unavailable for parking. Those fields remain blank.
Filesystem modification times are not treated as acquisition times.

carparks.csv and carpark_station_map.csv are not created or used: M4 is a regional
date-based comparison, so no carpark coordinates, distance assignments or spatial
mapping version is claimed. Only September bus data was analysed; no additional
months or missing readings were simulated.

## File Fingerprints and Manifest

The [manifest](userfiles/metadata/manifest.json) records current file sizes,
CSV row counts, fields, periods, local SHA-256 fingerprints and intended HDFS
paths for all raw, canonical and quarantine files, plus the preparation profile.
It also identifies the preparation script version and metadata snapshots.

**This is a student-generated manifest.** A lecturer-issued manifest with expected
hashes was not available in the project files reviewed. The hashes below identify
the exact retained files; they are not invented expected hashes or a claim of
verification against a lecturer reference.

| Original raw file | Locally calculated SHA-256 |
|---|---|
| bus_stops.csv | `29767608073b1c379cc816054c07ac5cd448ce82bebcd65740e19d4030da138c` |
| carpark_20260901_20260930.csv | `9b4af13d990b9c702f241a8d4d4cdd3154a6ac66a9258bf0ef084600a27f0664` |
| origin_destination_bus_202609.csv | `1b45454a55e04051aa7ad1f678b209c0b4ca96e3f9ce9e38ea96223a5d7c6030` |
| rainfall_20260901_20260930.csv | `e61a74d98bac6b4b1ede00547e7338511538378c163caedc68e5b0ea26eea04d` |

## HDFS Evidence

The raw, canonical and quarantine datasets are stored under their corresponding
/sg_mobility/ directories. The manifest, this note and rainfall preparation
profile are stored under /sg_mobility/metadata/. The
[verification report](evidence/data-preparation/provenance-hdfs-verification.txt)
records directory listings and SHA-256 comparisons between HDFS file contents
and the local files in the manifest. A successful HDFS match confirms the
uploaded bytes match these local files; it does not replace lecturer-manifest
verification or establish historical source metadata that was not retained.
