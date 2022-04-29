"""hourly docker stats backup"""


from datetime import datetime
from src.db import DatabaseConnect

import requests


class DockerBackup:
    """handle docker backup and storage"""

    URL = "https://hub.docker.com/v2/repositories/bbilly1/tubearchivist/"
    TABLE = "ta_docker_stats"

    def __init__(self):
        self.image_stats = False
        self.query = False

    def run_backup(self):
        """public method to run"""
        self._get_image_stats()
        self._build_query()
        self._insert_line()

    def _get_image_stats(self):
        """return dict for image"""
        response = requests.get(self.URL).json()
        now = datetime.now()

        last_updated = response["last_updated"]
        updated = datetime.fromisoformat(last_updated.split(".")[0])

        image_stats = {
            "time_stamp": int(now.strftime("%s")),
            "time_stamp_human": now.strftime("%Y-%m-%d %H:%M"),
            "last_updated": int(updated.strftime("%s")),
            "last_updated_human": updated.strftime("%Y-%m-%d %H:%M"),
            "stars": response["star_count"],
            "pulls": response["pull_count"]
        }

        self.image_stats = image_stats

    def _build_query(self):
        """build ingest query for postgres"""
        keys = self.image_stats.keys()
        values = tuple(self.image_stats.values())
        keys_str = ", ".join(keys)
        valid = ", ".join(["%s" for i in keys])
        query = (
            f"INSERT INTO {self.TABLE} ({keys_str}) VALUES ({valid});", values
        )
        self.query = query

    def _insert_line(self):
        """add line to postgres"""
        handler = DatabaseConnect()
        handler.db_execute(self.query)
        handler.db_close()
