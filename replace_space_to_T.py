import csv

from tqdm import tqdm


if __name__ == "__main__":
    # with open("/Volumes/tiny_m2/rplace_video_btmc/data/sorted_canvas.csv", "r") as infile, \
    #      open("/Volumes/tiny_m2/rplace_video_btmc/data/sorted_canvas_t.csv", "w") as outfile:
    #     outfile.write(infile.readline())
    #     for row in tqdm(infile):
    #         row = row[:10] + "T" + row[11:]
    #         outfile.write(row)

    with open("/Volumes/tiny_m2/rplace_video_btmc/data/sorted_canvas.csv", "r") as infile, \
         open("/Volumes/tiny_m2/rplace_video_btmc/data/sorted_canvas_t____.csv", "w") as outfile:
        csv_reader = csv.reader(infile)
        csv_writer = csv.writer(outfile)

        for row in tqdm(csv_reader, total=160353104):
            row[0] = row[0][:10] + "T" + row[0][11:]
            row[3] = row[3].strip("()")
            csv_writer.writerow(row)
