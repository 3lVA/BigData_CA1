#imports
import csv
import re
from mrjob.job import MRJob # import the class to build mapreduce job in python


#create the job & give it features of MRJob class
class M1BusCorridors(MRJob):
    """Find the busiest directed bus-stop pairs.""" #description of the job
    def mapper(self, _, line):
        try:
            fields = next(csv.reader([line]))
        except csv.Error:
            self.increment_counter("Input checks", "CSV parse error", 1)
            return

        if not fields:
            return

        fields = [field.strip() for field in fields]
        fields[0] = fields[0].lstrip("\ufeff")

        if fields[0] == "YEAR_MONTH":
            return

        if len(fields) != 7:
            self.increment_counter("Input checks", "Wrong column count", 1)
            return
        
        month, day_type, hour_text, transport, origin, destination, trips_text = fields

        if transport != "BUS":
            self.increment_counter("Input checks", "Non-bus record", 1)
            return

        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            self.increment_counter("Input checks", "Invalid month", 1)
            return

        if day_type not in {"WEEKDAY", "WEEKENDS/HOLIDAY"}:
            self.increment_counter("Input checks", "Invalid day type", 1)
            return

        if not origin or not destination:
            self.increment_counter("Input checks", "Missing stop ID", 1)
            return

        try:
            hour = int(hour_text)
            trips = int(trips_text)
        except ValueError:
            self.increment_counter("Input checks", "Invalid integer", 1)
            return

        if not 0 <= hour <= 23 or trips < 0:
            self.increment_counter("Input checks", "Invalid hour or trips", 1)
            return

        yield (month, day_type, hour, origin, destination), trips
    
if __name__ == "__main__":
    M1BusCorridors.run()

# check if the file is being executed directly
if __name__ == "__main__":
    M1BusCorridors.run() #start the job when execute script
    
