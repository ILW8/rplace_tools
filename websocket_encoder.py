#!/usr/bin/env python

import asyncio
import datetime
import queue
import threading
import time

import tqdm
import websockets
import subprocess


class EncodingThread(threading.Thread):
    ffmpeg_proc = None
    # frames_queue = queue.Queue(32)
    should_stop = False
    pbar = tqdm.tqdm()

    # command = [ FFMPEG_BIN,
    #         '-y', # (optional) overwrite output file if it exists
    #         '-f', 'rawvideo',
    #         '-vcodec','rawvideo',
    #         '-s', '420x360', # size of one frame
    #         '-pix_fmt', 'rgb24',
    #         '-r', '24', # frames per second
    #         '-i', '-', # The imput comes from a pipe
    #         '-an', # Tells FFMPEG not to expect any audio
    #         '-vcodec', 'mpeg'",
    #         'my_output_videofile.mp4' ]
    #
    # pipe = sp.Popen( command, stdin=sp.PIPE, stderr=sp.PIPE)

    # def feed_frames(self):
    #     while not self.should_stop:
    #         try:
    #             data = self.frames_queue.get_nowait()
    #             self.ffmpeg_proc.stdin.write(data)
    #             self.ffmpeg_proc.stdin.flush()
    #             self.pbar.update(1)
    #             # print("wftffmpeg")
    #         except queue.Empty:
    #             time.sleep(0.001)

    def run(self):
        self.ffmpeg_proc = subprocess.Popen(["ffmpeg",
                                             "-f", "rawvideo",
                                             "-vcodec", "rawvideo",
                                             "-s", "1000x1000",
                                             "-pix_fmt", "rgba",
                                             "-r", "240",
                                             "-i", "-",
                                             "-pix_fmt", "yuv420p",
                                             # "-vf", "scale=250x250",
                                             "-an",
                                             "-c:v", "h264_videotoolbox",
                                             "-q:v", "80",
                                             f"{datetime.datetime.now().timestamp()}.mp4"],
                                            stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        # feeder = threading.Thread(target=self.feed_frames)
        # feeder.start()
        self.ffmpeg_proc.wait()

    def stop(self):
        if self.ffmpeg_proc is not None:  # don't think it could ever be none?
            self.ffmpeg_proc.stdin.close()
        self.should_stop = True

    def add_frame(self, frame_data: bytes):
        # self.frames_queue.put(frame_data)
        self.ffmpeg_proc.stdin.write(frame_data)
        self.ffmpeg_proc.stdin.flush()
        self.pbar.update(1)


class WebsocketListener:
    def __init__(self, encoder: EncodingThread):
        self.exit_future = None
        self.encoder = encoder

    async def echo(self, websocket):
        async for message in websocket:
            if type(message) is str:
                if message == "end":
                    # signal ffmpeg to stop
                    if self.encoder is not None:
                        self.encoder.stop()
                    self.exit_future.cancel()
                continue
            # print(message)
            # print(f"got a message of length {len(message)}")
            assert self.encoder is not None
            self.encoder.add_frame(message)

    async def main(self):
        async with websockets.serve(self.echo, "localhost", 9999, max_size=None, max_queue=64, ping_interval=None):
            self.exit_future = asyncio.get_running_loop().create_future()
            try:
                await self.exit_future  # run forever
            except asyncio.CancelledError:
                pass


def main():
    encoder = EncodingThread()
    encoder.start()
    websocket_listener = WebsocketListener(encoder)
    asyncio.run(websocket_listener.main())
    encoder.join()


if __name__ == "__main__":
    main()
