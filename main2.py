from datetime import datetime, timedelta
from threading import Thread
from time import sleep
from modules.engine import Engine
from modules.model import STTModel
import nvidia_smi
import logging
import sys
import faulthandler
import torch
import warnings
from dotenv import load_dotenv

nvidia_smi.nvmlInit()

faulthandler.enable()

warnings.filterwarnings("ignore")
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
load_dotenv()




def run(engine: Engine):
    while True:
        froom = datetime.now() - timedelta(days=3)
        now = datetime.now() - timedelta(hours=1)
        try:
            engine.run_timestamps(start_date=froom.strftime("%Y-%m-%d %H:%M:%S"), end_date=now.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            print(e)
        sleep(60)


CHANNELS = [
            1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 21, 22
        ]

if __name__ == '__main__':
    handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
    info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
    memory_in_gb = info.free / 1000_000_000

    if memory_in_gb < 5:
        logging.info(("Memory < ", 5, "Exiting...", (memory_in_gb)))
        sys.exit(0)

    length = len(CHANNELS)
    half = length // 2

    model = STTModel(model_name='large-v3-turbo')

    engines = []

    print(half)
    for chan in CHANNELS[half:]:
        engine = Engine(channel_id=chan)
        engine.set_model(model)

        engines.append(engine)
    
    threads = []

    for engine in engines:
       thread = Thread(target=run, args=(engine,)) 
       thread.start()
       threads.append(thread)

    for thread in threads:
        thread.join()
        


