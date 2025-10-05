import struct
import numpy as np

from webcam import FrameFormatter
from turbojpeg import TurboJPEG, TJSAMP_422
from linuxpy.video.device import PixelFormat

class ConverterYUYV:
    def __init__(self, fmt):
        self.oU  = fmt.width * fmt.height 
        self.oV  = self.oU + self.oU // 2
        self.end = 2 * self.oU
        self.buf = bytearray(self.end) 
        self.fmt = fmt

    def convert(self, data):
        # libjpeg-turbo wants YUV data with the planes separated, see:
        # https://rawcdn.githack.com/libjpeg-turbo/libjpeg-turbo/main/doc/turbojpeg/group___turbo_j_p_e_g.html#YUVnotes
        self.buf[0:self.oU:2] = data[0:len(data):4]
        self.buf[1:self.oU:2] = data[2:len(data):4]
        self.buf[self.oU:self.oV:1] = data[1:len(data):4]
        self.buf[self.oV:self.end:1] = data[3:len(data):4]
        return self.fmt.jpeg.encode_from_yuv(
            self.buf,
            self.fmt.height,
            self.fmt.width,
            85,
            TJSAMP_422
        )

class JPEGFormatter(FrameFormatter):
    def __init__(self):
        self.jpeg = TurboJPEG()
        self.conv = None
        super().__init__()

    def setup_format(self, fmt):
        super().setup_format(fmt)
        # TODO: add converters for more V4L formats
        match self.pixfmt:
            case PixelFormat.YUYV:
                self.conv = ConverterYUYV(self)
            case _:
                raise ValueError(f"Unsupported pixel format: {frame.pixel_format}")

    def process_frame(self, frame):
        return self.conv.convert(frame.data)
