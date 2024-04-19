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
                "build", "--platform", "linux/amd64,linux/arm64",
                "-t", "bbilly1/tubearchivist:unstable", "--push"
            ],
            "build_release": [
                "build", "--platform", "linux/amd64,linux/arm64",
                "-t", "bbilly1/tubearchivist",
                "-t", "bbilly1/tubearchivist:unstable",
                "-t", "bbilly1/tubearchivist:$VERSION", "--push"
            ],
            "sync_es": [
                ["docker", "image", "pull", "docker.elastic.co/elasticsearch/elasticsearch:$VERSION"],
                ["docker", "tag", "docker.elastic.co/elasticsearch/elasticsearch:$VERSION", "bbilly1/tubearchivist-es"],
                ["docker", "tag", "docker.elastic.co/elasticsearch/elasticsearch:$VERSION", "bbilly1/tubearchivist-es:$VERSION"],
                ["docker", "push", "bbilly1/tubearchivist-es"],
                ["docker", "push", "bbilly1/tubearchivist-es:$VERSION"],
            ],
            "discord_unstable_hook": environ.get("DOCKER_UNSTABLE_HOOK_URL"),
            "discord_release_hook": environ.get("GITHUB_RELEASE_HOOK_URL"),
        },
        "browser-extension": {
            "gh_user": "tubearchivist",
            "gh_repo": "browser-extension",
            "discord_release_hook": environ.get("GITHUB_RELEASE_HOOK_URL"),
        },
        "docs": {
            "gh_user": "tubearchivist",
            "gh_repo": "docs",
            "rebuild": [
                ["docker", "compose", "-f", "../docker/docker-compose.yml", "up", "-d", "--build", "docs"]
            ]
        },
        "tubearchivist-jf": {
            "gh_user": "tubearchivist",
            "gh_repo": "tubearchivist-jf",
            "docker_user": "bbilly1",
            "docker_repo": "tubearchivist-jf",
            "build_release": [
                "build", "--platform", "linux/amd64,linux/arm64",
                "-t", "bbilly1/tubearchivist-jf",
                "-t", "bbilly1/tubearchivist-jf:$VERSION", "--push"
            ],
            "discord_release_hook": environ.get("GITHUB_RELEASE_HOOK_URL"),
        },
        "tubearchivist-jf-plugin": {
            "gh_user": "tubearchivist",
            "gh_repo": "tubearchivist-jf-plugin",
        },
        "members": {
            "gh_user": "tubearchivist",
            "gh_repo": "members",
            "docker_user": "bbilly1",
            "docker_repo": "tubearchivist-client",
            "build_release": [
                "build", "--platform", "linux/amd64,linux/arm64",
                "-t", "bbilly1/tubearchivist-client",
                "-t", "bbilly1/tubearchivist-client:$VERSION", "--push"
            ],
            "discord_release_hook": environ.get("GITHUB_RELEASE_HOOK_URL"),
        },
        "tubearchivist-plex": {
            "gh_user": "tubearchivist",
            "gh_repo": "tubearchivist-plex",
        },
        "discord-bot": {
            "gh_user": "tubearchivist",
            "gh_repo": "discord-bot",
            "rebuild": [
                ["docker", "compose", "-f", "../docker/docker-compose.yml", "up", "-d", "--build", "discord-bot"]
            ],
        },
    }
    ROADMAP_HOOK_URL = environ.get("ROADMAP_HOOK_URL")
    GH_HOOK_SECRET = environ.get("GH_HOOK_SECRET")
    DOCKER_HOOK_SECRET = environ.get("DOCKER_HOOK_SECRET")
