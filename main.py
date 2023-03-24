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


# split canvas into chunks of 125 * 125
#


def main():
    with open("data/place-meta.json", "r") as meta_file:
        meta = json.load(meta_file)
    meta2022 = meta["2022"]
    canvas_size_x = meta2022["sizeX"]
    last = 0
    discarded_hits = 0
    with open("data/new_encoded.bin", "wb") as outfile:
        for chunk in meta2022["chunks"]:
            path = chunk["path"]
            size_x, size_y, size_color = chunk["format"]
            points = chunk["points"]
            with open(path, "rb") as chunk_file:
                chunk_data = chunk_file.read()
                reader = BitReader(chunk_data)

            step_nbits = sum((size_x, size_y, size_color))
            hits = min(points, math.floor(len(chunk_data) / step_nbits * 8))

            # hit_buffer = list()
            for _ in trange(hits):
                x, y, color = reader.read(size_x), reader.read(size_y), reader.read(size_color)

                # coord_index = y * canvas_size_x + x
                # if (coord_index - last) > 2**20:
                #     discarded_hits += 1
                # last = coord_index
                # hit_buffer.append((x, y, color))

                # if len(hit_buffer) > 256:


            print(discarded_hits)


if __name__ == "__main__":
    main()
