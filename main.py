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
# Worker
# ==========================================


def run(engine: Engine):
    """
    Worker utama.
    Mengambil audio PENDING dalam rentang waktu
    kemudian melakukan transkripsi.
    """

    while True:

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
            )

        except Exception:

            error_trace = traceback.format_exc()

            logging.exception(error_trace)

            send_telegram_alert(
                f"⚠️ *Error pada Engine*\n\n```{error_trace[-3000:]}```"
            )

        sleep(10)


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    GPU_CONCURRENT_LIMIT = int(os.getenv("GPU_CONCURRENT_LIMIT", "1"))

    if GPU_READY:

        logging.info(
            f"Loading GPU model ({GPU_MODEL}) with concurrent limit {GPU_CONCURRENT_LIMIT}"
        )

        model = STTModel(
            model_name=GPU_MODEL,
            device="cuda",
            compute_type=GPU_COMPUTE_TYPE,
            concurrent_limit=GPU_CONCURRENT_LIMIT,
        )

    else:

        logging.info(
            f"Loading CPU model ({CPU_MODEL})"
        )

        model = STTModel(
            model_name=CPU_MODEL,
            device="cpu",
            compute_type=CPU_COMPUTE_TYPE,
            concurrent_limit=1,
        )

    engine = Engine()
    engine.set_model(model)

    worker = Thread(
        target=run,
        args=(engine,),
        daemon=True,
    )

    worker.start()

    logging.info("Engine STT berhasil dijalankan.")

    try:

        while True:
            sleep(1)

    except KeyboardInterrupt:

        logging.info("Menghentikan Engine...")