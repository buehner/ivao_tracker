import logging


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)-5s - %(name)-26s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
