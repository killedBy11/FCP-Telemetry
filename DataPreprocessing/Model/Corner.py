import math

import numpy

from DataPreprocessing.Model.Node import Node


# Corner and Node classes that keep the properties calculated.
# Node class should not be used outside of this file.
class Corner:
    _nodes = None
    _radiuses = None
    _direction = None
    _max_radius = None
    _min_radius = None
    _median_radius = None
    _avg_radius = None
    _max_speed = None
    _min_speed = None
    _median_speed = None
    _avg_speed = None
    _acceleration_decelerations = None
    _max_acceleration = None
    _max_deceleration = None
    _centrifugals = None
    _max_centrifugal = None
    _median_centrifugal = None
    _avg_centrifugal = None
    _fuel_used = None
    _distance_traveled = None
    _rise_run = None
    _max_rise = None
    _min_rise = None
    _avg_rise = None
    _median_rise = None
    _min_map = None
    _max_map = None
    _avg_map = None
    _median_map = None
    _min_load = None
    _max_load = None
    _avg_load = None
    _median_load = None

    def __init__(self, nodes, direction, radiuses):
        assert (len(nodes) == len(radiuses) + 1)
        self._nodes = nodes
        self._direction = direction
        self._radiuses = radiuses
        self._compute_all()

    def _compute_radius_properties(self):
        if len(self._radiuses) == 0:
            return

        sum = 0
        cnt = 0
        self._min_radius = math.inf
        self._max_radius = 0
        not_none = []
        for r in self._radiuses:
            if r is None:
                continue
            cnt += 1
            sum += r
            not_none.append(r)
            if r > self._max_radius:
                self._max_radius = r
            if r < self._min_radius:
                self._min_radius = r

        if cnt == 0:
            return

        self._avg_radius = sum / cnt
        self._median_radius = numpy.median(not_none)
        if self._direction == 'straight':
            self._avg_radius = self._median_radius = 1

    def _compute_speed_properties(self):
        if len(self._nodes) == 0:
            return

        sum = 0
        cnt = 0
        self._min_speed = math.inf
        self._max_speed = 0
        speeds = []
        for sp in self._nodes[:len(self._nodes) - 1]:
            for s in sp.speeds:
                sum += s
                cnt += 1
                if s > self._max_speed:
                    self._max_speed = s
                if s < self.min_speed:
                    self._min_speed = s
                speeds.append(s)

        if cnt == 0:
            return

        self._avg_speed = sum / cnt
        self._median_speed = numpy.median(speeds)

    def _compute_fuel_distance(self):
        self._fuel_used = self._nodes[-1].min_fuel_used - self._nodes[0].min_fuel_used
        self._distance_traveled = self._nodes[-1].min_distance - self._nodes[0].min_distance

    def _compute_maps_and_loads(self):
        maps = []
        loads = []

        for n in self._nodes[:len(self._nodes) - 1]:
            maps = maps + n.maps
            loads = loads + n.calc_loads

        self._min_map = min(maps)
        self._max_map = max(maps)
        self._avg_map = numpy.mean(maps)
        self._median_map = numpy.median(maps)
        self._min_load = min(loads)
        self._max_load = max(loads)
        self._avg_load = numpy.mean(loads)
        self._median_load = numpy.median(loads)

    def _compute_rise_run(self):
        if len(self._nodes) <= 1:
            return

        self._rise_run = []

        altitudes = []

        for r in self._nodes:
            if r.altitude is not None:
                altitudes.append(r)

        if len(altitudes) <= 1:
            return

        for i in range(len(altitudes) - 1):
            node1 = altitudes[i]
            node2 = altitudes[i + 1]
            run = node2.min_distance - node1.min_distance
            rise = node2.altitude - node1.altitude
            self._rise_run.append(rise / run)

        self._max_rise = numpy.max(self._rise_run)
        self._min_rise = numpy.min(self._rise_run)
        self._avg_rise = numpy.mean(self._rise_run)
        self._median_rise = numpy.median(self._rise_run)

    def _compute_array_properties(self):
        Xs = []
        Ys = []

        for i in self._nodes:
            for j in i.Xs:
                Xs.append(abs(j))
            for j in i.Ys:
                Ys.append(j)

        self._acceleration_decelerations = Ys
        self._centrifugals = Xs

        self._max_centrifugal = max(self._centrifugals)
        self._median_centrifugal = numpy.median(self._centrifugals)
        self._avg_centrifugal = sum(self._centrifugals) / len(self._centrifugals)

        self._max_acceleration = max(self._acceleration_decelerations)
        self._max_deceleration = min(self._acceleration_decelerations)

    # computes properties for corner
    def _compute_all(self):
        self._compute_radius_properties()
        self._compute_fuel_distance()
        self._compute_maps_and_loads()
        self._compute_array_properties()
        self._compute_speed_properties()
        self._compute_rise_run()

    # encodes object to array for easier json parsing
    def to_array(self):
        nodes = []

        for i in self._nodes:
            nodes.append(i.to_array())

        return [nodes, self._radiuses, self._direction, self._max_radius, self._min_radius, self._avg_radius,
                self._median_radius, self._max_speed, self._min_speed, self._avg_speed, self._median_speed,
                self._acceleration_decelerations, self._max_acceleration, self._max_deceleration, self._centrifugals,
                self._max_centrifugal, self._median_centrifugal, self._avg_centrifugal, self._fuel_used,
                self._distance_traveled, self._rise_run, self._max_rise, self._min_rise, self._avg_rise, self._median_rise,
                self._min_map, self._max_map, self._avg_map, self._median_map, self._min_load, self._max_load, self._avg_load,
                self._median_load]

    # loads object from an array encoded with the to_array method for easier json parsing
    @classmethod
    def from_array(cls, array):
        nodes = array[0]
        ns = []

        for node in nodes:
            n = Node.from_array(node)
            ns.append(n)

        c = Corner(ns, '', array[1])

        c._direction = array[2]
        c._max_radius = array[3]
        c._min_radius = array[4]
        c._avg_radius = array[5]
        c._median_radius = array[6]
        c._max_speed = array[7]
        c._min_speed = array[8]
        c._avg_speed = array[9]
        c._median_speed = array[10]
        c._acceleration_decelerations = array[11]
        c._max_acceleration = array[12]
        c._max_deceleration = array[13]
        c._centrifugals = array[14]
        c._max_centrifugal = array[15]
        c._median_centrifugal = array[16]
        c._avg_centrifugal = array[17]
        c._fuel_used = array[18]
        c._distance_traveled = array[19]
        c._rise_run = array[20]
        c._max_rise = array[21]
        c._min_rise = array[22]
        c._avg_rise = array[23]
        c._median_rise = array[24]
        c._min_map = array[25]
        c._max_map = array[26]
        c._avg_map = array[27]
        c._median_map = array[28]
        c._min_load = array[29]
        c._max_load = array[30]
        c._avg_load = array[31]
        c._median_load = array[32]

        return c

    @property
    def entry_speed(self):
        return self._nodes[0].speeds[0]

    @property
    def exit_speed(self):
        return self._nodes[-1].speeds[0]

    @property
    def decelerated_speed(self):
        speed = 0
        prev_speed = self._nodes[0].speeds[0]
        for i in self._nodes:
            for j in i.speeds:
                if prev_speed > j:
                    speed += prev_speed - j
                prev_speed = j

        return speed

    @property
    def accelerated_speed(self):
        speed = 0
        prev_speed = self._nodes[0].speeds[0]
        for i in self._nodes[:len(self._nodes) - 1]:
            for j in i.speeds:
                if prev_speed < j:
                    speed += j - prev_speed
                prev_speed = j

        return speed

    @property
    def entry_map(self):
        return self._nodes[0].maps[0]

    @property
    def exit_map(self):
        return self._nodes[-1].maps[0]

    @property
    def entry_load(self):
        return self._nodes[0].loads[0]

    @property
    def exit_load(self):
        return self._nodes[-1].loads[0]

    @property
    def nodes(self):
        return self._nodes.copy()

    @property
    def radiuses(self):
        return self._radiuses.copy()

    @property
    def direction(self):
        return self._direction

    @property
    def max_radius(self):
        return self._max_radius

    @property
    def min_radius(self):
        return self._min_radius

    @property
    def avg_radius(self):
        return self._avg_radius

    @property
    def median_radius(self):
        return self._median_radius

    @property
    def max_speed(self):
        return self._max_speed

    @property
    def min_speed(self):
        return self._min_speed

    @property
    def avg_speed(self):
        return self._avg_speed

    @property
    def median_speed(self):
        return self._median_speed

    @property
    def acceleration_decelerations(self):
        return self._acceleration_decelerations

    @property
    def max_acceleration(self):
        return self._max_acceleration

    @property
    def max_deceleration(self):
        return self._max_deceleration

    @property
    def centrifugals(self):
        return self._centrifugals.copy()

    @property
    def max_centrifugal(self):
        return self._max_centrifugal

    @property
    def median_centrifugal(self):
        return self._median_centrifugal

    @property
    def avg_centrifugal(self):
        return self._avg_centrifugal

    @property
    def fuel_used(self):
        return self._fuel_used

    @property
    def distance_traveled(self):
        return self._distance_traveled

    @property
    def rise_run(self):
        return self._rise_run

    @property
    def max_rise(self):
        return self._max_rise

    @property
    def min_rise(self):
        return self._min_rise

    @property
    def avg_rise(self):
        return self._avg_rise

    @property
    def median_rise(self):
        return self._median_rise

    @property
    def min_map(self):
        return self._min_map

    @property
    def max_map(self):
        return self._max_map

    @property
    def avg_map(self):
        return self._avg_map

    @property
    def median_map(self):
        return self._median_map

    @property
    def min_load(self):
        return self._min_load

    @property
    def max_load(self):
        return self._max_load

    @property
    def avg_load(self):
        return self._avg_load

    @property
    def median_load(self):
        return self._median_load

