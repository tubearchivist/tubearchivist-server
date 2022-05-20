"""handle release functionality"""

import base64
import json
from datetime import datetime
from hashlib import sha256
from hmac import HMAC, compare_digest
import requests
import redis

from src.db import DatabaseConnect
from src.webhook_base import WebhookBase


class GithubHook(WebhookBase):
    """process hooks from github"""

    def __init__(self, request):
        self.request = request
        self.hook = False
        self.repo = False
        self.repo_conf = False

    def validate(self):
        """make sure hook is legit"""
        sig = self.request.headers.get("X-Hub-Signature-256")
        if not sig:
            return False

        received = sig.split("sha256=")[-1].strip()
        print(f"received: {received}")
        secret = self.GH_HOOK_SECRET.encode()
        msg = self.request.data
        expected = HMAC(key=secret, msg=msg, digestmod=sha256).hexdigest()
        print(f"expected: {expected}")
        return compare_digest(received, expected)

    def create_hook_task(self):
        """check what task is required"""
        self.hook = self.request.json
        self.repo = self.hook["repository"]["name"]

        if self.repo not in self.HOOK_MAP:
            print(f"repo {self.repo} not registered")
            return False

        self.repo_conf = self.HOOK_MAP[self.repo]
        if "ref" in self.hook:
            # is a commit hook
            self.process_commit_hook()

        if "release" in self.hook:
            # is a release hook
            self.process_release_hook()

        return False

    def process_commit_hook(self):
        """process commit hook after validation"""
        on_master = self.check_branch()
        if not on_master:
            print("commit not on master")
            return

        self._check_roadmap()

        build_message = self.check_commit_message()
        if not build_message:
            print("build keyword not found in commit message")
            return

        self.repo = self.hook["repository"]["name"]
        TaskHandler(self.repo_conf).create_task("build_unstable")

    def check_branch(self):
        """check if commit on master branch"""
        master_branch = self.hook["repository"]["master_branch"]
        ref = self.hook["ref"]

        return ref.endswith(master_branch)

    def check_commit_message(self):
        """check if keyword in commit message is there"""
        message = self.hook["head_commit"]["message"]
        return message.endswith(self.repo_conf["unstable_keyword"])

    def _check_roadmap(self):
        """check if roadmap update needed"""
        modified = [i["modified"] for i in self.hook["commits"]]
        for i in modified:
            if "README.md" in i:
                print("README updated, check roadmap")
                RoadmapHook(self.repo_conf, self.ROADMAP_HOOK_URL).update()
                break

    def process_release_hook(self):
        """build and process for new release"""
        if self.hook["action"] != "released":
            return

        tag_name = self.hook["release"]["tag_name"]
        task = TaskHandler(self.repo_conf, tag_name=tag_name)
        task.create_task("build_release")
        GithubBackup(tag_name).save_tag()


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

    def __init__(self, repo_conf, hook_url):
        self.repo_conf = repo_conf
        self.hook_url = hook_url
        self.roadmap_raw = False
        self.implemented = False
        self.pending = False

    def update(self):
        """update message"""
        pending_old, implemented_old, message_id = self.get_last_roadmap()
        self.get_new_roadmap()
        self.parse_roadmap()
        if pending_old == self.pending and implemented_old == self.implemented:
            print("roadmap did not change")
            return

        if message_id:
            self.delete_webhook(message_id)

        last_id = self.send_message()
        self.update_roadmap(last_id)

    @staticmethod
    def get_last_roadmap():
        """get last entry in db to comapre agains"""
        query = "SELECT * FROM ta_roadmap ORDER BY time_stamp DESC LIMIT 1;"
        handler = DatabaseConnect()
        rows = handler.db_execute(query)
        handler.db_close()

        try:
            pending = [i.get("pending") for i in rows][0]
            implemented = [i.get("implemented") for i in rows][0]
            last_id = [i.get("last_id") for i in rows][0]
        except IndexError:
            pending, implemented, last_id = False, False, False

        return pending, implemented, last_id

    def get_new_roadmap(self):
        """get current roadmap"""
        user = self.repo_conf.get("gh_user")
        repo = self.repo_conf.get("gh_repo")
        url = f"https://api.github.com/repos/{user}/{repo}/contents/README.md"
        response = requests.get(url).json()
        content = base64.b64decode(response["content"]).decode()
        paragraphs = [i.strip() for i in content.split("##")]
        for paragraph in paragraphs:
            if paragraph.startswith("Roadmap"):
                roadmap_raw = paragraph
                break
        else:
            roadmap_raw = False

        self.roadmap_raw = roadmap_raw

    def parse_roadmap(self):
        """extract relevant information"""
        pending_items = []
        implemented_items = []
        for line in self.roadmap_raw.split("\n"):
            if line.startswith("- [ ] "):
                pending_items.append(line.replace("[ ] ", ""))
            if line.startswith("- [X] "):
                implemented_items.append(line.replace("[X] ", ""))

        self.pending = "\n".join(pending_items)
        self.implemented = "\n".join(implemented_items)

    def delete_webhook(self, message_id):
        """delete old message"""
        url = f"{self.hook_url}/messages/{message_id}"
        response = requests.delete(url)
        print(response)

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
        response = requests.post(f"{self.hook_url}?wait=true", json=data)
        print(response)
        print(response.text)

        return response.json()["id"]

    def update_roadmap(self, last_id):
        """update new roadmap in db"""
        ingest_line = {
            "time_stamp": int(datetime.now().strftime("%s")),
            "time_stamp_human": datetime.now().strftime("%Y-%m-%d"),
            "last_id": last_id,
            "implemented": self.implemented,
            "pending": self.pending,
        }
        keys = ingest_line.keys()
        values = tuple(ingest_line.values())
        keys_str = ", ".join(keys)
        valid = ", ".join(["%s" for i in keys])
        query = (
            f"INSERT INTO ta_roadmap ({keys_str}) VALUES ({valid});", values
        )
        handler = DatabaseConnect()
        _ = handler.db_execute(query)
        handler.db_close()


class RedisBase:
    """connection base for redis"""

    REDIS_HOST = "redis"
    REDIS_PORT = 6379
    NAME_SPACE = "ta:"

    def __init__(self):
        self.conn = redis.Redis(host=self.REDIS_HOST, port=self.REDIS_PORT)


class TaskHandler(RedisBase):
    """handle buildx task queue"""

    def __init__(self, repo_conf, tag_name=False):
        super().__init__()
        self.key = self.NAME_SPACE + "task:buildx"
        self.repo_conf = repo_conf
        self.tag_name = tag_name

    def create_task(self, task_name):
        """create task"""
        self.create_queue()
        self.set_task(task_name)
        self.set_pub()

    def create_queue(self):
        """set initial json object for queue"""
        if self.conn.execute_command(f"EXISTS {self.key}"):
            print(f"{self.key} already exists")
            return

        message = {
            "created": int(datetime.now().strftime("%s")),
            "tasks": {}
        }
        self.conn.execute_command(
            "JSON.SET", self.key, ".", json.dumps(message)
        )

    def set_task(self, task_name):
        """publish new task to queue"""

        user = self.repo_conf.get("gh_user")
        repo = self.repo_conf.get("gh_repo")
        build_command = self.build_command(task_name)
        task = {
            "timestamp": int(datetime.now().strftime("%s")),
            "clone": f"https://github.com/{user}/{repo}.git",
            "name": self.repo_conf.get("gh_repo"),
            "build": build_command,
        }

        self.conn.json().set(self.key, f".tasks.{repo}", task)

    def build_command(self, task_name):
        """return build command"""
        if not self.tag_name:
            return self.repo_conf.get(task_name)

        command = self.repo_conf.get(task_name)
        for idx, command_part in enumerate(command):
            if "$VERSION" in command_part:
                subed = command_part.replace("$VERSION", self.tag_name)
                command[idx] = subed

        return command

    def set_pub(self):
        """set message to pub"""
        self.conn.publish(self.key, self.repo_conf.get("gh_repo"))
