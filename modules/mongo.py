import pymongo
import logging
import time
from datetime import datetime
from typing import List, Optional
import os
from dotenv import load_dotenv


load_dotenv()

MONGO_URI      = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "dl_livestreams")

# ─────────────────────────────────────────────
# Retry / Reconnect settings
# ─────────────────────────────────────────────
MONGO_MAX_RETRIES   = int(os.getenv("MONGO_MAX_RETRIES", "5"))
MONGO_RETRY_DELAY   = float(os.getenv("MONGO_RETRY_DELAY", "3"))   # detik
MONGO_SERVER_TIMEOUT = int(os.getenv("MONGO_SERVER_TIMEOUT", "5000"))  # ms

# ─────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────

_client: Optional[pymongo.MongoClient] = None


def _create_client() -> pymongo.MongoClient:
    return pymongo.MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=MONGO_SERVER_TIMEOUT,
        connectTimeoutMS=MONGO_SERVER_TIMEOUT,
        socketTimeoutMS=MONGO_SERVER_TIMEOUT,
    )


def _get_db():
    """
    Mengembalikan database handle.
    Jika koneksi terputus, mencoba reconnect secara otomatis.
    """
    global _client

    for attempt in range(1, MONGO_MAX_RETRIES + 1):
        try:
            if _client is None:
                _client = _create_client()

            # Cek koneksi masih hidup
            _client.admin.command("ping")
            return _client[MONGO_DATABASE]

        except pymongo.errors.PyMongoError as e:
            logging.warning(
                f"[MongoDB] Koneksi gagal (percobaan {attempt}/{MONGO_MAX_RETRIES}): {e}"
            )
            _client = None  # Paksa reconnect di iterasi berikutnya

            if attempt < MONGO_MAX_RETRIES:
                logging.info(
                    f"[MongoDB] Mencoba ulang dalam {MONGO_RETRY_DELAY} detik..."
                )
                time.sleep(MONGO_RETRY_DELAY)

    raise ConnectionError(
        f"[MongoDB] Tidak dapat terhubung setelah {MONGO_MAX_RETRIES} percobaan."
    )


@property
def db():
    return _get_db()


# ─────────────────────────────────────────────
# Helpers — semua fungsi menggunakan _get_db()
# ─────────────────────────────────────────────

def get_pending_streams(start_date: str, end_date: str) -> List[dict]:

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d %H:%M:%S")
    except ValueError:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d")

    cursor = _get_db()['streams'].find(
        {
            'source': 'radio',
            # Handle kemungkinan trailing space pada nilai status
            'status_transcript': {'$regex': r'^\s*(PENDING|FAILED)\s*$', '$options': 'i'},
            'date': {'$gte': start_dt, '$lte': end_dt},
        },
        sort=[('date', 1)],
    )
    return list(cursor)


def mark_stream_in_progress(stream_id) -> None:
    _get_db()['streams'].update_one(
        {'_id': stream_id},
        {
            '$set': {
                'status_transcript': 'IN_PROGRESS',
                'updated_at': datetime.now(),
                'updated_by': 'stt_RADIO_1',
            }
        },
    )


def push_chunk_to_stream(stream_id, chunk_data: dict) -> None:
    _get_db()['streams'].update_one(
        {'_id': stream_id},
        {
            '$push': {'chunks': chunk_data},
            '$set': {
                'updated_at': datetime.now(),
                'updated_by': 'stt_RADIO_1',
            },
        },
    )


def complete_stream(
    stream_id,
    transcript: str,
    total_chunk: int,
    status: str,
) -> None:

    status_map = {
        'SUCCESS': 'COMPLETED',
        'SILENT':  'SILENT',
        'UNKOWN':  'FAILED',
    }
    _get_db()['streams'].update_one(
        {'_id': stream_id},
        {
            '$set': {
                'status_transcript': status_map.get(status, 'FAILED'),
                'transcript': transcript,
                'total_chunk': total_chunk,
                'updated_at': datetime.now(),
                'updated_by': 'stt_RADIO_1',
            }
        },
    )
