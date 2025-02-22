import logging
import tomllib

from ivao_tracker.logger.config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class _Config:
    def __init__(self):
        logger.info("Loading config")
        with open("config.toml", mode="rb") as cfg:
            self.config = tomllib.load(cfg)

    def __getattr__(self, name):
        try:
            return self.config[name]
        except KeyError:
            return getattr(self.args, name)


config = _Config()
