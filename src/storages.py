# src/storages.py
from pathlib import Path
import subprocess
import logging
from threading import Lock, Thread
from datetime import datetime
from typing import List


class SingleImageStorage:
    def __init__(self, root: str):
        self.root = Path(root)

    def store(self, camera_id: str, image: bytes):
        now = datetime.now()
        date_dir = now.strftime('%Y-%m-%d')
        filename = now.strftime('%H-%M-%S') + '.jpg'
        out_dir = self.root / camera_id / date_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        with path.open('wb') as f:
            f.write(image)
        logging.info(f'stored image for {camera_id} at {path}')


class VideoSnippetStorage:
    def __init__(self, root: str, batch_size: int, fps: int, crf: int, preset: str):
        self.root = Path(root)
        self.batch_size = batch_size
        self.fps = fps
        self.crf = crf
        self.preset = preset
        self.frames: List[bytes] = []
        self.lock = Lock()

    def store(self, camera_id: str, image: bytes):
        with self.lock:
            self.frames.append(image)
            if len(self.frames) >= self.batch_size:
                self._start_encoding(camera_id, self.frames)
                self.frames = []

    def flush(self, camera_id: str):
        with self.lock:
            if not self.frames:
                return
            batch = self.frames
            self.frames = []
        self._start_encoding(camera_id, batch)

    def _start_encoding(self, camera_id: str, frames: List[bytes]):
        Thread(target=self._encode, args=(camera_id, frames), daemon=True).start()

    def _encode(self, camera_id: str, frames: List[bytes]):
        now = datetime.now()
        date_dir = now.strftime('%Y-%m-%d')
        filename = now.strftime('%H-%M-%S') + '.mp4'
        out_dir = self.root / camera_id / date_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename

        cmd = [
            'ffmpeg', '-y',
            '-f', 'image2pipe',
            '-vcodec', 'mjpeg',
            '-r', str(self.fps),
            '-i', 'pipe:0',
            '-vsync', 'vfr',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            '-crf', str(self.crf),
            '-preset', self.preset,
            str(out_path),
        ]

        logging.info(f'encoding {len(frames)} frames at {self.fps} fps to {out_path}')
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for frame in frames:
                proc.stdin.write(frame)
            proc.stdin.flush()
            proc.stdin.close()
            proc.wait()
        except Exception as e:
            logging.error(f'ffmpeg encoding failed: {e}')

        logging.info(f'created video for {camera_id} at {out_path}')
