
from math import ceil, floor
from constants.radio import channels
from custom_types.engine import TranskripStatus
from modules.model import STTModel
from modules.mongo import save_audio, save_audio_chunk
from modules.siputro import Siputro, logging

import pydub
import numpy as np


class Engine:
    def __init__(self, channel_id: int, chunks_length: float = 10000):
        self.__client = Siputro(channel_id)
        self.__radio = channels[channel_id]
        self.__chunks_length = chunks_length

    def set_model(self, model: STTModel):
        self.__model = model

    def check_audio_exist(self, start_date: str, end_date: str) -> bool:
        audio_list_check = self.__client.get_audio_file_name_list(start_date, end_date, is_preview='Y')

        return len(audio_list_check) > 0



    def run(self, start_date: str, end_date: str):
        #check first
        
        # audio_list_check = self.__client.get_audio_file_name_list(start_date, end_date, is_preview='Y')

        # logging.info(("A", audio_list))

        if not self.check_audio_exist(start_date, end_date):
            logging.info("Empty")
            return

        
        audio_list = self.__client.get_audio_file_name_list(start_date, end_date)

        # logging.info(("AUDIO LENGTH: ", len(audio_list)))

        progress_per_item = 100 / len(audio_list) 
        progress = 0
        i = 0
        for audio in audio_list:
            status_audio = TranskripStatus.SUCCESS
            is_silent = True
            result_audio = ''
            try:
                segments = pydub.AudioSegment.from_mp3("{}/{}".format(self.__radio.path, audio))

                #Preprocess to prepare audio before fed into whisper
                if segments.frame_rate != 16_000:
                    segments = segments.set_frame_rate(16_000)
                if segments.sample_width != 2:
                    segments = segments.set_sample_width(2)
                if segments.channels != 1:
                    segments = segments.set_channels(1)



                chunks = pydub.utils.make_chunks(segments, self.__chunks_length)

                for i, chunk in enumerate(chunks):

                    status = TranskripStatus.UNKOWN
                    detik_awal = int(self.__chunks_length * i / 1000)
                    detik_akhir = int(self.__chunks_length * (i + 1) / 1000)
                    try :
                        arr = np.array(chunk.get_array_of_samples())
                        arr = arr.astype(np.float32) / 32_768.0
                        
                        result = self.__model.transcribe(arr)

                        if result.strip() == '':
                            status = TranskripStatus.SILENT
                        else:
                            status = TranskripStatus.SUCCESS

                        self.__client.post_audio_chunk(audio, len(chunks), i, detik_awal, detik_akhir, result, status) 
                        # save_audio_chunk(audio, len(chunks), i, ceil(detik_awal), ceil(detik_akhir), result, status)

                        # logging.info(("CHUNK : ", audio, len(chunks), i, detik_awal, detik_akhir, result, status) )

                        result_audio += result

                        is_silent = is_silent and status == TranskripStatus.SILENT
                        if status == TranskripStatus.SUCCESS:
                            status_audio = TranskripStatus.SUCCESS

                    except Exception as e:
                        logging.exception(e)
                
            except Exception as e:
                logging.exception(e)
                status = TranskripStatus.UNKOWN

            end_status = TranskripStatus.SILENT if is_silent and status_audio != TranskripStatus.UNKOWN else status_audio

            progress += progress_per_item

            if (i == len(audio_list) - 1):
                progress = 100
            i += 1

            self.__client.post_audio(audio, result_audio, end_status, progress)
            # save_audio(audio, result_audio, end_status, progress)

            # logging.info(result_audio)

    def run_timestamps(self, start_date: str, end_date: str):
        
        # audio_list_check = self.__client.get_audio_file_name_list(start_date, end_date, is_preview='Y')

        # logging.info(("A", audio_list))

        if not self.check_audio_exist(start_date, end_date):
            return


        audio_list = self.__client.get_audio_file_name_list(start_date, end_date)

        logging.info(("AUDIO LENGTH: ", len(audio_list)))

        progress_per_item = 100 / len(audio_list) 
        progress = 0
        for audio in audio_list:
            final_status = TranskripStatus.SUCCESS

            final_result = ''
            try:
                logging.info("Getting Audio File:")
                segments = pydub.AudioSegment.from_mp3("{}/{}".format(self.__radio.path, audio))
                logging.info("Got Audio File")

                #Preprocess to prepare audio before fed into whisper
                if segments.frame_rate != 16_000:
                    segments = segments.set_frame_rate(16_000)
                if segments.sample_width != 2:
                    segments = segments.set_sample_width(2)
                if segments.channels != 1:
                    segments = segments.set_channels(1)
                
                detik = 0
                try:
                    arr = np.array(segments.get_array_of_samples())
                    arr = arr.astype(np.float32) / 32_768.0

                    logging.info(("Transcribing audio :", audio))
                    chunks = self.__model.transcribe_with_lock(arr)
                    print(chunks)
                    chunks_length = len(chunks)
                    for i, chunk in enumerate(chunks):
                        self.__client.post_audio_chunk(audio, chunks_length * 2 + 1, i * 2, floor(detik), ceil(chunk.start), '', TranskripStatus.SILENT)
                        self.__client.post_audio_chunk(audio, chunks_length * 2 + 1, i * 2 + 1, ceil(chunk.start), ceil(chunk.end), chunk.text, TranskripStatus.SUCCESS)

                        save_audio_chunk(audio, chunks_length * 2 + 1, i * 2, floor(detik), ceil(chunk.start), '', TranskripStatus.SILENT)
                        save_audio_chunk(audio, chunks_length * 2 + 1, i * 2 + 1, floor(chunk.start), ceil(chunk.end), chunk.text, TranskripStatus.SUCCESS)

                        final_result += chunk.text
                        detik = ceil(chunk.end)

                    self.__client.post_audio_chunk(audio, chunks_length * 2 + 1, chunks_length * 2, floor(detik), 10 * 60, '', TranskripStatus.SILENT)
                    save_audio_chunk(audio, chunks_length * 2 + 1, chunks_length * 2, floor(detik), 10 * 60, '', TranskripStatus.SILENT)
                except Exception as e:
                    logging.exception(e)
                    # rethrow exception
                    raise e

            except Exception as e:
                logging.exception(e)
                final_status = TranskripStatus.UNKOWN
                print("FINAL STATUS:", final_status)
                # break

            

            progress += progress_per_item
            if final_result.strip() == '':
                final_status = TranskripStatus.SILENT

            logging.info("SAVING AUDIO")
            self.__client.post_audio(audio, final_result, final_status, progress)
            save_audio(audio, final_result, final_status, progress)
            logging.info("AUDIO SAVED")
            






            
