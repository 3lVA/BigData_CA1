import csv
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from mrjob.job import MRJob
from mrjob.step import MRStep


SINGAPORE = timezone(timedelta(hours=8))
REPORT_MONTH = "2026-09"
MINIMUM_RAIN_SLOTS = 260  # At least 90% of the 288 expected daily slots.
MINIMUM_DAYS = 3  # Declared analysis choice: require support in both groups.
PRECISION = Decimal("0.000001")
WET = "widespread_rainfall"
NO_RAIN = "no_recorded_rainfall"


def reported(value):
    # Round only the final results; intermediate calculations retain precision.
    return str(value.quantize(PRECISION, rounding=ROUND_HALF_UP))


def combine_counts(values):
    count = 0
    total = Decimal("0")
    for observations, amount in values:
        count += observations
        total += Decimal(amount)
    return count, total


class M4RainfallParking(MRJob):
    """Compare daily parking occupancy between regional weather groups."""

    def mapper(self, _, line):
        # The two canonical input schemas have different column counts.
        # Read only frozen, validated, deduplicated preparation outputs.
        fields = next(csv.reader([line]))
        if not fields:
            return
        fields = [field.strip() for field in fields]
        fields[0] = fields[0].lstrip("\ufeff")
        if fields[0] in ("station_id", "carpark_id"):
            return

        if len(fields) == 5:
            station, time_text, rain_text, _, _ = fields
            observed = datetime.fromisoformat(time_text)
            if observed.tzinfo is None:
                raise ValueError("Rainfall source time requires a timezone.")
            observed = observed.astimezone(SINGAPORE)
            rain = Decimal(rain_text)
            if not station or not rain.is_finite() or rain < 0:
                raise ValueError("Invalid canonical rainfall value.")
            if observed.minute % 5 or observed.second or observed.microsecond:
                raise ValueError("Rainfall must follow the five-minute slot grid.")
            if observed.strftime("%Y-%m") != REPORT_MONTH:
                return
            # R keys retain station identity until daily coverage is calculated.
            yield ("R", observed.date().isoformat(), station), (1, str(rain))

        elif len(fields) == 7:
            carpark, lot_type, time_text, capacity_text, available_text, _, _ = fields
            if lot_type != "C":
                return
            capacity = int(capacity_text)
            available = int(available_text)
            if not carpark or capacity <= 0 or not 0 <= available <= capacity:
                raise ValueError("Invalid canonical parking value.")
            observed = datetime.fromisoformat(time_text)
            if observed.tzinfo is None:
                raise ValueError("Parking source time requires a timezone.")
            observed = observed.astimezone(SINGAPORE)
            if observed.strftime("%Y-%m") != REPORT_MONTH:
                return
            occupancy = Decimal(capacity - available) / Decimal(capacity)
            yield ("P", observed.date().isoformat(), carpark), (1, str(occupancy))
        else:
            raise ValueError("Expected canonical rainfall or carpark CSV columns.")

    def combiner_daily(self, key, values):
        # Preserve sums and counts; never average partial averages.
        count, total = combine_counts(values)
        yield key, (count, str(total))

    def reducer_daily(self, key, values):
        kind, day, identifier = key
        count, total = combine_counts(values)
        if kind == "R":
            if count > 288:
                raise ValueError("More than 288 rainfall slots: check deduplication.")
            if count < MINIMUM_RAIN_SLOTS:
                self.increment_counter("M4 checks", "Ineligible station-days", 1)
                return
            # Rainfall sums remain station-specific; only a rain/no-rain indicator
            # enters the regional proportion. Do not sum rainfall across stations.
            yield day, ("R", identifier, int(total > 0), count)
        else:
            yield day, ("P", identifier, str(total / count), count)

    def reducer_join_date(self, day, records):
        # Stage 2 performs the reduce-side date join. A day holds only daily
        # summaries, not all the original five-minute observations.
        eligible_stations = 0
        wet_stations = 0
        parking = []
        for kind, identifier, value, count in records:
            if kind == "R":
                eligible_stations += 1
                wet_stations += value
            else:
                parking.append((identifier, value, count))

        if eligible_stations == 0:
            self.increment_counter("M4 checks", "Dates without eligible stations", 1)
            return
        if wet_stations == 0:
            category = NO_RAIN
        elif 2 * wet_stations >= eligible_stations:
            category = WET  # Declared threshold: at least 50% of eligible stations.
        else:
            self.increment_counter("M4 checks", "Intermediate weather dates", 1)
            return

        self.increment_counter("M4 weather dates", category, 1)
        for carpark, mean, count in parking:
            # A common key sends compact daily summaries to the final reducer.
            yield None, (carpark, category, mean, count)

    def reducer_compare(self, _, records):
        # Accumulate summaries incrementally. Memory depends on carpark count,
        # rather than retaining every raw observation or carpark-day record.
        carparks = {}
        for carpark, category, mean, observations in records:
            groups = carparks.setdefault(carpark, {})
            group = groups.setdefault(category, [0, Decimal("0"), 0])
            group[0] += 1
            group[1] += Decimal(mean)
            group[2] += observations

        top10 = []
        for carpark, groups in sorted(carparks.items()):
            wet = groups.get(WET, [0, Decimal("0"), 0])
            no_rain = groups.get(NO_RAIN, [0, Decimal("0"), 0])
            if min(wet[0], no_rain[0]) < MINIMUM_DAYS:
                self.increment_counter("M4 checks", "Carparks below minimum days", 1)
                continue

            # Give each contributing day equal weight within its weather group.
            wet_mean = wet[1] / wet[0]
            no_rain_mean = no_rain[1] / no_rain[0]
            difference = (wet_mean - no_rain_mean) * 100
            result = {
                "carpark_id": carpark,
                "widespread_rainfall_days": wet[0],
                "no_recorded_rainfall_days": no_rain[0],
                "widespread_rainfall_observations": wet[2],
                "no_recorded_rainfall_observations": no_rain[2],
                "widespread_rainfall_mean_occupancy_ratio": reported(wet_mean),
                "no_recorded_rainfall_mean_occupancy_ratio": reported(no_rain_mean),
                "difference_percentage_points": reported(difference),
                "absolute_difference_percentage_points": reported(abs(difference)),
            }
            yield ("comparison", carpark), result
            # Rank using the unrounded difference, then carpark ID for ties.
            top10.append((abs(difference), carpark, result))
            top10.sort(key=lambda item: (-item[0], item[1]))
            if len(top10) > 10:
                top10.pop()

        for rank, (_, carpark, result) in enumerate(top10, start=1):
            yield ("top10", rank), dict(result, rank=rank)

    def steps(self):
        return [
            MRStep(mapper=self.mapper, combiner=self.combiner_daily,
                   reducer=self.reducer_daily),
            MRStep(reducer=self.reducer_join_date),
            MRStep(reducer=self.reducer_compare),
        ]


def create_sample():
    # Select actual canonical records; never generate simulated readings.
    # The one-station subset tests the logic, not full-network weather labels.
    base = Path(__file__).resolve().parents[1]
    dates = {"2026-09-03", "2026-09-04", "2026-09-05",
             "2026-09-21", "2026-09-22", "2026-09-27"}
    sample_dir = base / "mapreduce"
    for filename, sample_name in (
        ("rainfall.csv", "m4_sample_rainfall.csv"),
        ("carpark.csv", "m4_sample_carpark.csv"),
    ):
        count = 0
        with (base / "canonical_data" / filename).open(
            newline="", encoding="utf-8-sig"
        ) as source, (sample_dir / sample_name).open(
            "w", newline="", encoding="utf-8"
        ) as target:
            reader = csv.DictReader(source)
            writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                day = row["observed_at"][:10]
                if day not in dates:
                    continue
                if filename == "rainfall.csv":
                    keep = row["station_id"] == "S306"
                else:
                    # A10 has all six dates. A11 deliberately lacks 27 September
                    # in the sample, testing exclusion below three rainy days.
                    keep = row["lot_type"] == "C" and (
                        row["carpark_id"] == "A10" or
                        (row["carpark_id"] == "A11" and day != "2026-09-27")
                    )
                if keep:
                    writer.writerow(row)
                    count += 1
        print(f"{sample_name}: {count} actual records")
    print("Sample only: S306; six dates; A11 deliberately omits 27 September.")
    print("Full canonical files are unchanged.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--create-sample"]:
        create_sample()
    else:
        M4RainfallParking.run()
