import csv
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Resolve paths from this script so preparation works from any working directory.
# These folders are shared with the client through the existing userfiles mount.
BASE = Path(__file__).resolve().parent
RAW = BASE / "ca1-data"
CANONICAL = BASE / "canonical_data"
QUARANTINE = BASE / "quarantine_data"

def prepare_bus_stops():
    # Read raw columns in the order required by the canonical output schema.
    source_columns = [
        "BusStopCode",
        "Description",
        "RoadName",
        "Latitude",
        "Longitude",
    ]

    # Key accepted records by stop ID to detect repeats and conflicting metadata.
    # Keep rejected source records with reasons so exclusions can be inspected.
    accepted = {}
    rejected = []
    total = 0

    # utf-8-sig handles a possible byte-order mark before the first header.
    # newline="" lets the csv module handle CSV line endings correctly.
    with (RAW / "bus_stops.csv").open(
        newline="", encoding="utf-8-sig"
    ) as source:
        # Access fields by name so their source-to-canonical mapping is explicit.
        reader = csv.DictReader(source)

        # Stop on missing required headers rather than processing the wrong schema.
        if not set(source_columns).issubset(reader.fieldnames or []):
            raise ValueError("The bus-stop CSV has unexpected headers.")

        for row in reader: 
            # Count each source row and trim whitespace from the selected fields.
            total += 1
            record = [
                (row.get(column) or "").strip()
                for column in source_columns
            ]
            # Preserve the ID as text so values such as 01012 keep their leading zero.
            stop_id = record[0]
            reason = ""

            # DictReader uses a None key for surplus fields. Reject these rows
            # and missing IDs because they cannot form a reliable metadata record.
            if None in row:
                reason = "extra_columns"
            elif not stop_id:
                reason = "missing_stop_id"
            else:
                # Validate numeric coordinates and geographical bounds before acceptance.
                # Keep the original coordinate text in the output to avoid rounding it.
                try:
                    latitude = float(record[3])
                    longitude = float(record[4])

                    if not (
                        -90 <= latitude <= 90
                        and -180 <= longitude <= 180
                    ):
                        raise ValueError
                except ValueError:
                    reason = "invalid_coordinates"

            # Preserve the original row as JSON with a reason, then skip acceptance.
            if reason:
                rejected.append([reason, json.dumps(row)])
                continue

            # An exact repeat contributes once. Different metadata for the same ID
            # needs investigation, so stop instead of choosing a version silently.
            if stop_id in accepted:
                if record != accepted[stop_id]:
                    raise ValueError(
                        f"Conflicting metadata for stop {stop_id}"
                    )

                rejected.append([
                    "exact_duplicate",
                    json.dumps(row),
                ])
                continue

            accepted[stop_id] = record

    # Write the validated records with the column names specified in Appendix A.
    with (CANONICAL / "bus_stops.csv").open(
        "w", newline="", encoding="utf-8"
    ) as destination:
        writer = csv.writer(destination)
        writer.writerow([
            "bus_stop_id",
            "description",
            "road_name",
            "latitude",
            "longitude",
        ])
        writer.writerows(accepted.values())

    # Always write a quarantine header, even when no records were excluded.
    with (QUARANTINE / "bus_stops_quarantine.csv").open(
        "w", newline="", encoding="utf-8"
    ) as destination:
        writer = csv.writer(destination)
        writer.writerow(["reason", "raw_record"])
        writer.writerows(rejected)

    # Report counts for provenance and verify input = accepted + excluded.
    print(
        f"Bus stops: input={total}, "
        f"accepted={len(accepted)}, excluded={len(rejected)}"
    )


def prepare_bus_od():
    source_path = RAW / "origin_destination_bus_202609.csv"
    output_path = CANONICAL / "bus_od.csv"
    temporary_path = CANONICAL / "bus_od.csv.tmp"
    quarantine_path = QUARANTINE / "bus_od_quarantine.csv"

    source_columns = [
        "YEAR_MONTH",
        "DAY_TYPE",
        "TIME_PER_HOUR",
        "PT_TYPE",
        "ORIGIN_PT_CODE",
        "DESTINATION_PT_CODE",
        "TOTAL_TRIPS",
    ]

    # Use the prepared metadata to identify unmatched stop IDs.
    # Unmatched historic stops remain in the OD analysis.
    with (CANONICAL / "bus_stops.csv").open(
        newline="", encoding="utf-8"
    ) as source:
        known_stops = {
            row["bus_stop_id"]
            for row in csv.DictReader(source)
        }

    # Remember each full OD key and its trip count to distinguish
    # repeated records from conflicting values for the same key.
    seen = {}
    total = 0
    excluded = 0
    duplicates = 0
    unmatched_rows = 0
    months = set()

    # Publish the canonical file only after preparation succeeds,
    # keeping a failed run from publishing a partial final file.
    with source_path.open(newline="", encoding="utf-8-sig") as source, \
         temporary_path.open("w", newline="", encoding="utf-8") as output, \
         quarantine_path.open("w", newline="", encoding="utf-8") as rejected:

        reader = csv.DictReader(source)
        writer = csv.writer(output)
        quarantine_writer = csv.writer(rejected)

        if not set(source_columns).issubset(reader.fieldnames or []):
            raise ValueError("The bus OD CSV has unexpected headers.")

        # Use the canonical column names and order from Appendix A.
        writer.writerow([
            "year_month",
            "day_type",
            "hour",
            "origin_stop_id",
            "destination_stop_id",
            "total_trips",
        ])
        quarantine_writer.writerow(["reason", "raw_record"])

        for row in reader:
            total += 1
            reason = ""

            # Reject surplus or missing fields before extracting values.
            if None in row or any(
                row.get(column) is None for column in source_columns
            ):
                excluded += 1
                quarantine_writer.writerow([
                    "wrong_column_count",
                    json.dumps(row),
                ])
                continue

            month, day_type, hour_text, transport, origin, destination, trips_text = [
                row[column].strip()
                for column in source_columns
            ]

            # Preserve stop IDs as strings, including leading zeroes.
            # Validate source fields before accepting their passenger counts.
            if transport != "BUS":
                reason = "non_bus_record"
            elif not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
                reason = "invalid_month"
            elif day_type not in {"WEEKDAY", "WEEKENDS/HOLIDAY"}:
                reason = "invalid_day_type"
            elif not origin or not destination:
                reason = "missing_stop_id"
            else:
                try:
                    hour = int(hour_text)
                    trips = int(trips_text)
                except ValueError:
                    reason = "invalid_integer"
                else:
                    if not 0 <= hour <= 23:
                        reason = "invalid_hour"
                    elif trips < 0:
                        reason = "negative_trip_count"

            # Retain rejected source records with a reason for the audit trail.
            if reason:
                excluded += 1
                quarantine_writer.writerow([
                    reason,
                    json.dumps(row),
                ])
                continue

            # Different hours are distinct source aggregates.
            # M1 will combine their passenger totals after preparation.
            key = (month, day_type, hour, origin, destination)

            if key in seen:
                if trips != seen[key]:
                    # Record the conflict and stop for investigation instead
                    # of selecting an arbitrary passenger count.
                    quarantine_writer.writerow([
                        "conflicting_od_key",
                        json.dumps(row),
                    ])
                    raise ValueError(
                        f"Conflicting trip counts for {key}: "
                        f"{seen[key]} and {trips}"
                    )

                # Keep one copy of an agreed record and log the extra copy.
                excluded += 1
                duplicates += 1
                quarantine_writer.writerow([
                    "exact_duplicate",
                    json.dumps(row),
                ])
                continue

            seen[key] = trips
            months.add(month)

            # A valid OD record remains accepted when metadata is missing.
            # Count unmatched rows so this limitation can be disclosed.
            if origin not in known_stops or destination not in known_stops:
                unmatched_rows += 1

            writer.writerow([
                month,
                day_type,
                hour,
                origin,
                destination,
                trips,
            ])

    temporary_path.replace(output_path)

    print(
        f"Bus OD: input={total}, accepted={len(seen)}, "
        f"excluded={excluded}, duplicates={duplicates}, "
        f"unmatched_stop_rows={unmatched_rows}"
    )
    print(f"Bus OD months: {', '.join(sorted(months))}")


def prepare_rainfall():
    source_path = RAW / "rainfall_20260901_20260930.csv"
    # Convert observation times to Singapore time before grouping by date.
    singapore = timezone(timedelta(hours=8))
    # Keep one reading per station/time and one metadata record per station.
    # Record alternate station names so metadata choices can be explained.
    readings = {}
    stations = {}
    aliases = {}
    total = 0
    excluded = 0
    duplicates = 0

    required_columns = {
        "timestamp",
        "station_id",
        "station_name",
        "latitude",
        "longitude",
        "rainfall_mm",
    }

    # Read the source using column names and save excluded rows with reasons.
    # utf-8-sig handles a possible byte-order mark in the CSV header.
    with source_path.open(newline="", encoding="utf-8-sig") as source, \
         (QUARANTINE / "rainfall_quarantine.csv").open(
             "w", newline="", encoding="utf-8"
         ) as rejected:
        reader = csv.DictReader(source)
        quarantine_writer = csv.writer(rejected)
        quarantine_writer.writerow(["reason", "raw_record"])
        # Stop if required columns are missing, as with bus preparation.
        if not required_columns.issubset(reader.fieldnames or []):
            raise ValueError("The rainfall CSV has unexpected headers.")

        for row in reader:
            total += 1
            # Reject rows with extra or missing values before parsing them.
            if None in row or any(
                row.get(name) is None for name in required_columns
            ):
                excluded += 1
                quarantine_writer.writerow(["wrong_column_count", json.dumps(row)])
                continue

            station_id = row["station_id"].strip()
            station_name = row["station_name"].strip()
            reason = ""

            # Require a timezone offset so the observation date is unambiguous.
            try:
                observed = datetime.fromisoformat(
                    row["timestamp"].strip().replace("Z", "+00:00")
                )
                if observed.tzinfo is None:
                    raise ValueError
                observed = observed.astimezone(singapore)
            except ValueError:
                reason = "invalid_or_missing_timezone_timestamp"

            if not reason and not station_id:
                reason = "missing_station_id"

            if not reason:
                # The source uses slots such as 00:00, 00:05 and 00:10.
                # Exclude timestamps outside that checked five-minute grid.
                if observed.minute % 5 or observed.second or observed.microsecond:
                    reason = "off_grid_timestamp"

            if not reason:
                # Decimal keeps values such as 0.2 exact. Zero rainfall is valid.
                try:
                    rainfall = Decimal(row["rainfall_mm"].strip())
                    if not rainfall.is_finite() or rainfall < 0:
                        raise ValueError
                except (InvalidOperation, ValueError):
                    reason = "invalid_rainfall"

            if not reason:
                # Check station coordinates before writing the metadata file.
                try:
                    latitude = float(row["latitude"])
                    longitude = float(row["longitude"])
                    if not (
                        -90 <= latitude <= 90
                        and -180 <= longitude <= 180
                    ):
                        raise ValueError
                except ValueError:
                    reason = "invalid_station_coordinates"

            # Retain the original record and reason for each exclusion.
            if reason:
                excluded += 1
                quarantine_writer.writerow([reason, json.dumps(row)])
                continue

            # A station/time key identifies one observation.
            # Exact repeats contribute once so rainfall is not double-counted.
            key = (station_id, observed)
            if key in readings:
                if rainfall != readings[key]:
                    # This source lacks the version times needed to choose
                    # between conflicting readings. Log the conflict and stop.
                    quarantine_writer.writerow([
                        "conflicting_reading_without_version_timestamps",
                        json.dumps(row),
                    ])
                    raise ValueError(
                        f"Conflicting rainfall for {station_id} at {observed.isoformat()}"
                    )
                excluded += 1
                duplicates += 1
                quarantine_writer.writerow(["exact_duplicate", json.dumps(row)])
                continue

            readings[key] = rainfall
            aliases.setdefault(station_id, set()).add(station_name)

            # A changed station location needs a validity-date check.
            if station_id in stations:
                previous = stations[station_id]
                if (latitude, longitude) != (previous[2], previous[3]):
                    quarantine_writer.writerow([
                        "station_location_changed",
                        json.dumps(row),
                    ])
                    raise ValueError(
                        f"Check location validity dates for station {station_id}"
                    )

            # Some station IDs have alternate names at the same coordinates.
            # Select the latest observed name. Equal-time ties use the greater
            # name alphabetically, making repeated runs choose consistently.
            metadata = (observed, station_name, latitude, longitude)
            if (
                station_id not in stations
                or metadata[:2] > stations[station_id][:2]
            ):
                stations[station_id] = metadata

    # Write the canonical schema after all records have been checked.
    # Missing source-update and retrieval times stay blank and are disclosed.
    temporary_path = CANONICAL / "rainfall.csv.tmp"
    with temporary_path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.writer(destination)
        writer.writerow([
            "station_id", "observed_at", "rainfall_mm",
            "source_updated_at", "retrieved_at",
        ])
        for (station_id, observed), rainfall in sorted(readings.items()):
            writer.writerow([
                station_id, observed.isoformat(), str(rainfall), "", "",
            ])
    # Publish the finished CSV only after its output has been written.
    temporary_path.replace(CANONICAL / "rainfall.csv")

    # Write one station metadata row for later lookup by the analyses.
    with (CANONICAL / "weather_stations.csv").open(
        "w", newline="", encoding="utf-8"
    ) as destination:
        writer = csv.writer(destination)
        writer.writerow(["station_id", "station_name", "latitude", "longitude"])
        for station_id, (_, name, latitude, longitude) in sorted(stations.items()):
            writer.writerow([station_id, name, latitude, longitude])

    times = [observed for _, observed in readings]
    start = min(times).isoformat() if times else None
    end = max(times).isoformat() if times else None

    # Save counts, dates, missing source fields and alternate names.
    # This supplies evidence for the documentation and later manifest.
    profile = {
        "input_rows": total,
        "accepted_unique_slots": len(readings),
        "excluded_rows": excluded,
        "duplicates_removed": duplicates,
        "station_count": len(stations),
        "timezone": "Asia/Singapore (UTC+08:00)",
        "observed_start": start,
        "observed_end": end,
        "slot_rule": "Exact five-minute timestamps; off-grid rows quarantined.",
        "unavailable_source_fields": ["source_updated_at", "retrieved_at"],
        "conflict_rule": "Stop for investigation when version timestamps are unavailable.",
        "metadata_rule": "Latest observation time, then lexicographically greatest station name.",
        "station_name_aliases": {
            station_id: sorted(names)
            for station_id, names in sorted(aliases.items())
            if len(names) > 1
        },
    }
    with (CANONICAL / "rainfall_profile.json").open(
        "w", encoding="utf-8"
    ) as destination:
        json.dump(profile, destination, indent=2, ensure_ascii=False)
        destination.write("\n")

    # Report counts so input can be checked against accepted plus excluded.
    print(
        f"Rainfall: input={total}, accepted={len(readings)}, "
        f"excluded={excluded}, duplicates={duplicates}, stations={len(stations)}"
    )
    print(f"Rainfall period: {start} to {end}")
    print(
        "Rainfall provenance: source_updated_at and retrieved_at "
        "are unavailable in the downloaded CSV."
    )


# Run preparation when this script is executed directly. Create output folders
# if needed so the same command can be used on a fresh project copy.
if __name__ == "__main__":
    CANONICAL.mkdir(exist_ok=True)
    QUARANTINE.mkdir(exist_ok=True)
    # Prepare metadata first because OD preparation uses its stop IDs.
    prepare_bus_stops()
    prepare_bus_od()
    prepare_rainfall()