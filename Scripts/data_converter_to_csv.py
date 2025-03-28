import csv
from OBD2.OBDFrames import OBDFrame, nanoseconds_to_seconds

LINE_LENGTH = 26


# parse one line provided by the logging script to an instance of OBD_Frame
def parse_line(line):
    if len(line) != LINE_LENGTH:
        raise Exception("INVALID_LINE_LENGTH")
    pid = line[0:2]
    a = line[2:4]
    b = line[4:6]
    time = line[6:25]

    pid = int(pid, 16)
    a = int(a, 16)
    b = int(b, 16)
    time = int(time)

    return OBDFrame(pid, a, b, time)


# script configuratio
SOURCE = './fuel_monitoring_both_o2_map.log'
DESTINATION = './fuel_monitoring_both_o2_map.csv'
PIDS_AND_UNITS = [[0x0B, None], [0x0C, None], [0x14, 'V'], [0x14, '%'], [0x15, 'V'], [0x15, '%'], [0x03, None]]


# returns an array full of None for each PID
def reset_current_line():
    current_line = [None] * len(PIDS_AND_UNITS)
    return current_line


def convert():
    global SOURCE, DESTINATION
    # open the necessary files
    input_file = open(SOURCE, 'r')
    output_file = open(DESTINATION, 'w')
    line = input_file.readline()
    writer = csv.writer(output_file)

    # build the table head and write it
    csv_header = ["TIME"]

    for i in PIDS_AND_UNITS:
        csv_header.append(OBDFrame(pid=i[0]).get_message(unit=i[1]))

    writer.writerow(csv_header)

    # start with an empty line
    current_line = reset_current_line()

    while line != "":
        try:
            # get an OBD_Frame
            parameter = parse_line(line)

            # try to find its appropriate column and parse to an array
            for i in range(len(PIDS_AND_UNITS)):
                if parameter.pid == PIDS_AND_UNITS[i][0]:
                    current_line[i] = parameter.parse(unit=PIDS_AND_UNITS[i][1])

            # check if the line was filled
            no_nones = True
            for i in current_line:
                if i is None:
                    no_nones = False
                    break

            if no_nones:
                # if the line was filled, find the minimum time of the cells in the row
                mini = 1000000000000000000
                for i in current_line:
                    if i[2] < mini:
                        mini = i[2]
                # put the found time as the first column
                raw = [mini]
                # append the human-readable values to the row
                for i in current_line:
                    raw.append(i[1])
                # write and reset the current_line
                writer.writerow(raw)
                current_line = reset_current_line()
        except Exception:
            print("Invalid line!")
        finally:
            line = input_file.readline()

    input_file.close()
    output_file.close()


if __name__ == '__main__':
    convert()
