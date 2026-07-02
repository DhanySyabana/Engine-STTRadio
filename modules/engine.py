import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        self.__workers = int(os.getenv("ENGINE_WORKERS", "5"))
        logging.info(
            f"Engine Ready — parallel workers: {self.__workers}"
        )

    def set_model(self, model: STTModel):
        self.__model = model

    # ─────────────────────────────────────────────────────────────
    # Proses satu stream (dijalankan di thread pool)
    # ─────────────────────────────────────────────────────────────

    def _process_stream(self, stream: dict) -> None:

        stream_id = stream['_id']
        filename  = stream.get('filename', '')
        file_path = stream.get('file_path', '')

        if not file_path:
            logging.warning(
                f"[{stream_id}] Tidak memiliki file_path, dilewati."
            )
            return

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
            return

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
            return

        final_status     = 'SUCCESS'
        final_transcript = ''
        chunk_count      = 0

        # Tandai stream sebagai sedang diproses
        mark_stream_in_progress(stream_id)

        try:
            # ── I/O: baca dan preprocess audio (berjalan paralel) ──
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

            logging.info(f"[{filename}] Audio siap, menunggu slot transkripsi...")

            # ── Transkripsi: diproteksi lock, antri di antara thread ──
            whisper_chunks = self.__model.transcribe_with_lock(arr)

            logging.info(f"[{filename}] Transkripsi selesai, menyimpan ke DB...")

            n          = len(whisper_chunks)
            total_slot = n
            now        = datetime.now()
            detik      = 0.0  # dalam satuan detik (float)

            for j, chunk in enumerate(whisper_chunks):

                push_chunk_to_stream(stream_id, {
                    '_id':           ObjectId(),
                    'current_chunk': j + 1,
                    'second_start ': floor(detik * 1000),
                    'second_end':    ceil(chunk.end * 1000),
                    'result':        chunk.text,
                    'chunk_status':  'SUCCESS',
                    'created_at':    now,
                    'updated_at':    now,
                })

                final_transcript += chunk.text
                detik = chunk.end  # tetap simpan dalam detik untuk kalkulasi berikutnya

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
                return

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

    # ─────────────────────────────────────────────────────────────
    # Entry point — jalankan semua stream secara paralel
    # ─────────────────────────────────────────────────────────────

    def run_timestamps(self, start_date: str, end_date: str):

        streams = get_pending_streams(start_date, end_date)

        if not streams:
            logging.info(
                f"Tidak ada audio PENDING dalam rentang {start_date} – {end_date}"
            )
            return

        logging.info(
            f"Jumlah audio: {len(streams)} | "
            f"Paralel workers: {self.__workers}"
        )

        with ThreadPoolExecutor(max_workers=self.__workers) as pool:

            futures = {
                pool.submit(self._process_stream, stream): stream
                for stream in streams
            }

            for future in as_completed(futures):
                stream = futures[future]
                filename = stream.get('filename', str(stream['_id']))
                try:
                    future.result()
                except Exception as e:
                    # Exception seharusnya sudah ditangani di _process_stream,
                    # ini safety net jika ada yang lolos
                    logging.error(
                        f"[{filename}] Unhandled exception di thread: {e}"
                    )
                    send_telegram_alert(
                        f"💥 Unhandled thread error: `{filename}`\n\n"
                        f"```{str(e)[-1500:]}```"
                    )
