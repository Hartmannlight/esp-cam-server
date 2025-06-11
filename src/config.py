# src/config.py
import yaml
from typing import List, Union, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl, validator
from datetime import datetime


class KumaConfig(BaseModel):
    push_url: HttpUrl
    failure_threshold: int = Field(3, ge=1)


class SingleImageStorageConfig(BaseModel):
    type: Literal['single_image']
    root: str


class VideoSnippetStorageConfig(BaseModel):
    type: Literal['video_snippet']
    root: str
    batch_size: int = Field(100, ge=1)
    fps: int = Field(10, ge=1)
    crf: int = Field(23, ge=0, le=51)
    preset: str = 'medium'


StorageConfig = Union[SingleImageStorageConfig, VideoSnippetStorageConfig]


class IdentityPPConfig(BaseModel):
    type: Literal['identity']


class RotatePPConfig(BaseModel):
    type: Literal['rotate']
    degrees: float
    expand: bool = True


class DateTimeStampPPConfig(BaseModel):
    type: Literal['datetime_stamp']
    fmt: str = '%Y-%m-%d %H:%M:%S'
    position: List[int] = Field([10, 10], min_length=2, max_length=2)
    color: str = Field('#FFFFFF', pattern=r'^#?[0-9A-Fa-f]{6}$')
    font_size: int = Field(20, gt=0)
    font_path: Optional[str] = None


PostProcessorConfig = Union[
    IdentityPPConfig,
    RotatePPConfig,
    DateTimeStampPPConfig,
]


class IntervalTriggerConfig(BaseModel):
    type: Literal['interval']
    seconds: int = Field(..., gt=0)
    start_time: Optional[str]
    end_time: Optional[str]

    @validator('start_time', 'end_time', pre=True)
    def validate_time_format(cls, value):
        if value is None:
            return value
        try:
            datetime.strptime(value, '%H:%M')
        except ValueError:
            raise ValueError('time must be in HH:MM format')
        return value


class CronTriggerConfig(BaseModel):
    type: Literal['cron']
    second: Optional[str] = None
    minute: Optional[str] = None
    hour: Optional[str] = None
    day: Optional[str] = None
    month: Optional[str] = None
    day_of_week: Optional[str] = None


TriggerConfig = Union[IntervalTriggerConfig, CronTriggerConfig]


class CameraConfig(BaseModel):
    id: str
    type: Literal['pull']
    url: HttpUrl
    kuma: Optional[KumaConfig]
    storage: List[StorageConfig]
    postprocessors: List[PostProcessorConfig] = []
    triggers: List[TriggerConfig]

    @validator('triggers')
    def ensure_triggers_not_empty(cls, v):
        if not v:
            raise ValueError('at least one trigger must be defined')
        return v


class AppConfig(BaseModel):
    cameras: List[CameraConfig]


def load_config(path: str) -> AppConfig:
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    return AppConfig.model_validate(data)
