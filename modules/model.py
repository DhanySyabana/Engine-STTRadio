from dataclasses import dataclass
from threading import Semaphore
from typing import List, Literal, Optional, Union
from faster_whisper import transcribe
import whisperx
import numpy as np
import logging


@dataclass
class TranscribeResult:
    text: str
    start: float
    end: float
    language: str
    language_confidence: Optional[float]

class STTModel:
    def __init__(self, model_name: str = 'base', device: Literal['cpu', 'cuda'] = 'cuda', compute_type = "float16", workers=0, lang: str = "id", concurrent_limit: int = 1):

        self.__model = whisperx.load_model(model_name, device, compute_type=compute_type, language=lang)
        self.__workers = workers
        self.__semaphore = Semaphore(concurrent_limit)

    def transcribe(self, audio: Union[np.ndarray, str], batch_size: int = 16, lang: str = "id") -> str:
        result = self.__model.transcribe(audio, batch_size=batch_size, language=lang, num_workers=self.__workers)
        # logging.info(result)
        result = ''.join([r['text'] for r in result['segments']])

        return result
    def transcribe_timestamps(self, audio: Union[np.ndarray, str], batch_size: int = 16, lang: str = "id") -> List[TranscribeResult]:
        result = self.__model.transcribe(audio, batch_size=batch_size, language=lang, num_workers=self.__workers)
        ret : List[TranscribeResult] = []
        for seg in result['segments']:
           ret.append(
                TranscribeResult(
                    text=seg.get("text", ""),
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                    language=result.get("language", lang),
                    language_confidence=result.get("language_probability")
                )
            )
        return ret
    def transcribe_with_lock(self, audio: Union[np.ndarray, str], batch_size: int = 4, lang: str = "id") -> List[TranscribeResult]:
        with self.__semaphore:
            return self.transcribe_timestamps(audio,batch_size,lang)
        


