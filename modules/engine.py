import logging
import os
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


# ─────────────────────────────────────────────
# Konstanta error yang diketahui dari ffmpeg/pydub
# ─────────────────────────────────────────────

_CORRUPT_FILE_SIGNALS = (
    "Invalid data found when processing input",
    "Failed to find two consecutive MPEG audio frames",
    "No such file or directory",
    "moov atom not found",
    "Invalid argument",
    "Error opening input",
)


def _is_corrupt_audio_error(e: Exception) -> bool:
    """Mendeteksi apakah exception berasal dari file audio rusak/tidak valid."""
    msg = str(e).lower()
    return any(sig.lower() in msg for sig in _CORRUPT_FILE_SIGNALS)


class Engine:

    def __init__(self):
        logging.info("Engine Ready To Run")

    def set_model(self, model: STTModel):
        self.__model = model

    def run_timestamps(self, start_date: str, end_date: str, channel_ids: list = None):

        streams = get_pending_streams(start_date, end_date, channel_ids)

        if not streams:
            logging.info(
                f"Tidak ada audio PENDING dalam rentang {start_date} – {end_date}"
            )
            return

        logging.info(f"Jumlah audio PENDING: {len(streams)}")

        # ── Jalankan sekuensial (satu per satu) untuk stabilitas GPU ──
        for stream in streams:
            stream_id = stream['_id']
            filename  = stream.get('filename', '')
            file_path = stream.get('file_path', '')

            if not file_path:
                logging.warning(
                    f"[{stream_id}] Tidak memiliki file_path, dilewati."
                )
                continue

            # ── Validasi: file harus ada dan tidak kosong ──────────────
            if not os.path.isfile(file_path):
                logging.error(
                    f"[{filename}] File tidak ditemukan: {file_path}. "
                    f"Stream ditandai FAILED."
                )
                complete_stream(
                    stream_id=stream_id,
                    transcript='',
                    total_chunk=0,
                    status='UNKOWN',
                )
                continue

            if os.path.getsize(file_path) == 0:
                logging.error(
                    f"[{filename}] File kosong (0 bytes): {file_path}. "
                    f"Stream ditandai FAILED."
                )
                complete_stream(
                    stream_id=stream_id,
                    transcript='',
                    total_chunk=0,
                    status='UNKOWN',
                )
                continue

            final_status     = 'SUCCESS'
            final_transcript = ''
            chunk_count      = 0

            # Tandai stream sebagai sedang diproses
            mark_stream_in_progress(stream_id)

            try:
                logging.info(f"[{filename}] Membaca file audio: {file_path}")
                segments = pydub.AudioSegment.from_mp3(file_path)

                if segments.frame_rate != 16_000:
                    segments = segments.set_frame_rate(16_000)
                if segments.sample_width != 2:
                    segments = segments.set_sample_width(2)
                if segments.channels != 1:
                    segments = segments.set_channels(1)

                arr = np.array(segments.get_array_of_samples())
                arr = arr.astype(np.float32) / 32_768.0

                logging.info(f"[{filename}] Mentranskrip audio...")
                whisper_chunks = self.__model.transcribe_with_lock(arr)

                n          = len(whisper_chunks)
                total_slot = n
                now        = datetime.now()
                detik      = 0.0  # dalam satuan detik (float)

                for j, chunk in enumerate(whisper_chunks):

                    push_chunk_to_stream(stream_id, {
                        '_id':           ObjectId(),
                        'current_chunk': j + 1,
                        'second_start':  floor(detik * 1000),  # Disimpan dalam ms
                        'second_end':    ceil(chunk.end * 1000),  # Disimpan dalam ms
                        'result':        chunk.text,
                        'chunk_status':  'SUCCESS',
                        'created_at':    now,
                        'updated_at':    now,
                    })

                    final_transcript += chunk.text
                    detik = chunk.end

                chunk_count = total_slot

            except Exception as e:

                if _is_corrupt_audio_error(e):
                    # ── File rusak / data tidak valid → FAILED diam-diam ──
                    logging.warning(
                        f"[{filename}] File audio rusak atau tidak valid, "
                        f"dilewati. Detail: {e}"
                    )
                    complete_stream(
                        stream_id=stream_id,
                        transcript='',
                        total_chunk=0,
                        status='UNKOWN',
                    )
                    continue

                # ── Error tak terduga → log + alert Telegram ───────────
                logging.exception(e)
                final_status = 'UNKOWN'
                logging.error(f"[{filename}] GAGAL diproses")
                send_telegram_alert(
                    f"⚠️ Transkrip gagal: `{filename}`\n\n```{str(e)[-1500:]}```"
                )

            # Tentukan status akhir
            if final_transcript.strip() == '' and final_status != 'UNKOWN':
                final_status = 'SILENT'

            logging.info(f"[{filename}] Transcript: {final_transcript[:120]}...")
            complete_stream(
                stream_id=stream_id,
                transcript=final_transcript,
                total_chunk=chunk_count,
                status=final_status,
            )
            logging.info(f"[{filename}] Selesai → status={final_status}")
