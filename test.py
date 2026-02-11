from datetime import datetime
import sys
from modules.engine import Engine
import os
from modules.model import STTModel
import warnings
from dotenv import load_dotenv
import faulthandler
import torch
import whisperx

faulthandler.enable()

warnings.filterwarnings("ignore")
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
load_dotenv()

device = "cuda" 
batch_size = 16 # reduce if low on GPU mem
compute_type = "float16" # change to "int8" if low on GPU mem (may reduce accuracy)
model = whisperx.load_model("large-v3-turbo", device=device, compute_type=compute_type)


# # rr1Thread = threading.Thread(target= run, args=("RRI Pro 1", "/home/stt/RAW-RADIO/rripro1"))
#
# # rr1Thread.start()
# # rr1Thread.join()
_audio = whisperx.load_audio('audio/lms.mp3')
result = model.transcribe(_audio, batch_size=batch_size, language='id')

print(result)
#
# result = ''.join([r['text'] for r in result['segments']])
# SaveResults(result, "andini", "andini", datetime.now())
#
#
# if __name__ == '__main__':
#     print("PID: ", os.getpid())
#     model = STTModel(model_name='large-v3-turbo')
#     engine = Engine(channel_id=8, model=model)
#     froom = datetime(year=2025, month=1, day=1)
#     now = datetime.now()
#     engine.run_timestamps(start_date=froom.strftime("%Y-%m-%d"), end_date=now.strftime("%Y-%m-%d"))


# threads = []
# engines = []
# for chan in channels.values():
#     engines.append(Engine(channel_id=chan.id))
#
# for en in engines:
#     thread = threading.Thread(target=en)
#
