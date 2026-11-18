import csv

from mrjob.job import MRJob


class CountBusStopRecords(MRJob):
    def mapper(self, _, line):
        fields = next(csv.reader([line]))
        if fields and fields[0].strip().lstrip("\ufeff").upper() != "BUSSTOPCODE":
            yield "bus_stop_records", 1

    def reducer(self, key, counts):
        yield key, sum(counts)


if __name__ == "__main__":
    CountBusStopRecords.run()