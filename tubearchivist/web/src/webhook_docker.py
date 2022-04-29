"""parse and forward docker webhooks"""

from os import environ
import requests


class DockerHook:
    """parse docker webhook and forward to discord"""

    HOOK_URL = environ.get("DOCKER_UNSTABLE_HOOK_URL")
    COMMITS_URL = "https://api.github.com/repos/bbilly1/tubearchivist/commits"

    def __init__(self, docker_hook):
        self.docker_hook = docker_hook
        self.docker_hook_details = self.docker_hook_parser()
        self.commit_url = False
        self.first_line_message = False

    def docker_hook_parser(self):
        """parse data from docker"""

        docker_hook_details = {
            "release_tag": self.docker_hook["push_data"]["tag"],
            "repo_url": self.docker_hook["repository"]["repo_url"],
            "repo_name": self.docker_hook["repository"]["repo_name"]
        }

        return docker_hook_details

    def get_latest_commit(self):
        """get latest commit url from master"""
        response = requests.get(f"{self.COMMITS_URL}/master").json()
        self.commit_url = response["html_url"]
        self.first_line_message = response["commit"]["message"].split("\n")[0]

    def forward_message(self):
        """forward message to discrod"""
        data = self.build_message()
        response = requests.post(self.HOOK_URL, json=data)
        if not response.ok:
            print(response.json())
            return {"success": False}

        return {"success": True}

    def build_message(self):
        """build message for discord hook"""
        release_tag = self.docker_hook_details["release_tag"]
        repo_url = self.docker_hook_details["repo_url"]
        message = (
            f"There is a new **{release_tag}** build " +
            f"published to [docker]({repo_url}). Built from:\n" +
            self.commit_url)

        data = {
            "content": message
        }

        return data
