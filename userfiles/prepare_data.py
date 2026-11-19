import csv
import json
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


# Run preparation when this script is executed directly. Create output folders
# if needed so the same command can be used on a fresh project copy.
if __name__ == "__main__":
    CANONICAL.mkdir(exist_ok=True)
    QUARANTINE.mkdir(exist_ok=True)
    prepare_bus_stops()