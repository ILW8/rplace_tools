import datetime
import json
import subprocess

import numpy as np
import csv

from tqdm import tqdm
import zstandard as zstd
import ciso8601
import random

import matplotlib.pyplot as plt

# from line_profiler_pycharm import profile


# from line_profiler_pycharm import profile


CANVAS_WIDTH_2022 = 1920
CANVAS_HEIGHT_2022 = 1080
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

COLORS2022KEYS = list(COLORS2022.keys())
COLORS2022KEYS_NONGREY = list(set(list(COLORS2022.keys())) - {"FFFFFF", "D4D7D9", "898D90"})
COLORS2022KEYS_NONWHITE_NORBLACK = list(set(list(COLORS2022.keys())) - {"FFFFFF", "000000"})

NAMES = [
    "DeadRote",
    "Prof. Impressor",
    "s1nqq",
    "n3rdiness",
    "placeholder",
    "even longer name here",
]
# letters are 5x7

VPIXW_PER_PIXEL = 8
TPIXW_PER_VPIX = 1  # text pixel width per video pixel
RENDER_OFFSET_X = 000
RENDER_OFFSET_Y = 400
REALTIME_SECONDS_PER_FRAME = 10.


class CreditsGenerator:
    def __init__(self, names, randomization_frames=480):
        self.canvas_width = int(CANVAS_WIDTH_2022 // VPIXW_PER_PIXEL)  # effective canvas width
        self.canvas_height = int(CANVAS_HEIGHT_2022 // VPIXW_PER_PIXEL)
        self.names = names
        self.randomization_duration = randomization_frames  # in frames
        self.randomization_start_offset = 60  # in frames

        self.hits = set()
        self.frame_data = np.full((self.canvas_height, self.canvas_width, 3), 255, dtype=np.uint8)

        self.is_showing_text = False
        self.showing_text_start = -1

        self.blacklist = np.zeros((self.canvas_height, self.canvas_width), dtype=bool)
        self.blacklist = np.zeros((self.canvas_height, self.canvas_width), dtype=bool)
        self.blacklist_argwhere = np.zeros((0, 2))
        self.letter_bitmap = {
            " ": np.array([[0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ]], dtype=bool),
            ",": np.array([[0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ],
                           [0, 0, 0, 0, 0, ],
                           [0, 1, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ]], dtype=bool),
            "A": np.array([[0, 1, 1, 1, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 1, 1, 1, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ]], dtype=bool),

            "B": np.array([[1, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 1, 1, 1, 0, ]], dtype=bool),

            "C": np.array([[0, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 1, 1, 0, ]], dtype=bool),

            "D": np.array([[1, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 1, 1, 1, 0, ]], dtype=bool),

            "E": np.array([[1, 1, 1, 1, 1, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 1, 1, 1, 1, ]], dtype=bool),

            "F": np.array([[1, 1, 1, 1, 1, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ]], dtype=bool),

            "G": np.array([[0, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 1, 1, 0, ]], dtype=bool),

            "H": np.array([[1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 1, 1, 1, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ]], dtype=bool),

            "I": np.array([[1, 1, 1, 1, 1, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [1, 1, 1, 1, 1, ]], dtype=bool),

            "J": np.array([[0, 0, 0, 1, 1, ],
                           [0, 0, 0, 0, 1, ],
                           [0, 0, 0, 0, 1, ],
                           [0, 0, 0, 0, 1, ],
                           [0, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 1, 1, 0, ]], dtype=bool),

            "K": np.array([[1, 0, 0, 0, 1, ],
                           [1, 0, 0, 1, 0, ],
                           [1, 0, 1, 0, 0, ],
                           [1, 1, 0, 0, 0, ],
                           [1, 0, 1, 0, 0, ],
                           [1, 0, 0, 1, 0, ],
                           [1, 0, 0, 0, 1, ]], dtype=bool),

            "L": np.array([[1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 1, 1, 1, 1, ]], dtype=bool),

            "M": np.array([[1, 0, 0, 0, 1, ],
                           [1, 1, 0, 1, 1, ],
                           [1, 0, 1, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ]], dtype=bool),

            "N": np.array([[1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 1, 0, 0, 1, ],
                           [1, 0, 1, 0, 1, ],
                           [1, 0, 0, 1, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ]], dtype=bool),

            "O": np.array([[0, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 1, 1, 0, ]], dtype=bool),

            "P": np.array([[1, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ]], dtype=bool),

            "Q": np.array([[0, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 1, 0, 1, ],
                           [1, 0, 0, 1, 0, ],
                           [0, 1, 1, 0, 1, ]], dtype=bool),

            "R": np.array([[1, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ]], dtype=bool),

            "S": np.array([[0, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 1, 1, 1, 0, ],
                           [0, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 1, 1, 0, ]], dtype=bool),

            "T": np.array([[1, 1, 1, 1, 1, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ]], dtype=bool),

            "U": np.array([[1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 1, 1, 0, ]], dtype=bool),

            "V": np.array([[1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 0, 1, 0, ],
                           [0, 0, 1, 0, 0, ]], dtype=bool),

            "W": np.array([[1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 1, 0, 1, ],
                           [1, 0, 1, 0, 1, ],
                           [0, 1, 0, 1, 0, ]], dtype=bool),

            "X": np.array([[1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 0, 1, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 1, 0, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ]], dtype=bool),

            "Y": np.array([[1, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 0, 1, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 0, 1, 0, 0, ]], dtype=bool),

            "Z": np.array([[1, 1, 1, 1, 1, ],
                           [0, 0, 0, 0, 1, ],
                           [0, 0, 0, 1, 0, ],
                           [0, 0, 1, 0, 0, ],
                           [0, 1, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 1, 1, 1, 1, ]], dtype=bool),

            # "A": np.array([[0, 1, 1, 1, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 1, 1, 1, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ]], dtype=bool),
            #
            # "B": np.array([[1, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 1, 1, 1, 0, ]], dtype=bool),
            #
            # "C": np.array([[0, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [0, 1, 1, 1, 0, ]], dtype=bool),
            #
            # "D": np.array([[1, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 1, 1, 1, 0, ]], dtype=bool),
            #
            # "E": np.array([[1, 1, 1, 1, 1, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 1, 1, 1, 1, ]], dtype=bool),
            #
            # "F": np.array([[1, 1, 1, 1, 1, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ]], dtype=bool),
            #
            # "G": np.array([[0, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [0, 1, 1, 1, 0, ]], dtype=bool),
            #
            # "H": np.array([[1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 1, 1, 1, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ]], dtype=bool),
            #
            # "I": np.array([[1, 1, 1, 1, 1, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [1, 1, 1, 1, 1, ]], dtype=bool),
            #
            # "J": np.array([[0, 10 0, 1, 1, ],
            #                [0, 0, 0, 0, 1, ],
            #                [0, 0, 0, 0, 1, ],
            #                [0, 0, 0, 0, 1, ],
            #                [0, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [0, 1, 1, 1, 0, ]], dtype=bool),
            #
            # "K": np.array([[1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 1, 0, ],
            #                [1, 0, 1, 0, 0, ],
            #                [1, 1, 0, 0, 0, ],
            #                [1, 0, 1, 0, 0, ],
            #                [1, 0, 0, 1, 0, ],
            #                [1, 0, 0, 0, 1, ]], dtype=bool),
            #
            # "L": np.array([[1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 1, 1, 1, 1, ]], dtype=bool),
            #
            # "M": np.array([[1, 0, 0, 0, 1, ],
            #                [1, 1, 0, 1, 1, ],
            #                [1, 0, 1, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ]], dtype=bool),
            #
            # "N": np.array([[1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 1, 0, 0, 1, ],
            #                [1, 0, 1, 0, 1, ],
            #                [1, 0, 0, 1, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ]], dtype=bool),
            #
            # "O": np.array([[0, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [0, 1, 1, 1, 0, ]], dtype=bool),
            #
            # "P": np.array([[1, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 0, 0, 0, 0, ]], dtype=bool),
            #
            # "Q": np.array([[0, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 1, 0, 1, ],
            #                [1, 0, 0, 1, 0, ],
            #                [0, 1, 1, 0, 1, ]], dtype=bool),
            #
            # "R": np.array([[1, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ]], dtype=bool),
            #
            # "S": np.array([[0, 1, 1, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 0, ],
            #                [1, 1, 1, 1, 0, ],
            #                [0, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [0, 1, 1, 1, 0, ]], dtype=bool),
            #
            # "T": np.array([[1, 1, 1, 1, 1, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ]], dtype=bool),
            #
            # "U": np.array([[1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [0, 1, 1, 1, 0, ]], dtype=bool),
            #
            # "V": np.array([[1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [0, 1, 0, 1, 0, ],
            #                [0, 0, 1, 0, 0, ]], dtype=bool),
            #
            # "W": np.array([[1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 1, 0, 1, ],
            #                [1, 0, 1, 0, 1, ],
            #                [0, 1, 0, 1, 0, ]], dtype=bool),
            #
            # "X": np.array([[1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [0, 1, 0, 1, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 1, 0, 1, 0, ],
            #                [1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ]], dtype=bool),
            #
            # "Y": np.array([[1, 0, 0, 0, 1, ],
            #                [1, 0, 0, 0, 1, ],
            #                [0, 1, 0, 1, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ],
            #                [0, 0, 1, 0, 0, ]], dtype=bool),

            "z": np.array([[0, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 0, 0, 1, 1, ],
                           [1, 0, 1, 0, 1, ],
                           [1, 1, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 1, 1, 0, ]], dtype=bool),

            "1": np.array([[0, 0, 0, 1, 0, ],
                           [0, 0, 1, 1, 0, ],
                           [0, 1, 0, 1, 0, ],
                           [0, 0, 0, 1, 0, ],
                           [0, 0, 0, 1, 0, ],
                           [0, 0, 0, 1, 0, ],
                           [0, 1, 1, 1, 1, ]], dtype=bool),

            "2": np.array([[0, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 0, 0, 0, 1, ],
                           [0, 0, 1, 1, 0, ],
                           [0, 1, 0, 0, 0, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 1, 1, 1, 1, ]], dtype=bool),

            "3": np.array([[0, 1, 1, 1, 0, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 0, 0, 0, 1, ],
                           [0, 0, 1, 1, 0, ],
                           [0, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 1, 1, 0, ]], dtype=bool),

            "4": np.array([[0, 0, 0, 1, 1, ],
                           [0, 0, 1, 0, 1, ],
                           [0, 1, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [1, 1, 1, 1, 1, ],
                           [0, 0, 0, 0, 1, ],
                           [0, 0, 0, 0, 1, ]], dtype=bool),

            "5": np.array([[1, 1, 1, 1, 1, ],
                           [1, 0, 0, 0, 0, ],
                           [1, 1, 1, 1, 0, ],
                           [0, 0, 0, 0, 1, ],
                           [0, 0, 0, 0, 1, ],
                           [1, 0, 0, 0, 1, ],
                           [0, 1, 1, 1, 0, ]], dtype=bool),

        }

        # offset of cropped_sorted.csv: 400x 500y
        # self.datafile = open("./cropped_sorted.csv", "r")

    # @staticmethod
    # def lookup_letter_bitmap(letter: str) -> list[tuple]:
    #     assert len(letter) == 1
    #     return [(0, 0)]

    def update_blacklist(self, line_1: str, line_2: str):
        canvas_width = self.canvas_width
        canvas_height = self.canvas_height

        self.blacklist = np.zeros((canvas_height, canvas_width), dtype=bool)

        for line, text in enumerate((line_1, line_2)):
            text_width = len(text) * (5 + 1) * TPIXW_PER_VPIX

            # center text:
            if text_width > canvas_width:
                raise ValueError(f"Text '{text}' will not fit in canvas (text width of {text_width} in canvas of "
                                 f"width {canvas_width})")
            left_margin = (canvas_width - text_width) // 2
            top_margin = (canvas_height // 2 +
                          (9 * TPIXW_PER_VPIX * (-1 if line == 0 else +1)))  # 4 pixels between lines

            current_x_pos = left_margin
            for letter in text:
                current_x_pos += 6 * TPIXW_PER_VPIX
                bitmap = self.letter_bitmap[letter.upper()]

                # self.blacklist[top_margin:top_margin + 7, current_x_pos:current_x_pos + 5] = bitmap
                for y, x in np.argwhere(bitmap):
                    # print(y, x)
                    self.blacklist[top_margin + y * TPIXW_PER_VPIX:top_margin + (y + 1) * TPIXW_PER_VPIX,
                                   current_x_pos + x * TPIXW_PER_VPIX:current_x_pos + (x + 1) * TPIXW_PER_VPIX] = True
        self.blacklist_argwhere = np.argwhere(self.blacklist)

    def __iter__(self):
        self.hit_num = 0
        self.current_frame = 0
        # self.last_flush = datetime.datetime.fromtimestamp(0)
        # self.last_flush = ciso8601.parse_datetime("2022-04-01T17:00:00.000")  # first pixel: 2022-04-01T12:44:10.315
        self.update_blacklist("DeadRote", "Project Mgmt,Script Writing,Research")
        return self

    # @profile
    def __next__(self):
        # # should_dispaly_credit = (self.current_frame + self.randomization_start_offset) >= self.randomization_duration
        # # if should_dispaly_credit:
        # #     if random.randint(0,
        # #                       max(10,
        # #                           (self.randomization_duration - (self.current_frame + self.randomization_start_offset)))
        # #                       ) == 0:
        # #         text_coords = self.blacklist_argwhere
        # #         hit_y, hit_x = text_coords[np.random.randint(text_coords.shape[0], size=1), :][0]
        # #         # return False, hit_x, hit_x, hit_y, hit_y, random.choice(("898D90", "D4D7D9", "FFFFFF"))
        # #         return False, hit_x, hit_x, hit_y, hit_y, "D4D7D9"
        #
        # self.hit_num += 1
        # should_flush = False
        # if self.hit_num % 2000 == 0:
        #     should_flush = True
        #     self.current_frame += 1
        #
        # hit_x = random.randint(0, self.canvas_width - 1)
        # hit_y = random.randint(0, self.canvas_height - 1)
        #
        # if self.current_frame - self.randomization_start_offset > 0:
        #     # while self.blacklist[hit_y, hit_x]:
        #     #     hit_x = random.randint(0, self.canvas_width - 1)
        #     #     hit_y = random.randint(0, self.canvas_height - 1)
        #     if self.blacklist[hit_y, hit_x]:
        #         return should_flush, hit_x, hit_x, hit_y, hit_y, "000000"
        #
        #     return should_flush, hit_x, hit_x, hit_y, hit_y, "FFFFFF"
        #
        # # if should_dispaly_credit and self.blacklist[hit_y, hit_x]:
        # #     # return should_flush, hit_x, hit_x2, hit_y, hit_y2, random.choice(("898D90", "D4D7D9", "FFFFFF"))
        # #     return True, hit_x, hit_x, hit_y, hit_y, "D4D7D9"
        # return should_flush, hit_x, hit_x, hit_y, hit_y, random.choice(COLORS2022KEYS_NONWHITE)
        while True:
            hit_x = random.randint(0, self.canvas_width - 1)
            hit_y = random.randint(0, self.canvas_height - 1)
            hit_coords = (hit_x, hit_y)
            if hit_coords in self.hits and not self.is_showing_text:
                if self.hit_num < self.canvas_height * self.canvas_width:
                    continue
                else:
                    self.is_showing_text = True
                    self.showing_text_start = self.current_frame

            if self.is_showing_text and self.current_frame - self.showing_text_start >= 16:
                if hit_coords not in self.hits:
                    if len(self.hits) == 0:
                        if self.current_frame - self.showing_text_start < 300:
                            self.current_frame += 1
                            return self.frame_data
                    continue

                self.hit_num -= 1
                self.hits.remove(hit_coords)
                if self.blacklist[hit_y, hit_x]:
                    self.frame_data[hit_y, hit_x] = COLORS2022["000000"]
                else:
                    self.frame_data[hit_y, hit_x] = COLORS2022["FFFFFF"]
            else:  # do the normal thing
                self.hits.add(hit_coords)
                self.hit_num += 1
                self.frame_data[hit_y, hit_x] = COLORS2022[random.choice(COLORS2022KEYS_NONWHITE_NORBLACK)]

            if self.hit_num % 512 == 0:
                self.current_frame += 1
                return self.frame_data


# @profile
def main2022_rawvideo():
    name_prefix = f"credits_{datetime.datetime.now().timestamp()}"
    canvas_width = int(CANVAS_WIDTH_2022 // VPIXW_PER_PIXEL)  # effective canvas width
    canvas_height = int(CANVAS_HEIGHT_2022 // VPIXW_PER_PIXEL)
    print(canvas_width, canvas_height)
    frame_data = np.full((canvas_height, canvas_width, 3), 255, dtype=np.uint8)
    # fd = open(f"/Volumes/stripe/rplace2022data/{name_prefix}.bin", "wb")
    # cctx = zstd.ZstdCompressor(level=1, threads=3)
    # compressor = cctx.stream_writer(fd)
    # bytes_written_compressed = 0
    credits_generator = CreditsGenerator(NAMES)

    pbar = tqdm(unit="frames")
    # credits_generator.update_blacklist("DeadRote", "Project Manager, Script Writing, Research")
    # print()
    # for aaa in credits_generator:
    #     if aaa[0]:
    #         print(aaa)

    ffmpeg_opts = ["ffmpeg",
                   "-f", "rawvideo",
                   "-vcodec", "rawvideo",
                   "-s", f"{canvas_width}x{canvas_height}",
                   "-pix_fmt", "rgb24",
                   "-r", "60",
                   "-i", "-",
                   "-pix_fmt", "yuv420p",
                   "-vf", f"scale={canvas_width * VPIXW_PER_PIXEL}:{canvas_height * VPIXW_PER_PIXEL}:flags=neighbor",
                   "-an",
                   "-c:v", "hevc_videotoolbox",  # mac-specific. use libx264 otherwise
                   "-q:v", "90",  # specific to videotoolbox, use -crf 15 with libx264
                   f"{name_prefix}.mp4"
                   ]
    ffmpeg_proc = subprocess.Popen(ffmpeg_opts,
                                   stdin=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL)

    # for should_flush_frame, hit_x, hit_x2, hit_y, hit_y2, hit_color in credits_generator:
    #     # todo: make use of VPIXW_PER_PIXEL
    #     # frame_data[hit_y * VPIXW_PER_PIXEL:(hit_y2+1) * VPIXW_PER_PIXEL,
    #     #            hit_x * VPIXW_PER_PIXEL:(hit_x2+1) * VPIXW_PER_PIXEL] = COLORS2022[hit_color]
    #
    #     # if hit_y2 <= canvas_height and hit_x2 <= canvas_width:
    #     #     if hit_x < 0 or hit_y < 0:
    #     #         if hit_x2 < 0:
    #     #             continue
    #     #         if hit_y2 < 0:
    #     #             continue
    #     #         hit_x = max(0, hit_x)
    #     #         hit_y = max(0, hit_y)
    #     #         hit_x2 = max(0, hit_x2)
    #     #         hit_y2 = max(0, hit_y2)
    #     #     frame_data[hit_y:hit_y2+1, hit_x:hit_x2+1] = COLORS2022[hit_color]
    #     frame_data[hit_y:hit_y2 + 1, hit_x:hit_x2 + 1] = COLORS2022[hit_color]
    #
    #     if should_flush_frame:
    #         ffmpeg_proc.stdin.write(frame_data.tobytes())
    #         pbar.update(1)
    for frame_data in credits_generator:
        ffmpeg_proc.stdin.write(frame_data.tobytes())
        pbar.update(1)
    ffmpeg_proc.stdin.flush()
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
    main2022_rawvideo()
