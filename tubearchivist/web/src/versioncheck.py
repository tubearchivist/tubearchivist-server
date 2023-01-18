"""increment and archive version check requests"""

from datetime import datetime

from src.db import DatabaseConnect
from src.ta_redis import RedisBase
from src.webhook_github import GithubBackup


class VersionCheckCounter(RedisBase):
    """count requests to version check API endpoint"""

    KEY_BASE = f"{RedisBase.NAME_SPACE}versioncounter"
    TABLE = "ta_version_stats"

    def __init__(self):
        super().__init__()
        self.timestamp = datetime.now().strftime("%Y%m%d")
        self.key = f"{self.KEY_BASE}:{self.timestamp}"
        self.query = False

    def increase(self):
        """increase counter by one"""
        self.conn.execute_command("INCR", self.key)

    def archive(self):
        """archive past counters to pg"""
        counters = self.conn.execute_command("KEYS", f"{self.KEY_BASE}:*")
        archive_keys = [i.decode() for i in counters if i.decode() != self.key]
        archive_keys.sort()
        if not archive_keys:
            print("no new version keys to archive")
            return

        for archive_key in archive_keys:
            self._build_query(archive_key)
            self._insert_line()
            self._delete_key(archive_key)

    def _build_query(self, archive_key):
        """store single archive key in pg"""
        stats = {
            "ping_date": archive_key.lstrip(self.KEY_BASE),
            "ping_count": self._get_count(archive_key),
            "latest_version": self._get_latest_version(),
        }
        keys = stats.keys()
        values = tuple(stats.values())
        keys_str = ", ".join(keys)
        valid = ", ".join(["%s" for i in keys])
        self.query = (
            f"INSERT INTO {self.TABLE} ({keys_str}) VALUES ({valid});", values
        )

    def _get_count(self, archive_key):
        """get count from redis"""
        result = self.conn.execute_command("GET", archive_key)
        return int(result.decode())

    def _get_latest_version(self):
        """get semantic release of latest"""
        latest = GithubBackup("latest").get_tag().get("release_version")
        return latest

    def _insert_line(self):
        """add line to postgres"""
        handler = DatabaseConnect()
        handler.db_execute(self.query)
        handler.db_close()

    def _delete_key(self, archive_key):
        """delete archived key from redis"""
        self.conn.execute_command("DEL", archive_key)


def run_version_check_archive():
    """daily task to store version check stats"""
    VersionCheckCounter().archive()
