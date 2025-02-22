import logging


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)-26s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
