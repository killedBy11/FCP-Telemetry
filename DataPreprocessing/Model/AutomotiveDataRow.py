import csv


# Wrapper class for rows in csv files. Makes it easier to process the data read
class AutomotiveDataRow:
    latest = None
    speed = None
    load = None
    MAP = None
    IAT = None
    RPM = None
    distance = None
    fuel_used = None
    fuel_consumption = None
    instant_fuel_consumption = None
    latitude = None
    longitude = None
    altitude = None
    heading = None
    speed_gps = None
    time_gps = None
    x = None
    y = None
    z = None
    AAP = None
    AAT = None

    def __init__(self, header=None, row=None):
        if header is not None and row is not None:
            self.load_from_csv_row(header, row)

    def load_from_csv_row(self, header, row):
        assert len(header) == len(row)
        for i in range(len(header)):
            if header[i] == 'LATITUDE':
                try:
                    self.latitude = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'LONGITUDE':
                try:
                    self.longitude = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'ALTITUDE':
                try:
                    self.altitude = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'HEADING':
                try:
                    self.heading = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'SPEED':
                try:
                    self.speed = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'SPEED_GPS':
                try:
                    self.speed_gps = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'TIME_GPS':
                try:
                    self.time_gps = row[i]
                except ValueError:
                    pass
            elif header[i] == 'X':
                try:
                    self.x = int(row[i])
                except ValueError:
                    pass
            elif header[i] == 'Y':
                try:
                    self.y = int(row[i])
                except ValueError:
                    pass
            elif header[i] == 'Z':
                try:
                    self.z = int(row[i])
                except ValueError:
                    pass
            elif header[i] == 'AAP':
                try:
                    self.AAP = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'AAT':
                try:
                    self.AAT = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'LOAD':
                try:
                    self.load = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'MAP':
                try:
                    self.MAP = int(row[i])
                except ValueError:
                    pass
            elif header[i] == 'IAT':
                try:
                    self.IAT = int(row[i])
                except ValueError:
                    pass
            elif header[i] == 'RPM':
                try:
                    self.RPM = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'DISTANCE':
                try:
                    self.distance = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'FUEL_USED':
                try:
                    self.fuel_used = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'FUEL_CONSUMPTION':
                try:
                    self.fuel_consumption = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'INSTANT_FUEL_CONSUMPTION':
                try:
                    self.instant_fuel_consumption = float(row[i])
                except ValueError:
                    pass
            elif header[i] == 'LATEST':
                try:
                    self.latest = int(row[i])
                except ValueError:
                    pass

    def get_csv_row(self, header):
        row = []
        for i in range(len(header)):
            if header[i] == 'LATITUDE':
                row.append(self.latitude)
            elif header[i] == 'LONGITUDE':
                row.append(self.longitude)
            elif header[i] == 'ALTITUDE':
                row.append(self.altitude)
            elif header[i] == 'HEADING':
                row.append(self.heading)
            elif header[i] == 'SPEED':
                row.append(self.speed)
            elif header[i] == 'SPEED_GPS':
                row.append(self.speed_gps)
            elif header[i] == 'TIME_GPS':
                row.append(self.time_gps)
            elif header[i] == 'X':
                row.append(self.x)
            elif header[i] == 'Y':
                row.append(self.y)
            elif header[i] == 'Z':
                row.append(self.z)
            elif header[i] == 'AAP':
                row.append(self.AAP)
            elif header[i] == 'AAT':
                row.append(self.AAT)
            elif header[i] == 'LOAD':
                row.append(self.load)
            elif header[i] == 'MAP':
                row.append(self.MAP)
            elif header[i] == 'IAT':
                row.append(self.IAT)
            elif header[i] == 'RPM':
                row.append(self.RPM)
            elif header[i] == 'DISTANCE':
                row.append(self.distance)
            elif header[i] == 'FUEL_USED':
                row.append(self.fuel_used)
            elif header[i] == 'FUEL_CONSUMPTION':
                row.append(self.fuel_consumption)
            elif header[i] == 'INSTANT_FUEL_CONSUMPTION':
                row.append(self.instant_fuel_consumption)
            elif header[i] == 'LATEST':
                row.append(self.latest)
        return row

    def is_sanitary(self, altitude=False, latitude=True, longitude=True, heading=False, speed=True, speed_gps=False,
                    time_gps=False, x=True, y=True, z=True, AAP=False, AAT=False, MAP=True, IAT=True, RPM=True,
                    load=True, instant_fuel_consumption=False, fuel_consumption=False, speed_threshold=0):
        if self.latest is None:
            return False
        if self.distance is None or self.distance < 0.0001:
            return False
        if speed and (self.speed <= speed_threshold or self.speed is None):
            return False
        if load and (self.load == 0 or self.load is None):
            return False
        if MAP and self.MAP is None:
            return False
        if IAT and self.IAT is None:
            return False
        if RPM and (self.RPM is None or self.RPM == 0):
            return False
        if fuel_consumption and (self.fuel_consumption is None or self.fuel_consumption == 0):
            return False
        if instant_fuel_consumption and self.instant_fuel_consumption is None:
            return False
        if latitude and (self.latitude is None or self.latitude == 0):
            return False
        if longitude and (self.longitude is None or self.longitude == 0):
            return False
        if altitude and (self.altitude is None or self.altitude == 0):
            return False
        if heading and self.heading is None:
            return False
        if speed_gps and self.speed_gps is None:
            return False
        if time_gps and self.time_gps is None:
            return False
        if x and self.x is None:
            return False
        if y and self.y is None:
            return False
        if z and self.z is None:
            return False
        if AAP and (self.AAP is None or self.AAP == 0):
            return False
        if AAT and (self.AAT is None or self.AAT < -50):
            return False
        if self.fuel_used is None or self.fuel_used == 0:
            return False
        return True


# Loads AutomotiveDataRows from csv
def load_csv(file):
    csv_file = open(file, 'r')
    csv_reader = csv.reader(csv_file, delimiter=',')
    header = next(csv_reader)
    print(header)
    automotive_data = []
    for row in csv_reader:
        adr = AutomotiveDataRow(header, row)
        if adr.is_sanitary(speed_threshold=10):
            automotive_data.append(adr)
    return automotive_data, header

# Writes AutomotiveDataRows to csv
def write_to_csv(automotive_data, header, file):
    csv_file = open(file, 'w', newline='')
    csv_writer = csv.writer(csv_file, delimiter=',')
    csv_writer.writerow(header)
    for adr in automotive_data:
        row = adr.get_csv_row(header)
        csv_writer.writerow(row)
