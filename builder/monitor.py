"""monitor redis for tasks to execute"""

import json
import subprocess
import os

from datetime import datetime

import redis


class RedisBase:
    """connection base for redis"""

    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    NAME_SPACE = "ta:"
    TASK_KEY = NAME_SPACE + "task:buildx"

    def __init__(self):
        self.conn = redis.Redis(host=self.REDIS_HOST, port=self.REDIS_PORT)


class Monitor(RedisBase):
    """look for messages"""

    def get_tasks(self):
        """get task list"""
        response = self.conn.execute_command("JSON.GET", self.TASK_KEY)
        tasks = json.loads(response.decode())
        return tasks

    def bootstrap(self):
        """create custom builder"""
        print("validate builder")
        command = ["docker", "buildx", "inspect"]
        output = subprocess.run(command, check=True, capture_output=True)
        inspect = output.stdout.decode()
        config = {}
        lines = [i for i in inspect.split("\n") if i]
        for line in lines:
            key, value = line.split(":", maxsplit=1)
            if value:
                config[key.strip()] = value.strip()

        if not config["Name"].startswith("tubearchivist"):
            print("create tubearchivist builder")
            self._create_builder()
        else:
            print("tubearchivist builder already created")

    def create_queue(self):
        """set initial json object for queue"""
        if self.conn.execute_command(f"EXISTS {self.TASK_KEY}"):
            print(f"{self.TASK_KEY} already exists")
            return

        message = {
            "created": int(datetime.now().strftime("%s")),
            "tasks": {}
        }
        self.conn.execute_command(
            "JSON.SET", self.TASK_KEY, ".", json.dumps(message)
        )

    @staticmethod
    def _create_builder():
        """create buildx builder"""
        base = ["docker", "buildx"]
        subprocess.run(
            base + ["create", "--name", "tubearchivist"], check=True
        )
        subprocess.run(base + ["use", "tubearchivist"], check=True)
        subprocess.run(base + ["inspect", "--bootstrap"], check=True)

    def check_stored(self):
        """check for any stored task since last watch"""
        task = self.get_tasks()
        if task["tasks"]:
            print("found stored task:")
            for task_name in task["tasks"]:
                print(task_name)
                Builder(task_name).run()

    def watch(self):
        """watch for messages"""
        print("waiting for tasks")
        watcher = self.conn.pubsub()
        watcher.subscribe(self.TASK_KEY)
        for i in watcher.listen():
            if i["type"] == "message":
                task = i["data"].decode()
                print(task)
                Builder(task).run()


class Builder(RedisBase):
    """execute task"""

    CLONE_BASE = "clone"

    def __init__(self, task):
        super().__init__()
        self.task = task
        self.task_detail = False

    def run(self):
        """run all steps"""
        self.get_task()
        self.clone()
        self.build()
        self.remove_task()

    def get_task(self):
        """get what to execute"""
        print("get task from redis")
        response = self.conn.execute_command("JSON.GET", self.TASK_KEY)
        response_json = json.loads(response.decode())
        self.task_detail = response_json["tasks"][self.task]

    def clone(self):
        """clone repo to destination"""
        if not self.task_detail["clone"]:
            print("skip clone")
            return

        print("clone repo")
        repo_dir = os.path.join(self.CLONE_BASE, self.task_detail["name"])
        if os.path.exists(repo_dir):
            command = ["git", "-C", repo_dir, "pull"]
        else:
            command = ["git", "clone", self.task_detail["clone"], repo_dir]

        subprocess.run(command, check=True)

    def build(self):
        """build the container"""
        command_list = self.task_detail["build"]
        if all(isinstance(i, list) for i in command_list):
            for command in command_list:
                print(f"running: {command}")
                subprocess.run(command, check=True)
        else:
            command = ["docker", "buildx"] + self.task_detail["build"]
            command.append(os.path.join(self.CLONE_BASE, self.task))
            print(f"running: {command}")
            subprocess.run(command, check=True)

    def remove_task(self):
        """remove task from redis queue"""
        print("remove task from redis")
        self.conn.json().delete(self.TASK_KEY, f".tasks.{self.task}")


if __name__ == "__main__":
    handler = Monitor()
    handler.bootstrap()
    handler.create_queue()
    handler.check_stored()
    try:
        handler.watch()
    except KeyboardInterrupt:
        print(" [X] cancle watch")
