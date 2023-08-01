"""handle release functionality"""

import base64
import json
from datetime import datetime
from hashlib import sha256, md5
from hmac import HMAC, compare_digest
from os import environ

from bs4 import BeautifulSoup
import requests

from src.db import DatabaseConnect
from src.ta_redis import TaskHandler
from src.webhook_base import WebhookBase


HOOK_URL = {
    "tubearchivist/browser-extension": environ.get("GITHUB_COMPANION_HOOK_URL"),
    "tubearchivist/tubearchivist": environ.get("GITHUB_TA_HOOK_URL"),
    "tubearchivist/docs": environ.get("GITHUB_DOCS_URL"),
}


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

        if "pull_request" in self.hook or "issue" in self.hook:
            CommentNotification(self.hook).run()

        return False

    def process_commit_hook(self):
        """process commit hook after validation"""
        on_master = self.check_branch()
        if not on_master:
            print("commit not on master")
            return

        if self.repo in ["docs", "discord-bot"]:
            TaskHandler(self.repo_conf).create_task("rebuild")
            return

        self._check_readme()

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
        first_line = message.split("\n")[0]
        return first_line.endswith(self.repo_conf["unstable_keyword"])

    def _check_readme(self):
        """check readme if roadmap or es update needed"""
        modified = [i["modified"] for i in self.hook["commits"]]
        for i in modified:
            if "README.md" in i:
                print("README updated, check roadmap")
                RoadmapHook(self.repo_conf, self.ROADMAP_HOOK_URL).update()
            if "docker-compose.yml" in i:
                print("docker-compose updated, check es version")
                EsVersionSync(self.repo_conf).run()

    def process_release_hook(self):
        """build and process for new release"""
        if self.hook["action"] != "released":
            return

        tag_name = self.hook["release"]["tag_name"]
        task = TaskHandler(self.repo_conf, tag_name=tag_name)
        task.create_task("build_release")
        GithubBackup(tag_name).save_tag()

    def save_hook(self):
        """save hook to disk for easy debugging"""
        now = datetime.now().strftime("%s")
        filename = f"/data/hooks/github_hook-{now}.json"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.hook))


class CommentNotification:
    """process comment notification hooks"""

    def __init__(self, data):
        self.data = data
        self.type = False
        self.repo = False
        self.color_hash = ""

    def run(self):
        """run all"""
        self.dedect()
        if not self.type:
            print("skip hook run")
            return

        hook_data = self.build_hook_data()
        self.send_hook(hook_data)

    def dedect(self):
        """dedect origin"""
        if "issue" in self.data:
            self._process_issue_hook()
        elif "pull_request" in self.data:
            self._process_pull_request_hook()

        print(self.type)

    def _process_issue_hook(self):
        """process incomming issue message"""
        if self.data["issue"].get("pull_request", False):
            origin = "pull request"
            self.color_hash += "pullrequest"
        else:
            origin = "issue"
            self.color_hash += "issue"

        if self.data["action"] == "opened":
            self.type = f"New {origin} opened"
        elif self.data["action"] == "created":
            self.type = f"New comment on {origin}"
        elif self.data["action"] == "closed":
            self.type = f"Closed {origin}"

    def _process_pull_request_hook(self):
        """send notification about pull requests"""
        self.color_hash += "pullrequest"
        if self.data["action"] == "opened":
            # new pull request
            self.type = "New pull request opened"
        elif self.data["action"] == "closed":
            # pull request is closed
            is_merged = self.data["pull_request"].get("merged_at")
            if is_merged:
                self.type = "Pull request merged"
            else:
                self.type = "Pull request closed"

    def build_hook_data(self):
        """build author object"""
        hook_data = {
            "embeds": [
                {
                    "author": self._parse_author(),
                    "title": self._parse_title(),
                    "url": self._parse_comment_url(),
                    "color": self._get_color(),
                }
            ]
        }
        description = self._prase_description()
        if description:
            hook_data["embeds"][0].update({"description": description})

        return hook_data

    def _parse_author(self):
        """build author dict"""
        return {
            "name": self.data["sender"]["login"],
            "icon_url": self.data["sender"]["avatar_url"],
            "url": self.data["sender"]["html_url"],
        }

    def _parse_title(self):
        """build title"""
        self.repo = self.data["repository"]["full_name"]
        if "issue" in self.data:
            name = self.data["issue"]["title"]
            number = self.data["issue"]["number"]
        elif "pull_request" in self.data:
            name = self.data["pull_request"]["title"]
            number = self.data["pull_request"]["number"]
        else:
            raise ValueError("action not found in data")

        title = f"[{self.repo}] {self.type} #{number}: {name}"
        self.color_hash += f"{self.repo}-{number}"
        return title

    def _parse_comment_url(self):
        """build comment url"""
        if "issue" in self.data:
            html_url = self.data["issue"]["html_url"]
            comment_id = self.data["issue"]["id"]
        else:
            html_url = self.data["pull_request"]["html_url"]
            comment_id = self.data["pull_request"]["id"]

        comment_url = f"{html_url}#issue-{comment_id}"

        return comment_url

    def _prase_description(self):
        """extract text from html description"""
        if "comment" in self.data:
            html = self.data["comment"]["body"]
        elif "issue" in self.data:
            html = self.data["issue"]["body"]
        elif "pull_request" in self.data:
            html = self.data["pull_request"]["body"]
        else:
            print("no description text found")
            return False

        if self.data["action"] == "closed":
            return False

        if not html:
            return "No description provided."

        text = BeautifulSoup(html, features="html.parser").text

        if len(text) >= 500:
            text = text[:500].rsplit(" ", 1)[0] + " ..."

        return text

    def _get_color(self):
        """build color hash"""
        hex_str = md5(self.color_hash.encode("utf-8")).hexdigest()[:6].encode()
        discord_col = int(hex_str, 16)
        return discord_col

    def send_hook(self, hook_data):
        """send hook"""
        url = HOOK_URL.get(self.repo)
        if not url:
            print(f"{self.repo} not found in HOOK_URL")
            return

        response = requests.post(
            f"{url}?wait=true", json=hook_data, timeout=10
        )
        if not response.ok:
            print(response.json())


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
        response = requests.get(self.URL + self.tag, timeout=10)
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
        response = requests.get(url, timeout=10).json()
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
        response = requests.delete(url, timeout=10)
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
        response = requests.post(
            f"{self.hook_url}?wait=true", json=data, timeout=10
        )
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


class EsVersionSync:
    """check if bbilly1/tubearchivist-es needs updating"""

    REPO = "repos/tubearchivist/tubearchivist"
    COMPOSE = f"https://api.github.com/{REPO}/contents/docker-compose.yml"
    IMAGE = "bbilly1/tubearchivist-es"
    TAGS = f"https://hub.docker.com/v2/repositories/{IMAGE}/tags"

    def __init__(self, repo_conf):
        self.repo_conf = repo_conf
        self.expected = False
        self.current = False

    def run(self):
        """run check, send task if needed"""
        self.get_expected()
        self.get_current()

        if self.expected == self.current:
            print(f"{self.IMAGE} on expected {self.expected}")
        else:
            print(f"bump {self.IMAGE} {self.current} - {self.expected}")
            self.build_task()

    def get_expected(self):
        """get expected es version from readme"""
        response = requests.get(self.COMPOSE, timeout=10).json()
        content = base64.b64decode(response["content"]).decode()
        line = [i for i in content.split("\n") if self.IMAGE in i][0]
        self.expected = line.split()[-1]

    def get_current(self):
        """get current version from docker hub"""
        response = requests.get(self.TAGS, timeout=10).json()
        all_tags = [i.get("name") for i in response["results"]]
        all_tags.pop(0)
        all_tags.sort()

        self.current = all_tags[-1]

    def build_task(self):
        """build task for builder"""
        task = TaskHandler(self.repo_conf, tag_name=self.expected)
        task.create_task("sync_es")
