import math
import os
import json
from tqdm import trange


class BitReader:
    position = 0
    bit_offset = 0
    current_byte = 0
    buffer = 0
    data = None

    def __init__(self, data: bytes):
        self.data = data

    def read(self, n_bits: int) -> int:
        if not n_bits:
            return 0

        while self.bit_offset < n_bits:
            self.buffer |= self.data[self.position] << self.bit_offset
            self.position += 1
            self.bit_offset += 8

        real_value = self.buffer & ((1 << n_bits) - 1)
        self.buffer >>= n_bits
        self.bit_offset -= n_bits

        return real_value


def main():
    with open("data/place-meta.json", "r") as meta_file:
        meta = json.load(meta_file)
    # meta2022 = meta["2022"]
    metadata = meta["base"]
    canvas_size_x = metadata["sizeX"]
    last = 0

    for chunk in metadata["chunks"]:
        path = chunk["path"]
        size_x, size_y, size_color = chunk["format"]
        points = chunk["points"]
        with open(path, "rb") as chunk_file:
            chunk_data = chunk_file.read()
            reader = BitReader(chunk_data)

        step_nbits = sum((size_x, size_y, size_color))
        hits = min(points, math.floor(len(chunk_data) / step_nbits * 8))
        # hits = min(1000, hits)

        for row in trange(hits):
            x, y, color = reader.read(size_x), reader.read(size_y), reader.read(size_color)
            # print(",".join(map(str, (row, x, y, color))))
        print(hits)


if __name__ == "__main__":
    main()
