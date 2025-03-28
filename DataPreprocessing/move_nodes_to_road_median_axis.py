import math

import requests
import xml.etree.ElementTree as ET

from DataPreprocessing.Model.AutomotiveDataRow import load_csv, write_to_csv

INPUT_FILE = '/Users/antoniuficard/Documents/OBDlogs/Data/Prezentare/test15_05_2024_1.csv'
OUTPUT_FILE = '/Users/antoniuficard/Documents/OBDlogs/Data/Prezentare/snap_test15_05_2024_1.csv'

overpass_url = "http://overpass-api.de/api/interpreter"


# checks if an element has the highway tag
def is_highway(element):
    for i in element:
        try:
            if i.tag == 'tag' and i.attrib['k'] == 'highway' and i.attrib['v'] != 'proposed':
                return True
        except:
            pass

    return False


# gets the ways in the vicinity of a coordinate set on a given radius, if the ways are highways
# if no ways were found, it recursively retries with a radius greater by 2 units and the process repeats until a way is found
def get_way(request_latitude, request_longitude, request_radius=10):
    global overpass_url
    overpass_query = f"""
    [out:xml];
    (
      way(around:{request_radius},{request_latitude},{request_longitude});
    );
    out geom;
    """
    response = requests.post(overpass_url, data=overpass_query)
    response.raise_for_status()  # Check for HTTP errors

    # Get the XML response
    xml_data = response.text
    tree = ET.ElementTree(ET.fromstring(xml_data))
    root = tree.getroot()

    way = []
    for i in root:
        if i.tag == 'way' and is_highway(i):
            way.append(i)

    if len(way) >= 1:
        return way

    again = get_way(request_latitude, request_longitude, (request_radius + 2))

    return again


# returns the euclidian distance for a pair of coordinates
def euclidian_distance(x1, y1, x2, y2):
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


# It takes the coordinates of a point and a segment and finds the orthogonal projection.
# The function computes the point's projection on the segment and returns if the projection is on the segment, raises ValueError otherwise
# input: x - float - x coordinate of the point to find the projection of
#        y - float - y coordinate of the point to find the projection of
#        xa - float - x coordinate of one of the segments ends
#        ya - float - y coordinate of one of the segments ends
#        xb - float - x coordinate of the other segment end
#        yb - float - y coordinate of the other segment end
# returns: xh, yh, dist
#        xh - float - x coordinate of the projection
#        yh - float - y coordinate of the projection
#        dist - float - distance to projection
# raises: ValueError - no orthogonal projection can be found on the segment.
def find_projection_on_segment(x, y, xa, ya, xb, yb):
    a = ya - yb
    b = xb - xa
    c = xa * yb - xb * ya

    if a == 0 and b == 0:
        return xa, ya, euclidian_distance(xa, ya, x, y)

    d_pr = abs(a * x + b * y + c) / math.sqrt(a * a + b * b)

    xh = (b * (b * x - a * y) - a * c) / (a * a + b * b)
    yh = (a * (a * y - b * x) - b * c) / (a * a + b * b)

    if xa > xb:
        aux = xa
        xa = xb
        xb = aux

    if ya > yb:
        aux = ya
        ya = yb
        yb = aux

    if xh < xa - float('6e-6') or xh > xb + float('6e-6') or yh < ya - float('6e-6') or yh > yb + float('6e-6'):
        raise ValueError

    return xh, yh, d_pr


# Gets the number of lanes on half of the road (one side of the median axis)
def get_lanes(w):
    for i in w:
        if i.tag == 'tag' and i.attrib['k'] == 'lanes':
            return int(i.attrib['v']) / 2
    return 1


# Sees if a point is on a way. Checks each segment that composes the way and gets the projection to that segment if the distance
#   is less than the amount of lanes and a set threshold. The threshold distance is greater if the force parameter is true.
# input: x - x coordinate of the point
#        y - y coordinate of the point
#        way - way given by the api
#        force - boolean - defaults to False. Attempts to use a greater distance from the median axis of the road
# returns: all projections on all eligible segments in the way
def point_in_way(x, y, way, force=False):
    if way is None:
        return []

    xa = math.inf
    ya = math.inf
    xb = math.inf
    yb = math.inf

    result = []

    for w in way:
        for i in range(len(w) - 1):
            if w[i].tag == 'nd' and w[i + 1].tag == 'nd':
                xa = float(w[i].attrib['lat'])
                ya = float(w[i].attrib['lon'])
                xb = float(w[i + 1].attrib['lat'])
                yb = float(w[i + 1].attrib['lon'])

                try:
                    xd, yd, dist = find_projection_on_segment(x, y, xa, ya, xb, yb)
                    if not force and dist > get_lanes(w) * float('369e-7') + float('28e-6'):
                        continue
                    if dist > get_lanes(w) * float('369e-7') + float('738e-7'):
                        continue
                    result.append([w, xd, yd, dist])
                except ValueError:
                    continue

    if len(result) != 0:
        return result
    return []


# Gets the properties of a way.
def get_road_attributes(w1):
    surface1 = None
    highway1 = None
    ref1 = None
    name1 = None

    for w in w1:
        if w.tag == 'tag' and w.attrib['k'] == 'surface':
            surface1 = w.attrib['v']
        elif w.tag == 'tag' and w.attrib['k'] == 'highway':
            highway1 = w.attrib['v']
        elif w.tag == 'tag' and w.attrib['k'] == 'ref':
            ref1 = w.attrib['v']
        elif w.tag == 'tag' and w.attrib['k'] == 'name':
            name1 = w.attrib['v']

    return ref1, name1, highway1, surface1


# Computes the similarity grade for 2 ways. If the name or ref is identical the output is 1, otherwise, floating point
#   values are assigned depending on what parameter match.
# input: w1 - way
#        w2 - way
# returns: float - 1 if ways are identical - same name or ref
#                - 0.6 if the highway type is the same i.e. both are secondary highways
#                - 0.3 if the surface type matches
def way_similarity_grade(w1, w2):
    if w1 is None or w2 is None:
        return 0
    if w1.attrib['id'] == w2.attrib['id']:
        return 1

    ref1, name1, highway1, surface1 = get_road_attributes(w1)
    ref2, name2, highway2, surface2 = get_road_attributes(w2)

    if ref1 == ref2 and ref1 is not None and highway1 == highway2 and highway1 is not None:
        return 1

    if name1 == name2 and name1 is not None and highway1 == highway2 and highway1 is not None:
        return 1

    if highway1 == highway2 and highway1 is not None:
        return 0.6

    if surface1 == surface2 and surface1 is not None:
        return 0.3

    return 0


# Gets an array of AutomotiveDataRow and attempts to find all eligible projections on all ways for each set of coordinates.
# Returns an array and for each corresponding AutomotiveDataRow there is an array that contains all projections, the way it
#   it is projected on, the coordinates and distance of the projection.
def load_from_osm(automotive_data):
    way = None
    i = 0

    snapped_points = []

    for adr in automotive_data:
        i += 1
        if i % 50 == 0:
            print(i)

        snapped = point_in_way(adr.latitude, adr.longitude, way)
        if way is None or len(snapped) == 0:
            way = get_way(adr.latitude, adr.longitude)
        else:
            snapped_points.append(snapped)
            continue

        snapped = point_in_way(adr.latitude, adr.longitude, way, force=True)

        snapped_points.append(snapped)

        if way is None or len(snapped) == 0:
            print('way is null for i:', i, adr.latitude, adr.longitude)

    for i in range(len(automotive_data)):
        snapped = snapped_points[i]
        snapped = sorted(snapped, key=lambda p: p[3])
        snapped_points[i] = snapped

    return snapped_points


# Tries to move each point to the best projection. Looks at points ahead and behind to find ways with better similarity grades.
# input: automotive_data - AutomotiveDataRow array
#        snapped_points - result of load_data_osm()
#        correction_range - the amount of point to look ahead and behind at. defaults to 36, because on average 6 gps readings give
#                           the same coordinates. The computer reads from OBD2 at 6hz and GPS at 1Hz.
#        similarity_threshold - defaults at 0.3 - the minimum similarity for a point to be considered. if no points are found with the
#                                                 minimum similarity, then it takes the closest point. If no points are in range, then
#                                                 it does not move the point.
def snap_points_to_nearest_nodes(automotive_data, snapped_points, correction_range=36, similarity_threshold=0.3):
    for i in range(len(automotive_data)):
        snapped = snapped_points[i]

        if len(snapped) == 0:
            continue

        if i < correction_range or i > len(automotive_data) - 1 - correction_range and len(snapped) >= 1:
            automotive_data[i].latitude = snapped[0][1]
            automotive_data[i].longitude = snapped[0][2]
            continue

        after_5 = snapped_points[i + correction_range]
        before_5 = snapped_points[i - correction_range]

        found = False
        best_similarity = 0
        best_similarity_way = None
        for s in snapped:
            try:
                similarity = way_similarity_grade(before_5[0][0], after_5[0][0]) * way_similarity_grade(after_5[0][0], s[0])
                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_similarity_way = s
                    found = True
                    break
            except IndexError:
                pass

        if found:
            automotive_data[i].latitude = best_similarity_way[1]
            automotive_data[i].longitude = best_similarity_way[2]

        if not found:
            automotive_data[i].latitude = snapped[0][1]
            automotive_data[i].longitude = snapped[0][2]


def process_data():
    # loads data from file
    automotive_data, header = load_csv(INPUT_FILE)

    new_ad = [automotive_data[0]]

    # converts sequences of points when the car was stationary - no distance increase - to a single row.
    for i in range(1, len(automotive_data)):
        if automotive_data[i].distance == automotive_data[i - 1].distance:
            continue
        new_ad.append(automotive_data[i])
    automotive_data = new_ad
    new_ad = None

    print("Size of sanitised data:", len(automotive_data))

    # loads ways that are in range
    points = load_from_osm(automotive_data)

    # attempts to move the points
    snap_points_to_nearest_nodes(automotive_data, points)

    # writes the data to the csv
    write_to_csv(automotive_data, header, OUTPUT_FILE)


if __name__ == '__main__':
    process_data()
