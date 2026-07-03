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


from bson import ObjectId

CHANNELS: List[str] = []

# List of channel_id (ObjectId or string hex) for main_1.py
CHANNELS_1: List[ObjectId] = [
    # Masukkan channel_id untuk main_1.py di sini
    #Elshinta Jakarta
    ObjectId("6a3a1583752ec84c2eeb8d42"),
    #GEN FM
    ObjectId("6a3a1583752ec84c2eeb8d43"),
    #Iradio
    ObjectId("6a3a1583752ec84c2eeb8d44"),
    #KIS FM
    ObjectId("6a3a1583752ec84c2eeb8d45"),
    #MNC Trijaya
    ObjectId("6a3a1583752ec84c2eeb8d46"),
    #Most FM
    ObjectId("6a3a1583752ec84c2eeb8d47"),
    #PASS FM Jakarta
    ObjectId("6a3a1583752ec84c2eeb8d48"),
    #Prambors Fm
    ObjectId("6a3a1583752ec84c2eeb8d49"),
    #RRI PRO
    ObjectId("6a3a1583752ec84c2eeb8d4a"),
    #RRI PRO 1
    ObjectId("6a3a1583752ec84c2eeb8d4b"),
    #RRI PRO 1 Banten
    ObjectId("6a3a1583752ec84c2eeb8d4c"),
    #RRI PRO 2
    ObjectId("6a3a1583752ec84c2eeb8d4d"),
    #RRI PRO 4
    ObjectId("6a3a1583752ec84c2eeb8d4e")
]

# List of channel_id (ObjectId or string hex) for main_2.py
CHANNELS_2: List[ObjectId] = [
    # Masukkan channel_id untuk main_2.py di sini
    #Smart FM Jakarta
    ObjectId("6a3a1583752ec84c2eeb8d4f"),
    #Sonora FM
    ObjectId("6a3a1583752ec84c2eeb8d50"),
    #Suara Surabaya FM
    ObjectId("6a3a1583752ec84c2eeb8d51"),
    #Istana FM
    ObjectId("6a420dc00ed952de6e543e09"),
    #Radio DMS FM
    ObjectId("6a4214c50ed952de6e543e0b"),
    #RRI PRO 1 Ende
    ObjectId("6a4217210ed952de6e543e0d"),
    #RRI PRO 1 Kupang
    ObjectId("6a4218500ed952de6e543e0f"),
    #RRI PRO 1 Merauke
    ObjectId("6a4219030ed952de6e543e11"),
    #RRI PRO 1 Nabire
    ObjectId("6a4219960ed952de6e543e13"),
    #RRI PRO 1 Palu
    ObjectId("6a421a150ed952de6e543e15"),
    #RRI PRO 1 Pontianak
    ObjectId("6a421a720ed952de6e543e17"),
    #RRI PRO 1 Samarinda
    ObjectId("6a421b670ed952de6e543e19"),
    #RRI PRO 1 Serui
    ObjectId("6a421bd10ed952de6e543e1b")
]

