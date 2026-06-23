from datetime import datetime, timedelta
from threading import Thread
from time import sleep
from modules.engine import Engine
from modules.model import STTModel
import logging
import faulthandler
import torch
import warnings
import sys
import traceback
import os
from dotenv import load_dotenv

from modules.telegram_alert import send_telegram_alert

faulthandler.enable()

warnings.filterwarnings("ignore")

if torch.cuda.is_available():
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

load_dotenv()

# ==========================================
# Logging
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

def custom_excepthook(exc_type, exc_value, exc_traceback):
    """Menangkap unhandled exception secara global untuk dikirim ke Telegram."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error(f"Uncaught exception: {error_msg}")
    send_telegram_alert(f"💥 *CRASH DETECTED!*\n\nError details:\n`{error_msg[-3000:]}`")

sys.excepthook = custom_excepthook

# ==========================================
# Configuration
# ==========================================

USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"

GPU_MODEL        = os.getenv("GPU_MODEL", "large-v3-turbo")
GPU_COMPUTE_TYPE = os.getenv("GPU_COMPUTE_TYPE", "float16")

CPU_MODEL        = os.getenv("CPU_MODEL", "small")
CPU_COMPUTE_TYPE = os.getenv("CPU_COMPUTE_TYPE", "int8")

MIN_GPU_MEMORY_GB = float(os.getenv("MIN_GPU_MEMORY_GB", "5"))

# ==========================================
# GPU Detection
# ==========================================

GPU_READY = False

if USE_GPU:
    if torch.cuda.is_available():
        try:
            # pyrefly: ignore [missing-import]
            import nvidia_smi

            nvidia_smi.nvmlInit()

            handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
            info   = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)

            memory_in_gb = info.free / 1_000_000_000

            if memory_in_gb >= MIN_GPU_MEMORY_GB:
                GPU_READY = True
                print(f"GPU detected. Free VRAM: {memory_in_gb:.2f} GB")
            else:
                print(
                    f"GPU detected but VRAM insufficient "
                    f"({memory_in_gb:.2f} GB < {MIN_GPU_MEMORY_GB} GB). "
                    f"Using CPU."
                )

        except Exception as e:
            print(f"Failed to initialize NVIDIA GPU: {e}")
            print("Using CPU.")
    else:
        print("CUDA not available. Using CPU.")
else:
    print("GPU disabled via .env")

# ==========================================
# Worker
# ==========================================

def run(engine: Engine):
    """Loop utama per channel: ambil audio PENDING 3 hari ke belakang, transkrip, ulangi tiap 60 detik."""
    while True:
        start = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        end   = (datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")

        try:
            engine.run_timestamps(start_date=start, end_date=end)
        except Exception as e:
            error_trace = traceback.format_exc()
            logging.exception(e)
            send_telegram_alert(f"⚠️ *Error di loop Engine*\n\n`{error_trace[-3000:]}`")

        sleep(10)

# ==========================================
# Channels
# ==========================================

from constants.channels import CHANNELS

# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    logging.info(f"Channel yang akan diproses: {CHANNELS}")

    if not CHANNELS:
        logging.error(
            "Tidak ada channel ditemukan. Pastikan koleksi 'streams' di MongoDB berisi data."
        )
        exit(1)

    half = len(CHANNELS) // 2 or len(CHANNELS)

    if GPU_READY:
        print(f"Loading GPU model ({GPU_MODEL}, {GPU_COMPUTE_TYPE})")
        model = STTModel(
            model_name=GPU_MODEL,
            device="cuda",
            compute_type=GPU_COMPUTE_TYPE
        )
    else:
        print(f"Loading CPU model ({CPU_MODEL}, {CPU_COMPUTE_TYPE})")
        model = STTModel(
            model_name=CPU_MODEL,
            device="cpu",
            compute_type=CPU_COMPUTE_TYPE
        )

    engines = []

    for chan in CHANNELS[0:half]:
        engine = Engine(scrapper_name=chan)
        engine.set_model(model)
        engines.append(engine)

    threads = []

    for engine in engines:
        thread = Thread(
            target=run,
            args=(engine,),
            daemon=True  # supaya thread ikut mati saat program keluar
        )
        thread.start()
        threads.append(thread)

    try:
        while True:
            sleep(1)

    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt diterima. Menghentikan aplikasi...")