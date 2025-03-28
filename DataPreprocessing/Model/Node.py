import math


class Node:
    _latitude = None
    _longitude = None
    _Xs = None
    _Ys = None
    _Zs = None
    _max_fuel_used = None
    _max_distance = None
    _min_distance = None
    _min_fuel_used = None
    _altitude = None
    _speeds = None
    _maps = None
    _calc_loads = None

    def __init__(self, latitude, longitude, ad=None):
        self._latitude = latitude
        self._longitude = longitude
        self._Xs = []
        self._Ys = []
        self._Zs = []
        self._speeds = []
        self._maps = []
        self._calc_loads = []

        if ad is None:
            return

        self._max_distance = 0
        self._min_distance = math.inf
        self._max_fuel_used = 0
        self._min_fuel_used = math.inf
        for adr in ad:
            self._Xs.append(adr.x)
            self._Ys.append(adr.y)
            self._Zs.append(adr.z)
            self._max_fuel_used = max(self._max_fuel_used, adr.fuel_used)
            self._max_distance = max(self._max_distance, adr.distance)
            self._min_distance = min(self._min_distance, adr.distance)
            self._min_fuel_used = min(self._min_fuel_used, adr.fuel_used)
            self._altitude = adr.altitude
            self._speeds.append(adr.speed)
            self._maps.append(adr.MAP)
            self._calc_loads.append(adr.load)

    # encodes object to array for easier json parsing
    def to_array(self):
        return [self.latitude, self.longitude, self.Xs, self.Ys, self.Zs, self.max_fuel_used, self.max_distance,
                self.min_distance, self.min_fuel_used, self.altitude, self.speeds, self.maps, self.calc_loads]

    # returns object from array encoded with to_array
    @classmethod
    def from_array(cls, array):
        n = Node(array[0], array[1])
        n._Xs = array[2]
        n._Ys = array[3]
        n._Zs = array[4]
        n._max_fuel_used = array[5]
        n._max_distance = array[6]
        n._min_distance = array[7]
        n._min_fuel_used = array[8]
        n._altitude = array[9]
        n._speeds = array[10]
        n._maps = array[11]
        n._calc_loads = array[12]
        return n

    @property
    def latitude(self):
        return self._latitude

    @property
    def longitude(self):
        return self._longitude

    @property
    def Xs(self):
        return self._Xs.copy()

    @property
    def Ys(self):
        return self._Ys.copy()

    @property
    def Zs(self):
        return self._Zs.copy()

    @property
    def max_fuel_used(self):
        return self._max_fuel_used

    @property
    def max_distance(self):
        return self._max_distance

    @property
    def min_distance(self):
        return self._min_distance

    @property
    def min_fuel_used(self):
        return self._min_fuel_used

    @property
    def altitude(self):
        return self._altitude

    @property
    def speeds(self):
        return self._speeds.copy()

    @property
    def maps(self):
        return self._maps.copy()

    @property
    def calc_loads(self):
        return self._calc_loads.copy()
