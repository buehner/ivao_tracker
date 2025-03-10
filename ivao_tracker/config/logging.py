import logging


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)-7s - %(name)-30s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
