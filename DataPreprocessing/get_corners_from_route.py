import math

import DataPreprocessing.Model.AutomotiveDataRow
import move_nodes_to_road_median_axis
import json

from DataPreprocessing.Model.Corner import Corner
from DataPreprocessing.Model.Node import Node

INPUT_FILE = '/Users/antoniuficard/Documents/OBDlogs/Data/Prezentare/snap_floresti_centura_retur2.csv'
OUTPUT_FILE = '/Users/antoniuficard/Documents/OBDlogs/Data/Prezentare/split_floresti_centura_retur2.json'


# determinant of the matrix given by the coordinates of 3 points
# |x1, y1, 1|
# |x2, y2, 1|
# |x3, y3, 1|
def determinant(x1, y1, x2, y2, x3, y3):
    return x1 * y2 + x2 * y3 + x3 * y1 - x3 * y2 - x1 * y3 - x2 * y1


# the radius of the circle that has the 3 points given as a parameter on its circumference
def get_radius(xa, ya, xb, yb, xc, yc):
    yo = ((xa - xc) * (xa * xa + ya * ya - xb * xb - yb * yb) - (xa - xb) * (xa * xa + ya * ya - xc * xc - yc * yc)) / (
            2 * ((ya - yb) * (xa - xc) - (ya - yc) * (xa - xb)))

    if xa != xb:
        xo = (xa * xa + ya * ya - xb * xb - yb * yb - 2 * yo * (ya - yb)) / (2 * (xa - xb))
    elif xa != xc:
        xo = (xa * xa + ya * ya - xc * xc - yc * yc - 2 * yo * (ya - yc)) / (2 * (xa - xc))
    else:
        raise ValueError

    return math.sqrt((xb - xo) * (xb - xo) + (yb - yo) * (yb - yo))

# interprets the sign of the determinant
def get_direction(det):
    if det == 0:
        return 'straight'
    if det > 0:
        return 'right'
    return 'left'

# converts the AutomotiveDataRow objects to Node
def get_nodes(automotive_data):
    data = []
    nodes = []
    for i in range(len(automotive_data) - 1):
        data.append(automotive_data[i])
        if automotive_data[i].latitude != automotive_data[i + 1].latitude or automotive_data[i].longitude != \
                automotive_data[i + 1].longitude:
            nodes.append(Node(automotive_data[i].latitude, automotive_data[i].longitude, data))
            data = []

    return nodes

# gets an array containing the determinants and radiuses determined by the sequence of points.
# it evaluates node[i - 1], node[i] and node[i + 1]
# if the points are collinear, the radius is set to None
# if the radius or determinant do not reach the minimum threshold, the points are considered collinear.
def get_determinants_and_radiuses(automotive_data, straight_radius_threshold=0.007, min_determinant_abs=float('1e-10')):
    determinants = []
    radiuses_all = []

    for i in range(len(automotive_data) - 2):
        row1 = automotive_data[i]
        row2 = automotive_data[i + 1]
        row3 = automotive_data[i + 2]

        if row1.latitude == row2.latitude and row1.longitude == row2.longitude or row3.latitude == row2.latitude and row3.longitude == row2.longitude or row1.latitude == row3.latitude and row1.longitude == row3.longitude:
            continue

        det = determinant(row1.latitude, row1.longitude, row2.latitude, row2.longitude, row3.latitude, row3.longitude)
        radius = None

        if det != 0:
            radius = get_radius(row1.latitude, row1.longitude, row2.latitude, row2.longitude, row3.latitude,
                                row3.longitude)

        if radius is not None and radius > straight_radius_threshold or abs(det) < min_determinant_abs:
            det = 0

        determinants.append(det)
        radiuses_all.append(radius)

    return determinants, radiuses_all

# gets an array of corners given the input nodes, determinants and and radiuses. For a sequence to be considered a
# straight section there must be at least succesive_0s_for_straight adjacent nodes.
def find_corners(input_nodes, determinants, radiuses_all, succesive_0s_for_straight=1):
    nodes = []
    radiuses = []

    corners = []
    straights = []

    successive_0s = 0

    # identify straights
    for i in range(len(input_nodes) - 2):
        det = determinants[i]

        if det == 0:
            successive_0s += 1
            nodes.append(input_nodes[i])
            radiuses.append(radiuses_all[i])
            continue

        if successive_0s >= succesive_0s_for_straight:
            for j in range(i - successive_0s, i):
                determinants[j] = None

            nodes.append(input_nodes[i])
            c = Corner(nodes, get_direction(0), radiuses)
            straights.append(c)

        nodes = []
        radiuses = []
        successive_0s = 0

    if successive_0s >= succesive_0s_for_straight:
        for j in range(len(input_nodes) - 2 - successive_0s, len(input_nodes) - 2):
            determinants[j] = None

        nodes.append(input_nodes[len(input_nodes) - 1])
        c = Corner(nodes, get_direction(0), radiuses)
        straights.append(c)

    # identify corners
    nodes = []
    radiuses = []
    prev_det = 0
    straight_counter = 0

    for i in range(len(input_nodes) - 2):
        det = determinants[i]
        radius = radiuses_all[i]

        # if there was a straight section and a corner begins
        if prev_det is None and det is not None:
            corners.append(straights[straight_counter])
            straight_counter += 1
            nodes = []
            radiuses = []
            prev_det = det

        # if there was a corner and a straight section begins, or if the direction of the nodes changes from left to right or viceversa
        if prev_det is not None and (det is None or det is not None and prev_det * det < 0):
            nodes.append(input_nodes[i])
            try:
                c = Corner(nodes, get_direction(prev_det), radiuses)

                corners.append(c)
            except ValueError:
                pass
            nodes = []
            radiuses = []
            prev_det = det

        nodes.append(input_nodes[i])
        radiuses.append(radius)

    if prev_det is None:
        corners.append(straights[straight_counter])
        straight_counter += 1

    if prev_det is not None:
        nodes.append(input_nodes[len(input_nodes) - 1])
        try:
            c = Corner(nodes, get_direction(prev_det), radiuses)
            corners.append(c)
        except ValueError:
            pass

    # checks for errors
    assert len(straights) == straight_counter

    # eliminates the first item because it is a false identification.
    return corners[1:]


if __name__ == '__main__':
    automotive_data, header = DataPreprocessing.Model.AutomotiveDataRow.load_csv(INPUT_FILE)

    automotive_data = get_nodes(automotive_data)

    determinants, radiuses = get_determinants_and_radiuses(automotive_data, straight_radius_threshold=0.006,
                                                           min_determinant_abs=float('2e-10'))
    corners = find_corners(automotive_data, determinants, radiuses, succesive_0s_for_straight=7)

    fuel_used = 0
    distance = 0
    for corner in corners:
        fuel_used += corner.fuel_used
        distance += corner.distance_traveled

    print("Fuel used:", fuel_used)
    print("Distance:", distance)

    arrayed_corners = []

    for corner in corners:
        arrayed_corners.append(corner.to_array())

    with open(OUTPUT_FILE, "w") as file:
        json.dump(arrayed_corners, file, indent=4)
