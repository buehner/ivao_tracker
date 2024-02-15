from sqlmodel import SQLModel, create_engine

from ivao_tracker.config_loader import config


def get_db_url():
    db_cfg = config.config["db"]
    db_user = db_cfg["username"]
    db_host = db_cfg["host"]
    db_pass = db_cfg["password"]
    db_port = db_cfg["port"]
    db_database = db_cfg["database"]

    return "postgresql://{:s}:{:s}@{:s}:{:d}/{:s}".format(
        db_user, db_pass, db_host, db_port, db_database
    )


engine = create_engine(get_db_url(), echo=False)


def create_schema():
    # time.sleep(2)
    SQLModel.metadata.create_all(engine)
