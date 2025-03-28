from DataPreprocessing.Model.Corner import Corner
from DataPreprocessing.Model.Node import Node
import json
import gpxpy.gpx
import xml.etree.ElementTree as ET


def load_corners(input_file):
    corners = []

    with open(input_file, 'r') as file:
        data = json.load(file)

    for corner in data:
        corners.append(Corner.from_array(corner))

    return corners


def export_to_gpx(corners, output_file):
    gpx = gpxpy.gpx.GPX()

    colors = ['#FF0000', '#00FF00', '#0000FF']
    color_index = 0
    for corner in corners:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        for node in corner.nodes:
            track_point = gpxpy.gpx.GPXTrackPoint(latitude=node.latitude, longitude=node.longitude)
            gpx_segment.points.append(track_point)

        gpx_track.segments.append(gpx_segment)
        color_element = ET.Element('color')
        color_element.text = colors[color_index]
        gpx_track.extensions.append(color_element)
        gpx_track.description = str(corner.direction) + '\n' + "fuel=" + str(corner.fuel_used) + ", distance=" + str(corner.distance_traveled)
        color_index = (color_index + 1) % len(colors)
        gpx.tracks.append(gpx_track)


    with open(output_file, 'w') as f:
        f.write(gpx.to_xml())


if __name__ == '__main__':
    corners = load_corners('/Users/antoniuficard/Documents/OBDlogs/Data/Prezentare/split_floresti_centura_retur2.json')
    export_to_gpx(corners, '/Users/antoniuficard/Documents/OBDlogs/Data/Prezentare/split_floresti_centura_retur2.gpx')

    print("Continue...")
    input("Press Enter to continue...")

    labels = []

    for i in range(len(corners)):
        print(i)
        print(corners[i].nodes[0].latitude, corners[i].nodes[0].longitude)
        print(corners[i].nodes[-1].latitude, corners[i].nodes[-1].longitude)
        print(corners[i].direction)
        label = input("Label:")
        labels.append(label)

    with open('labels.json', "w") as file:
        json.dump(labels, file, indent=4)

