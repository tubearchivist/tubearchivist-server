"""base class to handle webhook config"""

from os import environ


class WebhookBase:
    """shared config"""

    # map key is gh_repo name
    HOOK_MAP = {
        "drone-test": {
            "gh_user": "tubearchivist",
            "gh_repo": "drone-test",
            "docker_user": "bbilly1",
            "docker_repo": "drone-test",
            "unstable_keyword": "#build",
            "build_unstable": [
                "build", "--platform", "linux/amd64,linux/arm64",
                "-t", "bbilly1/drone-test:unstable", "--push"
            ],
            "build_release": [
                "build", "--platform", "linux/amd64,linux/arm64",
                "-t", "bbilly1/drone-test",
                "-t", "bbilly1/drone-test:unstable",
                "-t", "bbilly1/drone-test:$VERSION", "--push"
            ],
            "discord_unstable_hook": environ.get("NOTIFICATION_TEST_HOOK_URL"),
            "discord_release_hook": environ.get("NOTIFICATION_TEST_HOOK_URL"),
        }
    }
    ROADMAP_HOOK_URL = environ.get("ROADMAP_HOOK_URL")
    GH_HOOK_SECRET = environ.get("GH_HOOK_SECRET")
    DOCKER_HOOK_SECRET = environ.get("DOCKER_HOOK_SECRET")
