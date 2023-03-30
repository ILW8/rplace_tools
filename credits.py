import datetime
import json
import subprocess

import numpy as np
import csv

from tqdm import tqdm
import zstandard as zstd
import ciso8601
import random
from raw_renderer import COLORS2022

import matplotlib.pyplot as plt

# from line_profiler_pycharm import profile


# from line_profiler_pycharm import profile


CANVAS_WIDTH_2022 = 1920
CANVAS_HEIGHT_2022 = 1080

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
        self.background_canvas = np.full((self.canvas_height, self.canvas_width, 3), 255, dtype=np.uint8)
        self.background_canvas_offset_x = -1
        self.background_canvas_offset_y = -1
        self.background_canvas_point_in_time = datetime.datetime.fromtimestamp(0)

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
        self.datafile = None
        self.csv_reader = None

    def load_background_canvas(self, x_offset, y_offset, point_in_time, open_new=True, update_live_canvas=False):
        if open_new:
            self.datafile = open("/Volumes/tiny_m2/rplace_video_btmc/data/sorted_canvas_t.csv", "r")
            self.datafile.readline()  # skip header
            self.csv_reader = csv.reader(self.datafile)
            self.background_canvas_offset_x = x_offset
            self.background_canvas_offset_y = y_offset
            self.background_canvas_point_in_time = point_in_time
        for i, row in enumerate(self.csv_reader):
            if i % 10_000 == 0:
                timestamp = ciso8601.parse_datetime(row[0])
                if timestamp > point_in_time:
                    return

            coords = row[3].split(",")

            if len(coords) == 4:
                hit_x, hit_x2, hit_y, hit_y2 = map(lambda x: int(x[0]) - x[1],
                                                   zip(coords, (x_offset, x_offset,
                                                                y_offset, y_offset)))
                self.background_canvas[hit_y, hit_x] = COLORS2022[row[2]]

            else:
                hit_x, hit_y = map(lambda x: int(x[0]) - x[1], zip(coords, (x_offset, y_offset)))
                hit_x2 = hit_x
                hit_y2 = hit_y

            if hit_y2 < self.canvas_height and hit_x2 < self.canvas_width:
                if hit_x < 0 or hit_y < 0:
                    if hit_x2 < 0:
                        continue
                    if hit_y2 < 0:
                        continue
                    hit_x = max(0, hit_x)
                    hit_y = max(0, hit_y)
                    hit_x2 = max(0, hit_x2)
                    hit_y2 = max(0, hit_y2)
            self.background_canvas[hit_y:hit_y2 + 1, hit_x:hit_x2 + 1] = COLORS2022[row[2]]
            if update_live_canvas:
                # if self.frame_data[hit_y:hit_y + 1, hit_x:hit_x + 1].sum() == 765:  # is (255, 255, 255)
                #     continue

                # only update if has been hit before
                if (hit_x, hit_y) in self.hits:
                    self.frame_data[hit_y:hit_y2 + 1, hit_x:hit_x2 + 1] = COLORS2022[row[2]]

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

            TRANSITION_TIME_FRAMES = 120
            if self.is_showing_text and self.current_frame - self.showing_text_start >= TRANSITION_TIME_FRAMES:
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
                self.frame_data[hit_y, hit_x] = self.background_canvas[hit_y, hit_x]

            if self.hit_num % 256 == 0:
                # if self.is_showing_text and self.current_frame - self.showing_text_start < TRANSITION_TIME_FRAMES:
                is_canvas_full = self.is_showing_text and self.current_frame - self.showing_text_start < TRANSITION_TIME_FRAMES

                self.background_canvas_point_in_time += datetime.timedelta(seconds=30)
                self.load_background_canvas(self.background_canvas_offset_x, self.background_canvas_offset_y,
                                            self.background_canvas_point_in_time,
                                            open_new=False, update_live_canvas=not is_canvas_full)
                if is_canvas_full:
                    self.frame_data = self.background_canvas.copy()
                self.current_frame += 1
                return self.frame_data


# @profile
def main2022_rawvideo():
    name_prefix = f"credits_{datetime.datetime.now().timestamp()}"
    canvas_width = int(CANVAS_WIDTH_2022 // VPIXW_PER_PIXEL)  # effective canvas width
    canvas_height = int(CANVAS_HEIGHT_2022 // VPIXW_PER_PIXEL)
    print(canvas_width, canvas_height)
    credits_generator = CreditsGenerator(NAMES)
    credits_generator.load_background_canvas(600, 600, ciso8601.parse_datetime("2022-04-01T16:00:00.000"))

    pbar = tqdm(unit="frames")
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

    for frame_data in credits_generator:
        ffmpeg_proc.stdin.write(frame_data.tobytes())
        pbar.update(1)
    ffmpeg_proc.stdin.flush()
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()


if __name__ == "__main__":
    main2022_rawvideo()
