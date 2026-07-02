import logging
from typing import List

def load_channels() -> List[str]:
    try:
        from modules.mongo import db

        # Ambil channel_id unik dari streams
        channel_ids = db['streams'].distinct('channel_id')

        # Ambil data channel berdasarkan channel_id
        channels = db['channels'].find(
            {'_id': {'$in': channel_ids}},
            {'scrapper_name': 1}
        )

        result = [
            str(channel['scrapper_name']).strip()
            for channel in channels
            if channel.get('scrapper_name')
        ]

        if result:
            logging.info(f"Channel dimuat dari MongoDB: {result}")
            return result

    except Exception as e:
        logging.error(
            f"Gagal memuat channel dari MongoDB: {e}. Menggunakan fallback."
        )

    return FALLBACK_CHANNELS


# Fallback jika MongoDB tidak bisa diakses saat startup
FALLBACK_CHANNELS: List[str] = [
    'prambors',
    'smartfm',
    'elshintajkt',
    'mnctrijayajakarta',
    'rripro',
    'sonorajkt',
    'rripro1',
    'rripro2',
    'rripro4',
    'passfm',
    'suarasurabaya',
    'iradio',
    'rripro1banten',
    'kbr',
    'genfm',
    'kisfm',
    'mostfm',
    'istana',
    'radiodms',
]

CHANNELS: []
