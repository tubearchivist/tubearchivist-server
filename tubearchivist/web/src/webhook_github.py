"""handle release functionality"""

from datetime import datetime
from os import environ
import requests

from src.db import DatabaseConnect



class GithubBackup:
    """backup release and notes"""

    URL = "https://api.github.com/repos/bbilly1/tubearchivist/releases/tags/"
    TABLE = "ta_release"

    def __init__(self, tag):
        self.tag = tag
        self.ingest_line = False
        self.query = False

    def save_tag(self):
        """save release tag in db"""
        self.ingest_build_line()
        self.reset_latest()
        _ = self.db_execute()
        self._build_ingest_query()
        _ = self.db_execute()

    def get_tag(self):
        """get tag dict"""
        self.build_get_query()
        rows = self.db_execute()
        result = dict(rows[0])
        return result

    def ingest_build_line(self):
        """ingest latest release into postgres"""
        response = requests.get(self.URL + self.tag)
        if not response.ok:
            print(response.text)
            raise ValueError

        response_json = response.json()

        if isinstance(response_json, list):
            last_release = response.json()[0]
        elif isinstance(response_json, dict):
            last_release = response.json()

        published_at = last_release["published_at"]
        published = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        release_notes = last_release["body"]
        head = release_notes.split("\r\n")[0].lower()
        breaking_changes = "manual changes" in head or "breaking changes" in head

        ingest_line = {
            "time_stamp": int(published.strftime("%s")),
            "time_stamp_human": published.strftime("%Y-%m-%d"),
            "release_version": last_release["tag_name"],
            "release_is_latest": True,
            "breaking_changes": breaking_changes,
            "release_notes": release_notes,
        }
        self.ingest_line = ingest_line

    def _build_ingest_query(self):
        """build ingest query for postgres"""
        keys = self.ingest_line.keys()
        values = tuple(self.ingest_line.values())
        keys_str = ", ".join(keys)
        valid = ", ".join(["%s" for i in keys])
        query = (
            f"INSERT INTO {self.TABLE} ({keys_str}) VALUES ({valid});", values
        )
        self.query = query

    def reset_latest(self):
        """unset latest tag of now old version"""
        self.query = (
            f"UPDATE {self.TABLE} SET release_is_latest = %s;", (False,)
        )

    def db_execute(self):
        """add line to postgres"""
        handler = DatabaseConnect()
        rows = handler.db_execute(self.query)
        handler.db_close()
        return rows

    def build_get_query(self):
        """get release dict from db"""
        if self.tag == "latest":
            query = (
                f"SELECT * FROM {self.TABLE} " +
                "WHERE release_is_latest = True " +
                "LIMIT 1;"
            )
        else:
            query = (
                f"SELECT * FROM {self.TABLE} " +
                f"WHERE release_version = '{self.tag}' " +
                "LIMIT 1;"
            )
        self.query = query


class RoadmapHook:
    """update roadmap"""

    README = "https://raw.githubusercontent.com/bbilly1/tubearchivist/master/README.md"
    HOOK_URL = environ.get("ROADMAP_HOOK_URL")

    def __init__(self):
        self.roadmap_raw = False
        self.implemented = False
        self.pending = False

    def update(self):
        """update message"""
        self.get_roadmap()
        self.parse_roadmap()
        self.send_message()

    def get_roadmap(self):
        """get current roadmap"""
        response = requests.get(self.README)
        paragraphs = [i.strip() for i in response.text.split("##")]
        for paragraph in paragraphs:
            if paragraph.startswith("Roadmap"):
                roadmap_raw = paragraph
                break
        else:
            roadmap_raw = False

        self.roadmap_raw = roadmap_raw

    def parse_roadmap(self):
        """extract relevant information"""
        _, pending, implemented = self.roadmap_raw.split("\n\n")
        implemented = implemented.lstrip("Implemented:\n")
        self.implemented = implemented.replace("[X] ", "")
        self.pending = pending.replace("[ ]", "")

    def send_message(self):
        """build message dict"""
        data = {
            "embeds": [{
                "title": "Upcoming:",
                "description": self.pending,
                "color": 2331524
            }, {
                "title": "Implemented:",
                "description": self.implemented,
                "color": 10555
            }]
        }
        response = requests.post(self.HOOK_URL, json=data)
        print(response)
        print(response.text)
