import argparse
from typing import List
from faster_whisper.utils import _MODELS

from modules.model import STTModel, Union
from time import time
import itertools
import traceback
import threading
import pydub
import numpy as np
import warnings
import torch

warnings.filterwarnings("ignore")
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

class Counter:
    def __init__(self):
        self._incs = itertools.count()
        self._accesses = itertools.count()

    def increment(self):
        next(self._incs)

    def value(self):
        return next(self._incs) - next(self._accesses)

thread_result_counter = Counter()
start_time = None
def get_args():
    parser = argparse.ArgumentParser(
                prog='Stress Test',
                description='Stress testing harware in STT Task with Whisper'
            )

    parser.add_argument('-m', '--model', default='large-v3-turbo', type=str, choices=list(_MODELS.keys()), help='Model used in test')
    parser.add_argument('-t', '--threads', default=8, type=int, help='Engine Threads Count')
    parser.add_argument('-w', '--worker', default=2, type=int, help='Model Workers Count')
    parser.add_argument('-a', '--audio', default='/home/stt/RAW-RADIO/rripro4/rripro4_03-06-07-15-38.mp3', type=str, help="Audio to transcribe")
    parser.add_argument('-n', '--number', default=2, type=int, help='Test N')
    args = parser.parse_args()
    return args

def work(thread_num: int, model: STTModel, audio: Union[np.ndarray, str], n: int, m: int):
    global thread_result_counter
    c = 0
    while c < n:
        print('THREAD', thread_num, ':', 'TRANSCRIBING with MODEL', m)
        print("TRANSCRIBESTART")
        _ = model.transcribe(audio)
        print("TRANSCRIBEND")
        thread_result_counter.increment()
        c += 1
        print('THREAD', thread_num, ':', c, 'MODEL', m)

        

class PropagatingThread(threading.Thread):
    def run(self):
        self.exc = None
        try:
            if hasattr(self, '_Thread__target'):
                # Thread uses name mangling prior to Python 3.
                self.ret = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
            else:
                self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self, timeout=None):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
        return self.ret
def main():
    global start_time
    args = get_args()
    THREAD_COUNT = args.threads
    MODEL_NAME = args.model
    WORKER_COUNT = args.worker
    AUDIO = args.audio
    N = args.number
    WORKERS: List[STTModel] = []
    THREADS: List[PropagatingThread] = []
    for i in range(WORKER_COUNT):
        model = STTModel(model_name=MODEL_NAME)
        WORKERS.append(model)

    model_flag = 0
    print("Getting Audio")
    segments = pydub.AudioSegment.from_mp3(AUDIO)
    print("Got Audio")

    #Preprocess to prepare audio before fed into whisper
    if segments.frame_rate != 16_000:
        segments = segments.set_frame_rate(16_000)
    if segments.sample_width != 2:
        segments = segments.set_sample_width(2)
    if segments.channels != 1:
        segments = segments.set_channels(1)
    arr = np.array(segments.get_array_of_samples())
    arr = arr.astype(np.float32) / 32_768.0

    start_time = time()
    print("MAKING THREAD")
    for i in range(THREAD_COUNT):
        thread = PropagatingThread(target=work, args=(i, WORKERS[model_flag], arr, N, model_flag))
        model_flag += 1
        model_flag %= WORKER_COUNT
        THREADS.append(thread)
        print("THREAD", i, "RUNNING")
        thread.start()

    for thread in THREADS:
        thread.join()


    

if __name__  == '__main__':
    try:
        print("asda")
        main()
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        print("Test Aborted.")
    finally:
        end_time = time()
        print("Program Running for:", (end_time - start_time), "seconds")
        print("Total Transcribed:", thread_result_counter.value())


