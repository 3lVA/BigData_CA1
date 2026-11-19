import csv

from mrjob.job import MRJob
from mrjob.step import MRStep


class M1BusCorridors(MRJob):
    """Rank directed bus-stop pairs using prepared canonical inputs."""

    def configure_args(self):
        super().configure_args()
        # mrjob makes this small metadata file available to the job's tasks.
        self.add_file_arg(
            "--stops",
            required=True,
            help="Path to the canonical bus_stops.csv file",
        )

    def mapper(self, _, line):
        # Preparation has already validated and deduplicated the source.
        # This job reads the six-column canonical OD schema.
        fields = next(csv.reader([line]))
        if not fields:
            return

        fields = [field.strip() for field in fields]
        fields[0] = fields[0].lstrip("\ufeff")
        if fields[0] == "year_month":
            return
        if len(fields) != 6:
            raise ValueError("M1 requires the six-column canonical bus OD file.")

        month, day_type, hour, origin, destination, trips_text = fields
        trips = int(trips_text)
        if not month or not day_type or not origin or not destination or trips < 0:
            raise ValueError("Invalid canonical OD record. Check data preparation.")

        # Leave the hour out of the key so all hours for the same directed
        # pair are grouped together. Preserve stop IDs as strings.
        yield (month, day_type, origin, destination), trips

    def combiner_sum(self, key, trip_counts):
        # Add matching values within mapper output to reduce shuffle traffic.
        yield key, sum(trip_counts)

    def reducer_sum(self, key, trip_counts):
        month, day_type, origin, destination = key

        # Calculate each pair's total, then change the key so the next
        # stage compares pairs within the same month and day type.
        yield (month, day_type), (sum(trip_counts), origin, destination)

    def reducer_top10_init(self):
        # Load the small prepared metadata once per ranking reducer.
        # Each final pair uses this lookup for both endpoints.
        with open(self.options.stops, newline="", encoding="utf-8-sig") as source:
            self.stops = {
                row["bus_stop_id"]: row["description"]
                for row in csv.DictReader(source)
            }

    def reducer_top10(self, key, pairs):
        top_pairs = []
        unmatched_stops = set()

        for trips, origin, destination in pairs:
            # Check every corridor, including those outside the top ten,
            # so the result discloses all unmatched IDs in this group.
            if origin not in self.stops:
                unmatched_stops.add(origin)
            if destination not in self.stops:
                unmatched_stops.add(destination)

            # Keep only the best ten candidates to limit memory use.
            # Rank by trips descending, then origin and destination ascending.
            top_pairs.append((trips, origin, destination))
            top_pairs.sort(key=lambda pair: (-pair[0], pair[1], pair[2]))
            if len(top_pairs) > 10:
                top_pairs.pop()

        results = []
        for rank, (trips, origin, destination) in enumerate(top_pairs, start=1):
            results.append({
                "rank": rank,
                "origin_stop_id": origin,
                "origin_description": self.stops.get(origin, "UNMATCHED_STOP"),
                "destination_stop_id": destination,
                "destination_description": self.stops.get(
                    destination, "UNMATCHED_STOP"
                ),
                "total_trips": trips,
            })

        # One result per month/day-type group contains its top ten and
        # a separate list of unmatched stop IDs for transparent reporting.
        yield key, {
            "top10": results,
            "unmatched_stop_ids": sorted(unmatched_stops),
        }

    def steps(self):
        return [
            MRStep(
                mapper=self.mapper,
                combiner=self.combiner_sum,
                reducer=self.reducer_sum,
            ),
            MRStep(
                reducer_init=self.reducer_top10_init,
                reducer=self.reducer_top10,
            ),
        ]


if __name__ == "__main__":
    M1BusCorridors.run()
