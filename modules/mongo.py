import pymongo
from datetime import datetime
from typing import List
import os
from dotenv import load_dotenv


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "dl_livestreams")

client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DATABASE]


def get_pending_streams(start_date: str, end_date: str) -> List[dict]:

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d %H:%M:%S")
    except ValueError:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d")

    cursor = db['streams'].find(
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
    db['streams'].update_one(
        {'_id': stream_id},
        {
            '$set': {
                'status_transcript': 'IN_PROGRESS',
                'updated_at': datetime.now(),
                'updated_by': 'engine_stt_1',
            }
        },
    )


def push_chunk_to_stream(stream_id, chunk_data: dict) -> None:

    db['streams'].update_one(
        {'_id': stream_id},
        {
            '$push': {'chunks': chunk_data},
            '$set': {
                'updated_at': datetime.now(),
                'updated_by': 'engine_stt_1',
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
    db['streams'].update_one(
        {'_id': stream_id},
        {
            '$set': {
                'status_transcript': status_map.get(status, 'FAILED'),
                'transcript': transcript,
                'total_chunk': total_chunk,
                'updated_at': datetime.now(),
                'updated_by': 'engine_stt_1',
            }
        },
    )
