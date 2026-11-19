import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from mrjob.job import MRJob
from mrjob.step import MRStep


SINGAPORE = timezone(timedelta(hours=8))
EXPECTED_SLOTS = 288
MINIMUM_SLOTS = 260


def sum_readings(values):
    # The prepared input has one valid reading per station/time slot.
    total = Decimal("0")
    count = 0
    for rainfall, observations in values:
        total += Decimal(rainfall)
        count += observations
    return total, count


def daily_result(station_id, day, total, count):
    # Calculate every station-day using the same coverage and missing-data rules.
    status = "partial"
    if count >= MINIMUM_SLOTS:
        status = "eligible"
    if count == 0:
        status = "no_observations"

    return {
        "station_id": station_id,
        "date": day,
        "total_observed_rainfall_mm": str(total) if count else None,
        "valid_observations": count,
        "expected_observations": EXPECTED_SLOTS,
        "coverage_percent": round(count / EXPECTED_SLOTS * 100, 2),
        "status": status,
    }


class M2RainfallStationDay(MRJob):
    """Calculate station-day rainfall and rank days with at least 90% coverage."""

    def mapper(self, _, line):
        # Read the five-column canonical CSV and skip its header.
        fields = next(csv.reader([line]))
        if not fields:
            return
        fields = [field.strip() for field in fields]
        fields[0] = fields[0].lstrip("\ufeff")
        if fields[0] == "station_id":
            return
        if len(fields) != 5:
            raise ValueError("M2 requires the canonical rainfall CSV.")

        station_id, observed_text, rainfall_text, _, _ = fields
        observed = datetime.fromisoformat(observed_text)
        if observed.tzinfo is None:
            raise ValueError("Observation time requires a timezone.")
        observed = observed.astimezone(SINGAPORE)
        rainfall = Decimal(rainfall_text)

        if not station_id or not rainfall.is_finite() or rainfall < 0:
            raise ValueError("Invalid canonical rainfall record.")
        if observed.minute % 5 or observed.second or observed.microsecond:
            raise ValueError("Observation is outside the five-minute grid.")

        # Group by station and Singapore date. A zero reading still counts.
        yield (station_id, observed.date().isoformat()), (str(rainfall), 1)

    def combiner_daily(self, key, values):
        # Combine matching readings locally to reduce shuffle traffic.
        total, count = sum_readings(values)
        yield key, (str(total), count)

    def reducer_daily(self, key, values):
        station_id, day = key
        total, count = sum_readings(values)
        if count > EXPECTED_SLOTS:
            raise ValueError("More than 288 slots: check input preparation.")

        # Send daily summaries to the next stage for ranking and gap reporting.
        yield None, daily_result(station_id, day, total, count)

    def reducer_results(self, _, records):
        # Daily summaries are much smaller than the original readings.
        # Use their station IDs and first/last dates as the reporting scope.
        days = list(records)
        station_ids = sorted({record["station_id"] for record in days})
        seen = {(record["station_id"], record["date"]) for record in days}
        first_day = date.fromisoformat(min(record["date"] for record in days))
        last_day = date.fromisoformat(max(record["date"] for record in days))

        # Report absent days inside this scope with zero observations
        # and null rainfall. Station operating dates are unavailable.
        day = first_day
        while day <= last_day:
            day_text = day.isoformat()
            for station_id in station_ids:
                if (station_id, day_text) not in seen:
                    days.append(daily_result(station_id, day_text, None, 0))
            day += timedelta(days=1)

        eligible = []
        for record in sorted(
            days, key=lambda record: (record["station_id"], record["date"])
        ):
            station_id = record["station_id"]
            day_text = record["date"]
            yield ("daily", station_id, day_text), record

            if record["status"] == "eligible":
                eligible.append(record)
            else:
                # Keep partial and completely absent days separately.
                yield ("partial", station_id, day_text), record

        # Rank rainfall descending, then station ID and date for stable ties.
        top10 = sorted(
            eligible,
            key=lambda record: (
                -Decimal(record["total_observed_rainfall_mm"]),
                record["station_id"],
                record["date"],
            ),
        )[:10]
        for rank, record in enumerate(top10, start=1):
            result = dict(record)
            result["rank"] = rank
            yield ("top10", rank), result

    def steps(self):
        return [
            MRStep(
                mapper=self.mapper,
                combiner=self.combiner_daily,
                reducer=self.reducer_daily,
            ),
            MRStep(reducer=self.reducer_results),
        ]


if __name__ == "__main__":
    M2RainfallStationDay.run()
