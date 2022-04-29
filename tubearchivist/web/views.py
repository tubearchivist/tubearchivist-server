"""holds all views and api endpoints"""

from flask import Flask, render_template, jsonify, request
from src.webhook_docker import DockerHook
from src.webhook_github import GithubBackup
import markdown

app = Flask(__name__)


@app.route("/")
def home():
    """home page"""
    latest = GithubBackup("latest").get_tag()
    latest_notes = markdown.markdown(latest["release_notes"])
    return render_template(
        'home.html', latest=latest, latest_notes=latest_notes
    )


@app.route("/api/release/<release_id>/")
def release(release_id):
    """api release"""
    result = GithubBackup(release_id).get_tag()
    return jsonify(result)


@app.route("/api/webhook/docker/", methods=['POST'])
def webhook_docker():
    """parse docker webhook data"""
    print(request.json)
    hook = DockerHook(request.json)
    if hook.docker_hook_details.get("release_tag") != "unstable":
        message = {"success": False}
        print(message, "not unstable build")
        return jsonify(message)

    hook.get_latest_commit()
    if not hook.first_line_message.endswith("#build"):
        message = {"success": False}
        print(message, "not build message in commit")
        return jsonify(message)

    message = hook.forward_message()
    print(message, "hook sent to discord")
    return jsonify(message)


@app.route("/api/webhook/github/", methods=['POST'])
def webhook_github():
    """prase webhooks from github"""
    print(request.json)
    message = {"success": False}
    return jsonify(message)
