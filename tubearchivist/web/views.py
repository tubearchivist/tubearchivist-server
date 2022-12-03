"""holds all views and api endpoints"""

from os import environ

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, jsonify, request, redirect
from src.api_docker import run_docker_backup
from src.webhook_docker import DockerHook
from src.webhook_github import GithubBackup, GithubHook
import markdown

app = Flask(__name__)

scheduler = BackgroundScheduler(timezone=environ.get("TZ"))
scheduler.add_job(
    run_docker_backup,
    trigger="cron",
    day="*",
    hour="*",
    minute="0",
    name="docker_backup",
)
scheduler.start()


@app.route("/")
def home():
    """home page"""
    latest = GithubBackup("latest").get_tag()
    latest_notes = markdown.markdown(latest["release_notes"])
    return render_template(
        'home.html', latest=latest, latest_notes=latest_notes
    )


@app.route("/discord")
def discord_redirect():
    """redirect to current discord invite link"""
    invite = environ.get("discord")
    return redirect(f"https://discord.gg/{invite}", code=302)


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
    handler.save_hook()

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
    handler.save_hook()
    message = {"success": True}
    return jsonify(message)
