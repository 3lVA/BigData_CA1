import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from mrjob.job import MRJob


SINGAPORE = timezone(timedelta(hours=8))
RATIO_PRECISION = Decimal("0.000001")


def combine_observations(values):
    # Preserve counts, ratio sums, maxima and pressure counts when combining.
    count = 0
    ratio_sum = Decimal("0")
    maximum = Decimal("0")
    pressure_count = 0

    for observations, partial_sum, partial_maximum, pressured in values:
        count += observations
        ratio_sum += Decimal(partial_sum)
        maximum = max(maximum, Decimal(partial_maximum))
        pressure_count += pressured

    return count, ratio_sum, maximum, pressure_count


class M3ParkingPressure(MRJob):
    """Calculate sample-weighted parking pressure per carpark and source date."""

    def mapper(self, _, line):
        # Read prepared observations; preparation already removed repeats.
        fields = next(csv.reader([line]))
        if not fields:
            return
        fields = [field.strip() for field in fields]
        fields[0] = fields[0].lstrip("\ufeff")
        if fields[0] == "carpark_id":
            return
        if len(fields) != 7:
            raise ValueError("M3 requires the seven-column canonical carpark CSV.")

        carpark_id, lot_type, observed_text, total_text, available_text, _, _ = fields

        # Keep car lots only. Other valid lot types were preserved in preparation.
        if lot_type != "C":
            return

        capacity = int(total_text)
        available = int(available_text)
        if not carpark_id or capacity <= 0 or not 0 <= available <= capacity:
            raise ValueError("Invalid canonical parking values.")

        observed = datetime.fromisoformat(observed_text)
        if observed.tzinfo is None:
            raise ValueError("Canonical source time requires a timezone.")
        observed = observed.astimezone(SINGAPORE)

        # Calculate occupancy with this observation's own capacity.
        occupied = capacity - available
        ratio = Decimal(occupied) / Decimal(capacity)

        # Compare integers for an exact >=90% decision before rounding.
        pressured = int(10 * occupied >= 9 * capacity)

        # Source observation date controls grouping, including older update dates.
        yield (carpark_id, observed.date().isoformat()), (
            1, str(ratio), str(ratio), pressured
        )

    def combiner(self, key, values):
        # Local aggregation reduces shuffle while preserving the final statistics.
        count, ratio_sum, maximum, pressure_count = combine_observations(values)
        yield key, (count, str(ratio_sum), str(maximum), pressure_count)

    def reducer(self, key, values):
        count, ratio_sum, maximum, pressure_count = combine_observations(values)

        # Give each unique valid observation equal weight in the mean.
        mean = ratio_sum / Decimal(count)
        pressure_fraction = Decimal(pressure_count) / Decimal(count)

        # Report ratios consistently to six decimal places using half-up rounding.
        yield key, {
            "valid_observations": count,
            "mean_occupancy_ratio": str(
                mean.quantize(RATIO_PRECISION, rounding=ROUND_HALF_UP)
            ),
            "max_occupancy_ratio": str(
                maximum.quantize(RATIO_PRECISION, rounding=ROUND_HALF_UP)
            ),
            "observations_at_least_90_percent": pressure_count,
            "fraction_at_least_90_percent": str(
                pressure_fraction.quantize(RATIO_PRECISION, rounding=ROUND_HALF_UP)
            ),
        }


if __name__ == "__main__":
    M3ParkingPressure.run()
