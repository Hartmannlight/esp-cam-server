import io
import os
import platform
from datetime import datetime
from typing import List
from PIL import Image, ImageDraw, ImageFont

from src.config import RotatePPConfig, DateTimeStampPPConfig


class PostProcessor:
    def process(self, image: bytes) -> bytes:
        raise NotImplementedError


class IdentityProcessor(PostProcessor):
    def process(self, image: bytes) -> bytes:
        return image


class RotateProcessor(PostProcessor):
    def __init__(self, cfg: RotatePPConfig):
        self.degrees = cfg.degrees
        self.expand = cfg.expand

    def process(self, image: bytes) -> bytes:
        img = Image.open(io.BytesIO(image)).convert('RGB').rotate(self.degrees, expand=self.expand)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        return buffer.getvalue()


class DateTimeStampProcessor(PostProcessor):
    def __init__(self, cfg: DateTimeStampPPConfig):
        self.format = cfg.fmt
        x, y = cfg.position
        self.position = (float(x), float(y))
        hex_color = cfg.color.lstrip('#')
        self.color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        self.font_size = cfg.font_size
        if cfg.font_path and os.path.isfile(cfg.font_path):
            self.font_path = cfg.font_path
        else:
            self.font_path = (
                'C:/Windows/Fonts/arial.ttf'
                if platform.system() == 'Windows'
                else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
            )

    def process(self, image: bytes) -> bytes:
        img = Image.open(io.BytesIO(image)).convert('RGB')
        draw = ImageDraw.Draw(img)
        timestamp = datetime.now().strftime(self.format)
        try:
            font = ImageFont.truetype(self.font_path, self.font_size)
        except Exception:
            font = ImageFont.load_default()
        draw.text(self.position, timestamp, font=font, fill=self.color)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        return buffer.getvalue()


def build_postprocessors(cfg) -> List[PostProcessor]:
    result: List[PostProcessor] = []
    for pp in cfg.postprocessors:
        if pp.type == 'identity':
            result.append(IdentityProcessor())
        elif pp.type == 'rotate':
            result.append(RotateProcessor(pp))
        elif pp.type == 'datetime_stamp':
            result.append(DateTimeStampProcessor(pp))
    return result
