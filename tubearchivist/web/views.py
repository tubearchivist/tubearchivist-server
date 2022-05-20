"""holds all views and api endpoints"""

from flask import Flask, render_template, jsonify, request
from src.webhook_docker import DockerHook
from src.webhook_github import GithubBackup, GithubHook
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
    handler = DockerHook(request)
    valid = handler.validate()

    print(f"valid: {valid}")
    if not valid:
        return "Forbidden", 403

    print(request.json)
    message = handler.process()

    print(message, "hook sent to discord")
    return jsonify(message)


@app.route("/api/webhook/github/", methods=['POST'])
def webhook_github():
    """prase webhooks from github"""
    handler = GithubHook(request)
    valid = handler.validate()
    print(f"valid: {valid}")
    if not valid:
        return "Forbidden", 403

    print(request.json)
    handler.create_hook_task()
    message = {"success": True}
    return jsonify(message)
