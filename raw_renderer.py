import datetime
import json
import subprocess

import numpy as np
import csv

from tqdm import tqdm, trange

CANVAS_WIDTH = 1000
CANVAS_HEIGHT = CANVAS_WIDTH
CANVAS_WIDTH_2022 = 2000
CANVAS_HEIGHT_2022 = CANVAS_WIDTH_2022
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

COLORS2022 = {'000000': (0, 0, 0), '00756F': (0, 117, 111), '009EAA': (0, 158, 170),
              '00A368': (0, 163, 104), '00CC78': (0, 204, 120), '00CCC0': (0, 204, 192),
              '2450A4': (36, 80, 164), '3690EA': (54, 144, 234), '493AC1': (73, 58, 193),
              '515252': (81, 82, 82), '51E9F4': (81, 233, 244), '6A5CFF': (106, 92, 255),
              '6D001A': (109, 0, 26), '6D482F': (109, 72, 47), '7EED56': (126, 237, 86),
              '811E9F': (129, 30, 159), '898D90': (137, 141, 144), '94B3FF': (148, 179, 255),
              '9C6926': (156, 105, 38), 'B44AC0': (180, 74, 192), 'BE0039': (190, 0, 57),
              'D4D7D9': (212, 215, 217), 'DE107F': (222, 16, 127), 'E4ABFF': (228, 171, 255),
              'FF3881': (255, 56, 129), 'FF4500': (255, 69, 0), 'FF99AA': (255, 153, 170),
              'FFA800': (255, 168, 0), 'FFB470': (255, 180, 112), 'FFD635': (255, 214, 53),
              'FFF8B8': (255, 248, 184), 'FFFFFF': (255, 255, 255)}

# from line_profiler_pycharm import profile
#
#
# @profile
def main2022():
    name_prefix = str(datetime.datetime.now().timestamp())
    ffmpeg_common_opts = ["ffmpeg",
                          "-f", "rawvideo",
                          "-vcodec", "rawvideo",
                          "-s", "1000x1000",
                          "-pix_fmt", "rgb24",
                          "-r", "120",
                          "-i", "-",
                          "-pix_fmt", "yuv420p",
                          "-vf", "scale=2000:2000:flags=neighbor",
                          "-an",
                          "-c:v", "hevc_videotoolbox",  # mac-specific. use libx264 otherwise
                          "-q:v", "90",  # specific to videotoolbox, use -crf 15 with libx264
                          ]
    ffmpeg_procs = []
    for quadrant in range(4):
        options = ffmpeg_common_opts.copy()
        options.append(f"/Volumes/tiny_m2/rplace_video_btmc/{name_prefix}_{quadrant}.mp4")
        ffmpeg_proc = subprocess.Popen(options,
                                       stdin=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL)
        ffmpeg_procs.append(ffmpeg_proc)

    frame_data = np.full((CANVAS_WIDTH_2022, CANVAS_WIDTH_2022, 3), 255, dtype=np.uint8)

    with open("/Volumes/tiny_m2/rplace_video_btmc/data/sorted_canvas.csv", "r") as infile:
        infile.readline()  # skip header
        csv_reader = csv.reader(infile)
        # data = list()
        last_hit = -1

        for row in tqdm(csv_reader, total=160353104):
            # row[2]: color, row[3]: coords, row[0]: time string
            if len(row[0]) >= 20:
                parsed_time = datetime.datetime.strptime(row[0], r"%Y-%m-%d %H:%M:%S.%f")
            else:
                parsed_time = datetime.datetime.strptime(row[0], r"%Y-%m-%d %H:%M:%S")
            timestamp = parsed_time.timestamp()
            coords = tuple(map(lambda x: x.strip("()"), row[3].split(",")))
            if len(coords) == 2:
                frame_data[int(coords[1]),
                           int(coords[0])] = COLORS2022[row[2]]
            else:
                frame_data[int(coords[1]):int(coords[3])+1,
                           int(coords[0]):int(coords[2])+1] = COLORS2022[row[2]]

            # for hit_index, data in tqdm(enumerate(data), total=16559897):
            #     ts, x, y, color_index = data
            #     frame_data[y][x] = COLORS[color_index]
            if timestamp - last_hit > 5.:
                last_hit = timestamp
                ffmpeg_procs[0].stdin.write(frame_data[:1000, :1000, :].tobytes())  # top left
                ffmpeg_procs[1].stdin.write(frame_data[1000:2000, :1000, :].tobytes())  # bottom left
                ffmpeg_procs[2].stdin.write(frame_data[:1000, 1000:2000, :].tobytes())  # top right
                ffmpeg_procs[3].stdin.write(frame_data[1000:2000, 1000:2000, :].tobytes())  # bottom right
    for ffmpeg_proc in ffmpeg_procs:
        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait()


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
                                    "-c:v", "hevc_videotoolbox",  # mac-specific. use libx264 otherwise
                                    "-q:v", "90",  # specific to videotoolbox, use -crf 15 with libx264
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
    # __colors = ["#000000", "#00756F", "#009EAA", "#00A368",
    #             "#00CC78", "#00CCC0", "#2450A4", "#3690EA",
    #             "#493AC1", "#515252", "#51E9F4", "#6A5CFF",
    #             "#6D001A", "#6D482F", "#7EED56", "#811E9F",
    #             "#898D90", "#94B3FF", "#9C6926", "#B44AC0",
    #             "#BE0039", "#D4D7D9", "#DE107F", "#E4ABFF",
    #             "#FF3881", "#FF4500", "#FF99AA", "#FFA800",
    #             "#FFB470", "#FFD635", "#FFF8B8", "#FFFFFF"]
    # colors = {}
    # for color in __colors:
    #     colors[color] = (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))
    # print(colors)

    # main()
    main2022()
