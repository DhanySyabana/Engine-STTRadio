from dataclasses import dataclass
from typing import Dict


@dataclass
class Radio:
    id: int
    nama: str
    path: str



channels: Dict[int, Radio] = {
    1: Radio(id=1, nama='Smart FM jakarta', path="/home/stt/RAW-RADIO/smartfm"),
    2: Radio(id=2, nama='Elshinta jakarta', path="/home/stt/RAW-RADIO/elshintajkt"),
    3: Radio(id=3, nama='MNC Trijaya', path="/home/stt/RAW-RADIO/mnctrijayajakarta"),
    4: Radio(id=4, nama='RRI PRO', path="/home/stt/RAW-RADIO/rripro"),
    5: Radio(id=5, nama='Sonora', path="/home/stt/RAW-RADIO/sonorajkt"),
    7: Radio(id=7, nama='RRI PRO 1', path="/home/stt/RAW-RADIO/rripro1"),
    8: Radio(id=8, nama='RRI PRO 2', path="/home/stt/RAW-RADIO/rripro2"),
    9: Radio(id=9, nama='RRI PRO 4', path="/home/stt/RAW-RADIO/rripro4"),
    10: Radio(id=10, nama='Pass FM jakarta', path="/home/stt/RAW-RADIO/passfm"),
    11: Radio(id=11, nama='Suara Surabaya', path="/home/stt/RAW-RADIO/suarasurabaya"),
    12: Radio(id=12, nama='Sample', path="/home/stt/RAW-RADIO/"),
    13: Radio(id=13, nama='IRadio', path="/home/stt/RAW-RADIO/iradio"),
    14: Radio(id=14, nama='Prambors', path="/home/stt/RAW-RADIO/prambors"),
    15: Radio(id=15, nama='RRI PRO 1 Banten', path="/home/stt/RAW-RADIO/rripro1banten"),
    16: Radio(id=16, nama='KBR Radio', path="/home/stt/RAW-RADIO/kbr"),
    17: Radio(id=17, nama='GEN FM', path="/home/stt/RAW-RADIO/genfm"),
    18: Radio(id=18, nama='KIS FM', path="/home/stt/RAW-RADIO/kisfm"),
    19: Radio(id=19, nama='Most FM', path="/home/stt/RAW-RADIO/mostfm")
}

