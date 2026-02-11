import os
import requests
from typing import Optional, List
import logging

from custom_types.api import AudioListResponse
from custom_types.engine import TranskripStatus
from modules.model import Literal



from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry





s = requests.Session()

retries = Retry(total=5,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504])

s.mount('http://', HTTPAdapter(max_retries=retries))

class Siputro:
    def __init__(self, channel_id : int):
        self.__channel_id = channel_id
        self.__url = os.getenv('API_URL')
        self.__log_id : Optional[int] = None

    def get_audio_file_name_list(self, start_date: str, end_date: str, is_preview: Literal['Y', 'N'] = 'N') -> List[str]: 
        try:
            resp = s.get(
                "{}/api/audio/saluran".format(self.__url), 
                params={
                    'start_date': start_date,
                    'end_date': end_date,
                    'saluran_id': self.__channel_id,
                    'is_preview': is_preview
                },
                verify=False,
                timeout=10,
            )
            if resp.status_code != 200:
                raise Exception('Failed Getting Audio List from API')


            body = AudioListResponse(**resp.json())
            
            
            if body.data.log_id is not None:
                self.__log_id = body.data.log_id.id

            # logging.info(self.__log_id)
            # exit()

            return body.data.audio_list
        except Exception as e:
            logging.exception(e)            
            return []

    def post_audio_chunk(self, nama_audio: str, total_chunk: int, current_chunk: int, detik_awal: int, detik_akhir: int, result: str, status: TranskripStatus, verbose: bool = False):
        if verbose:        
            print("""SAVING CHUNK:
    Nama Audio: {},
    Current Chunk: {},
    Detik Awal: {},
    Detik Akhir: {},
    Result: {},
    Status: {}
""".format(nama_audio, current_chunk, detik_awal, detik_akhir, result, status.name))
        try:
            logging.info(({
                    "parent_log_id": self.__log_id,
                    "saluran_id": self.__channel_id,
                    "nama_audio": nama_audio,
                    "total_chunk": total_chunk,
                    "current_chunk": current_chunk,
                    "detik_awal": detik_awal,
                    "detik_akhir": detik_akhir,
                    "result": result,
                    "total_transkrip": status.value
                }

                ))
            resp = s.post(
                "{}/api/audio/log-transkrip".format(self.__url),
                data={
                    "parent_log_id": self.__log_id,
                    "saluran_id": self.__channel_id,
                    "nama_audio": nama_audio,
                    "total_chunk": total_chunk,
                    "current_chunk": current_chunk,
                    "detik_awal": detik_awal,
                    "detik_akhir": detik_akhir,
                    "result": result,
                    "total_transkrip": status.value
                },
                verify=False,
                timeout=10,
            )

            if resp.status_code != 200 and resp.status_code != 201:
                logging.info((resp.text))
                logging.info(resp.history)
                logging.info((resp.status_code, "{}/api/audio/log-transkrip".format(self.__url), "POST"))
                raise Exception('Failed Saving Audio Chunks')
        except Exception as e:
            logging.exception(e)
            # re raising exception for better error handling on the engine
            raise e
    def post_audio(self, nama_audio: str, result:str, status: TranskripStatus, progress_transkrip: int | float, verbose: bool = False):
        if verbose:
            print("""SAVING CHUNK:
    Nama Audio: {},
    Result: {},
    Status: {},
    Progress: {}
""".format(nama_audio, result, status.name, progress_transkrip))
        try:
            resp = s.post(
                "{}/api/audio/log-transkrip-per-audio".format(self.__url),
                data={
                    "parent_log_id": self.__log_id,
                    "saluran_id": self.__channel_id,
                    "nama_audio": nama_audio,
                    "result": result,
                    "total_transkrip": status.value,
                    "progress_transkrip": progress_transkrip
                },
                verify=False,
                timeout=10,
            )

            if resp.status_code != 200 and resp.status_code != 201:

                raise Exception('Failed Saving Audio Chunks')
        except Exception as e:
            logging.exception(e)



        



