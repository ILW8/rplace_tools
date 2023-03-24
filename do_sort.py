import csv
import time

from tqdm import tqdm


def main():
    with open("./data/tile_placements_sorted.csv", "r") as infile:
        data = list()
        csv_reader = csv.reader(infile)
        for line in tqdm(csv_reader):
            data.append((line[0], line[2], line[3], line[4]))
    print("loaded data")
    print(len(data))
    sort_start = time.perf_counter()
    data = sorted(data, key=lambda x: x[0])[:-1]  # remove header row
    print(f"sorted data, took {time.perf_counter() - sort_start:.3f}s")

    write_start = time.perf_counter()
    with open("./data/tile_placements_sorted_ts.csv", "w") as outfile:
        csv_writer = csv.writer(outfile)
        for line in tqdm(data):
            csv_writer.writerow(line)
    print(f"written sorted data, took {time.perf_counter() - write_start:.3f}s")


if __name__ == "__main__":
    main()
