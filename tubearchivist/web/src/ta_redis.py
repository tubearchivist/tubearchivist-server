"""handle redis interactions"""

import json
from datetime import datetime

import redis


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
        if task_name == "sync_es":
            task.update({"clone": False})

        self.conn.json().set(self.key, f".tasks.{repo}", task)

    def build_command(self, task_name):
        """return build command"""
        if not self.tag_name:
            return self.repo_conf.get(task_name)

        all_commands = self.repo_conf.get(task_name)

        if all(isinstance(i, list) for i in all_commands):
            to_build_commands = []
            for command in all_commands:
                to_build_commands.append(self._replace_version(command))
        else:
            to_build_commands = self._replace_version(all_commands)

        return to_build_commands

    def _replace_version(self, command):
        """replace version in str"""
        return [i.replace("$VERSION", self.tag_name) for i in command]

    def set_pub(self):
        """set message to pub"""
        self.conn.publish(self.key, self.repo_conf.get("gh_repo"))
