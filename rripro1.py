from datetime import datetime, timedelta
import logging
import sys
from threading import Thread
from typing import List
from modules.engine import Engine
import os
from modules.model import STTModel
import warnings
from dotenv import load_dotenv
import faulthandler
import torch
import nvidia_smi

nvidia_smi.nvmlInit()

faulthandler.enable()

warnings.filterwarnings("ignore")
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
load_dotenv()

# device = "cuda" 
# batch_size = 16 # reduce if low on GPU mem
# compute_type = "float16" # change to "int8" if low on GPU mem (may reduce accuracy)
# model = whisperx.load_model("large-v2", device='', compute_type=compute_type)


# # rr1Thread = threading.Thread(target= run, args=("RRI Pro 1", "/home/stt/RAW-RADIO/rripro1"))
#
# # rr1Thread.start()
# # rr1Thread.join()
# _audio = whisperx.load_audio('audio/lms.mp3')
# result = model.transcribe(_audio, batch_size=batch_size, language='id')
# result = ''.join([r['text'] for r in result['segments']])
# SaveResults(result, "andini", "andini", datetime.now())
#
#

def work(engine: Engine):
    today = datetime.now() - timedelta(days=1)
    print(today)
    engine.run_timestamps(start_date=today.strftime("%Y-%m-%d %H:%M:%S"), end_date=today.strftime("%Y-%m-%d %H:%M:%S"))
if __name__ == '__main__':

    handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
    info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
    memory_in_gb = info.free / 1000_000_000

    if memory_in_gb < 5:
        logging.info(("Memory < ", 5, "Exiting...", (memory_in_gb)))
        sys.exit(0)

    print("PID: ", os.getpid())
    # model = STTModel(model_name='large-v3')
    # channels = [8, 11]
    # engines: List[Engine] = []
    # for c in channels:
    #     print("Engines for channel", c)
    #     engine = Engine(model=model, channel_id=c)
    #     engines.append(engine)
    #
    # threads: List[Thread] = []
    # for e in engines:
    #     thread = Thread(target=work, args=(e,))
    #     threads.append(thread)
    #     thread.start()
    #
    # for t in threads:
    #     t.join()
    engine = Engine(channel_id=7)

    froom = datetime.now() - timedelta(days=30)
    now = datetime.now() - timedelta(hours=1)
    if not engine.check_audio_exist(start_date=froom.strftime("%Y-%m-%d %H:%M:%S"), end_date=now.strftime("%Y-%m-%d %H:%M:%S")):
        sys.exit(0)


    model = STTModel(model_name='large-v3-turbo')
    engine.set_model(model)
    engine.run_timestamps(start_date=froom.strftime("%Y-%m-%d %H:%M:%S"), end_date=now.strftime("%Y-%m-%d %H:%M:%S"))


    sys.exit(0)


# threads = []
# engines = []
# for chan in channels.values():
#     engines.append(Engine(channel_id=chan.id))
#
# for en in engines:
#     thread = threading.Thread(target=en)
#
