import datetime
import json
import subprocess

import numpy as np
import csv

from tqdm import tqdm, trange

CANVAS_WIDTH = 1000
CANVAS_HEIGHT = CANVAS_WIDTH
COLORS = [(255, 255, 255),  # "#FFFFFF",
          (228, 228, 228),  # "#E4E4E4",
          (136, 136, 136),  # "#888888",
          (34, 34, 34),  # "#222222",
          (255, 167, 209),  # "#FFA7D1",
          (229, 000, 000),  # "#E50000",
          (229, 149, 000),  # "#E59500",
          (160, 106, 6_6),  # "#A06A42",
          (229, 217, 000),  # "#E5D900",
          (148, 224, 6_8),  # "#94E044",
          (2, 190, 1),  # "#02BE01",
          (000, 211, 221),  # "#00D3DD",
          (000, 131, 199),  # "#0083C7",
          (000, 000, 234),  # "#0000EA",
          (207, 110, 228),  # "#CF6EE4",
          (130, 000, 128),  # "#820080"
          ]


def main():
    with open("data/tile_placements_sorted_ts.csv", "r") as infile:
        csv_reader = csv.reader(infile)
        data = list()
        for row in tqdm(csv_reader, total=16559897):
            x = int(row[1])
            if x > 999:
                x = 999
            y = int(row[2])
            if y > 999:
                y = 999
            data.append((int(row[0]), x, y, int(row[3])))
    with open("./data/2017_timestamps.json", "r") as json_in:
        timestamps = json.load(json_in)
        new_timestamps = dict()
        for key in timestamps:
            new_timestamps[int(key)] = timestamps[key]
        timestamps = new_timestamps
        del new_timestamps

    ffmpeg_proc = subprocess.Popen(["ffmpeg",
                                    "-f", "rawvideo",
                                    "-vcodec", "rawvideo",
                                    "-s", "1000x1000",
                                    "-pix_fmt", "rgb24",
                                    "-r", "120",
                                    "-i", "-",
                                    "-pix_fmt", "yuv420p",
                                    "-vf", "scale=2000:2000:flags=neighbor",
                                    "-an",
                                    "-c:v", "hevc_videotoolbox",
                                    "-q:v", "90",
                                    f"{datetime.datetime.now().timestamp()}.mp4"],
                                   stdin=subprocess.PIPE, stderr=None, stdout=subprocess.DEVNULL)

    frame_data = np.full((CANVAS_WIDTH, CANVAS_HEIGHT, 3), 255, dtype=np.uint8)

    last_hit = -1
    for hit_index, data in tqdm(enumerate(data), total=16559897):
        ts, x, y, color_index = data
        frame_data[y][x] = COLORS[color_index]
        if hit_index in timestamps and timestamps[hit_index] - last_hit > 10_000:
            last_hit = timestamps[hit_index]
            ffmpeg_proc.stdin.write(frame_data.tobytes())
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()


if __name__ == "__main__":
    main()
