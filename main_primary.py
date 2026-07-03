from datetime import datetime, timedelta
from threading import Thread
from time import sleep
from modules.engine import Engine
from modules.model import STTModel
from bson import ObjectId
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
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def custom_excepthook(exc_type, exc_value, exc_traceback):
    """Menangkap unhandled exception secara global untuk dikirim ke Telegram."""

    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback)
    )

    logging.error(error_msg)

    send_telegram_alert(
        f"💥 *CRASH DETECTED!*\n\n```{error_msg[-3000:]}```"
    )


sys.excepthook = custom_excepthook

# ==========================================
# Configuration
# ==========================================

USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"

GPU_MODEL = os.getenv("GPU_MODEL", "large-v3-turbo")
GPU_COMPUTE_TYPE = os.getenv("GPU_COMPUTE_TYPE", "float16")

CPU_MODEL = os.getenv("CPU_MODEL", "small")
CPU_COMPUTE_TYPE = os.getenv("CPU_COMPUTE_TYPE", "int8")

MIN_GPU_MEMORY_GB = float(
    os.getenv("MIN_GPU_MEMORY_GB", "5")
)

# ==========================================
# GPU Detection
# ==========================================

GPU_READY = False

if USE_GPU:

    if torch.cuda.is_available():

        try:
            import nvidia_smi

            nvidia_smi.nvmlInit()

            handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
            info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)

            free_memory = info.free / 1_000_000_000

            if free_memory >= MIN_GPU_MEMORY_GB:
                GPU_READY = True
                logging.info(
                    f"GPU detected. Free VRAM: {free_memory:.2f} GB"
                )
            else:
                logging.warning(
                    f"GPU detected but only "
                    f"{free_memory:.2f} GB free. "
                    f"Using CPU."
                )

        except Exception as e:
            logging.warning(f"GPU initialization failed: {e}")
            logging.warning("Using CPU.")

    else:
        logging.info("CUDA not available. Using CPU.")

else:
    logging.info("GPU disabled from .env")


# ==========================================
# Helper to Load Channel IDs
# ==========================================

def load_channel_ids_from_module(channels_key: str) -> list:
    """
    Membaca daftar channel_id (ObjectId) dari constants/channels.py secara dinamis.
    Melakukan reload module agar perubahan file langsung terdeteksi tanpa restart.
    """
    import importlib
    import constants.channels

    try:
        importlib.reload(constants.channels)
        channel_ids = getattr(constants.channels, channels_key, None)
        if channel_ids is None:
            logging.warning(f"Key {channels_key} tidak ditemukan di constants/channels.py. Memproses semua channel.")
            return None

        # Konversi string hex menjadi ObjectId jika diperlukan, dan pastikan tipe valid
        converted = []
        for cid in channel_ids:
            if isinstance(cid, ObjectId):
                converted.append(cid)
            elif isinstance(cid, str):
                try:
                    converted.append(ObjectId(cid.strip()))
                except Exception:
                    logging.error(f"Format ObjectId tidak valid: {cid}")
            else:
                logging.error(f"Tipe data channel_id tidak valid: {type(cid)}")

        logging.info(f"Loaded {len(converted)} channel_id dari constants.channels.{channels_key}: {converted}")
        return converted
    except Exception as e:
        logging.error(f"Gagal memuat channel dari constants/channels.py: {e}")
        return None


# ==========================================
# Worker
# ==========================================

def run(engine: Engine, channels_key: str):
    """
    Worker utama.
    Mengambil audio PENDING dalam rentang waktu yang di-filter berdasarkan channel_ids
    kemudian melakukan transkripsi.
    """

    while True:
        # Load ulang channel_ids setiap iterasi agar fleksibel jika file diedit tanpa restart
        channel_ids = load_channel_ids_from_module(channels_key)

        start = (
            datetime.now() - timedelta(days=1)
        ).strftime("%Y-%m-%d %H:%M:%S")

        end = (
            datetime.now() - timedelta(hours=1)
        ).strftime("%Y-%m-%d %H:%M:%S")

        try:
            engine.run_timestamps(
                start_date=start,
                end_date=end,
                channel_ids=channel_ids,
            )

        except Exception:

            error_trace = traceback.format_exc()

            logging.exception(error_trace)

            send_telegram_alert(
                f"⚠️ *Error pada Engine ({channels_key})*\n\n```{error_trace[-3000:]}```"
            )

        sleep(10)


# ==========================================
# Start Engine Wrapper
# ==========================================

def start_engine(channels_key: str):
    """
    Menginisialisasi model dan menjalankan worker STT Engine.
    """
    logging.info(f"Starting engine instance with config key: {channels_key}")

    if GPU_READY:
        logging.info(
            f"Loading GPU model ({GPU_MODEL})"
        )
        model = STTModel(
            model_name=GPU_MODEL,
            device="cuda",
            compute_type=GPU_COMPUTE_TYPE,
        )
    else:
        logging.info(
            f"Loading CPU model ({CPU_MODEL})"
        )
        model = STTModel(
            model_name=CPU_MODEL,
            device="cpu",
            compute_type=CPU_COMPUTE_TYPE,
        )

    engine = Engine()
    engine.set_model(model)

    worker = Thread(
        target=run,
        args=(engine, channels_key),
        daemon=True,
    )

    worker.start()

    logging.info(f"Engine STT ({channels_key}) berhasil dijalankan.")

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        logging.info(f"Menghentikan Engine ({channels_key})...")


if __name__ == "__main__":
    start_engine("CHANNELS_1")