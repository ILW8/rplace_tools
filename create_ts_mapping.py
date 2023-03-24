import csv
import time
import json

from tqdm import tqdm


def main():
    with open("./data/tile_placements_sorted_ts.csv", "r") as infile:
        data = dict()
        csv_reader = csv.reader(infile)
        last_ts = -1
        for row_index, line in tqdm(enumerate(csv_reader)):
            try:
                if int(line[0]) > last_ts:
                    last_ts = int(line[0])
                    data[row_index] = last_ts
            except ValueError:
                continue
    with open("./data/2017_timestamps.json", "w") as outfile:
        json.dump(data, outfile)


if __name__ == "__main__":
    main()
