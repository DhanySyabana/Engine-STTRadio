from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

@dataclass
class SaluranData:
    id: int
    nama: str
    slug: str
    logo: str
    nama_folder: str
    id_siputra: str
    created_at: str
    updated_at: str
    deleted_at: Optional[str]

@dataclass
class LogData:
    id: int
    saluran_id: int
    start_date: str
    end_date: str
    jml_audio: int
    status: str
    updated_at: str
    created_at: str 

@dataclass
class AudioListData:
    log_id: Optional[LogData]
    saluran: Optional[SaluranData]
    audio_list: List[str]
    jml_audio: int
    
    def __post_init__(self):
        if self.saluran is not None:
            self.saluran = SaluranData(**self.saluran)
        if self.log_id is not None:
            self.log_id = LogData(**self.log_id)

@dataclass
class AudioListResponse:
    status: str
    data: AudioListData
    def __post_init__(self):
        self.data = AudioListData(**(self.data))


