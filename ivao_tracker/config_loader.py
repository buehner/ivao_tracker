import tomllib


class _Config:
    def __init__(self):
        print("Loading config")
        with open("config.toml", mode="rb") as cfg:
            self.config = tomllib.load(cfg)

    def __getattr__(self, name):
        try:
            return self.config[name]
        except KeyError:
            return getattr(self.args, name)


config = _Config()
