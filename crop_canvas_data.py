import csv
from tqdm import tqdm

LEFT_X = 400
RIGHT_X = 900
TOP_Y = 500
BOTTOM_Y = 1000


def main():
    with open("/Volumes/tiny_m2/rplace_video_btmc/data/sorted_canvas_t.csv", "r") as infile, \
            open("cropped_bigger_sorted.csv", "w") as outfile:
        infile.readline()  # skip header
        csv_reader = csv.reader(infile)
        csv_writer = csv.writer(outfile)

        for row in tqdm(csv_reader, total=160353104):
            coords = row[3].split(",")
            y = int(coords[1])
            x = int(coords[0])

            if LEFT_X <= x <= RIGHT_X and TOP_Y <= y <= BOTTOM_Y:
                if len(coords) == 4:
                    x2 = max(min(RIGHT_X, int(coords[2])), LEFT_X)
                    y2 = max(min(BOTTOM_Y, int(coords[3])), TOP_Y)
                    row[3] = ",".join(list(map(str, (x, x2, y, y2))))
                csv_writer.writerow(row)


if __name__ == "__main__":
    main()
