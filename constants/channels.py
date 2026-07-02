import logging
from typing import List


def load_channels() -> List[str]:

    try:
        from modules.mongo import _get_db
        db = _get_db()

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

        logging.warning("Tidak ada channel ditemukan di MongoDB.")
        return []

    except Exception as e:
        logging.error(
            f"Gagal memuat channel dari MongoDB: {e}. "
            f"Akan dicoba lagi di iterasi berikutnya."
        )
        return []


CHANNELS: List[str] = []
