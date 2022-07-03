"""base class to handle webhook config"""

from os import environ


class WebhookBase:
    """shared config"""

    # map key is gh_repo name
    HOOK_MAP = {
        "tubearchivist": {
            "gh_user": "tubearchivist",
            "gh_repo": "tubearchivist",
            "docker_user": "bbilly1",
            "docker_repo": "tubearchivist",
            "unstable_keyword": "#build",
            "build_unstable": [
                "build", "--platform", "linux/amd64",
                "-t", "bbilly1/tubearchivist:unstable", "--push"
            ],
            "build_release": [
                "build", "--platform", "linux/amd64,linux/arm64",
                "-t", "bbilly1/tubearchivist",
                "-t", "bbilly1/tubearchivist:unstable",
                "-t", "bbilly1/tubearchivist:$VERSION", "--push"
            ],
            "sync_es": [
                ["docker", "image", "pull", "elasticsearch:$VERSION"],
                ["docker", "tag", "elasticsearch:$VERSION", "bbilly1/tubearchivist-es"],
                ["docker", "tag", "elasticsearch:$VERSION", "bbilly1/tubearchivist-es:$VERSION"],
                ["docker", "push", "bbilly1/tubearchivist-es"],
                ["docker", "push", "bbilly1/tubearchivist-es:$VERSION"],
            ],
            "discord_unstable_hook": environ.get("DOCKER_UNSTABLE_HOOK_URL"),
            "discord_release_hook": environ.get("GITHUB_RELEASE_HOOK_URL"),
        }
    }
    ROADMAP_HOOK_URL = environ.get("ROADMAP_HOOK_URL")
    GH_HOOK_SECRET = environ.get("GH_HOOK_SECRET")
    DOCKER_HOOK_SECRET = environ.get("DOCKER_HOOK_SECRET")
