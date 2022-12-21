"""parse and forward docker webhooks"""

import json
from datetime import datetime

import requests
from src.webhook_base import WebhookBase


class DockerHook(WebhookBase):
    """parse docker webhook and forward to discord"""

    def __init__(self, request):
        self.request = request
        self.name = False
        self.hook = False
        self.repo_conf = False
        self.tag = False

    def validate(self):
        """validate hook origin"""
        received = self.request.args.get("secret")
        if not received:
            return False

        return received == self.DOCKER_HOOK_SECRET

    def process(self):
        """process the hook data"""

        parsed = self._parse_hook()
        if not parsed:
            return False

        if self.tag == "unstable":
            response = self._send_unstable_hook()
        else:
            response = self._send_release_hook()

        return response

    def _send_unstable_hook(self):
        """send notification for unstable build"""

        commit_url, first_line_message = self._get_last_commit()
        if not first_line_message.endswith(self.repo_conf["unstable_keyword"]):
            message = {"success": False}
            print(message, "build message not found in commit")
            return message

        url = self.repo_conf["discord_unstable_hook"]
        message_data = self._build_unstable_message(commit_url)
        response = self._forward_message(message_data, url)
        return response

    def _parse_hook(self):
        """parse hook json"""
        self.hook = self.request.json
        self.tag = self.hook["push_data"]["tag"]
        if not self.tag or self.tag == "latest":
            return False

        self.name = self.hook["repository"]["name"]
        if self.name not in self.HOOK_MAP:
            print(f"repo {self.name} not registered")
            return False

        self.repo_conf = self.HOOK_MAP[self.name]

        return True

    def _get_last_commit(self):
        """get last commit from git repo"""
        user = self.repo_conf.get("gh_user")
        repo = self.repo_conf.get("gh_repo")
        url = f"https://api.github.com/repos/{user}/{repo}/commits/master"
        response = requests.get(url, timeout=20).json()
        commit_url = response["html_url"]
        first_line_message = response["commit"]["message"].split("\n")[0]

        return commit_url, first_line_message

    @staticmethod
    def _forward_message(message_data, url):
        """forward message to discrod"""
        response = requests.post(url, json=message_data, timeout=20)
        if not response.ok:
            print(response.json())
            return {"success": False}

        return {"success": True}

    def _build_unstable_message(self, commit_url):
        """build message for discord hook"""
        repo_url = self.hook["repository"]["repo_url"]
        message = (
            f"There is a new **{self.tag}** build published to " +
            f"[docker]({repo_url}). Built from:\n{commit_url}"
        )
        message_data = {
            "content": message
        }

        return message_data

    def _send_release_hook(self):
        """send new release notification"""
        user = self.repo_conf.get("gh_user")
        repo = self.repo_conf.get("gh_repo")
        release_url = (
            f"https://github.com/{user}/{repo}/" +
            f"releases/tag/{self.tag}"
        )
        message_data = {
            "content": release_url
        }

        url = self.repo_conf["discord_release_hook"]
        response = self._forward_message(message_data, url)

        return response

    def save_hook(self):
        """save hook to disk for easy debugging"""
        now = datetime.now().strftime("%s")
        filename = f"/data/hooks/docker_hook-{now}.json"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.hook))
