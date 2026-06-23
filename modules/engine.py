import logging
from datetime import datetime
from math import ceil, floor

from bson import ObjectId

import numpy as np
import pydub


from modules.model import STTModel
from modules.mongo import (
    get_pending_streams,
    mark_stream_in_progress,
    push_chunk_to_stream,
    complete_stream,
)
from modules.telegram_alert import send_telegram_alert

class Engine:
    def __init__(self, scrapper_name: str):

        self.__scrapper_name = scrapper_name
        logging.info(f"Engine siap untuk channel: {scrapper_name}")

    def set_model(self, model: STTModel):
        self.__model = model

    def run_timestamps(self, start_date: str, end_date: str):

        streams = get_pending_streams(self.__scrapper_name, start_date, end_date)

        if not streams:
            logging.info(
                f"[channel={self.__scrapper_name}] Tidak ada audio PENDING "
                f"dalam rentang {start_date} – {end_date}"
            )
            return

        logging.info(f"[channel={self.__scrapper_name}] Jumlah audio: {len(streams)}")

        for stream in streams:
            stream_id  = stream['_id']
            filename   = stream.get('filename', '')
            file_path  = stream.get('file_path', '')

            if not file_path:
                logging.warning(f"Stream {stream_id} tidak memiliki file_path, dilewati.")
                continue

            final_status     = 'SUCCESS'
            final_transcript = ''
            chunk_count      = 0

            # Tandai stream sebagai sedang diproses
            mark_stream_in_progress(stream_id)

            try:
                logging.info(f"Membaca file audio: {file_path}")
                segments = pydub.AudioSegment.from_mp3(file_path)
                logging.info("File audio berhasil dibaca")

                # Preprocess: konversi ke 16 kHz, mono, 16-bit
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

                    logging.info(f"Mentranskrip: {filename}")
                    whisper_chunks = self.__model.transcribe_with_lock(arr)

                    n = len(whisper_chunks)
                    # total slot = (jumlah segment × 2) + 1 (slot silent penutup)
                    total_slot = n * 1
                    now = datetime.now()

                    for j, chunk in enumerate(whisper_chunks):

                        push_chunk_to_stream(stream_id, {
                            '_id':            ObjectId(),
                            'current_chunk':  j * 1 + 1,
                            'second_start':     floor(detik),
                            'second_end':    ceil(chunk.end),
                            'result':         chunk.text,
                            'chunk_status': 'SUCCESS',
                            'created_at':     now,
                            'updated_at':     now,
                        })

                        final_transcript += chunk.text
                        detik = ceil(chunk.end)

                    chunk_count = total_slot

                except Exception as e:
                    logging.exception(e)
                    raise e

            except Exception as e:
                logging.exception(e)
                final_status = 'UNKOWN'
                logging.info(f"[{filename}] GAGAL diproses")
                send_telegram_alert(f"Transkrip gagal: {filename} gagal diproses")

            # Tentukan status akhir
            if final_transcript.strip() == '' and final_status != 'UNKOWN':
                final_status = 'SILENT'

            logging.info(f"result: {final_transcript}")
            complete_stream(
                stream_id=stream_id,
                transcript=final_transcript,
                total_chunk=chunk_count,
                status=final_status,
            )
            logging.info(f"Selesai: {filename} → status={final_status}")

