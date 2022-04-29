"""monitor reddit for new posts and comments"""

from os import environ
import requests


class MonitorReddit:
    """holds reddit connection"""

    headers = {"User-Agent": "r/tubeArchivist discord bot monitor"}
    posts = "https://www.reddit.com/r/tubeArchivist/new.json"
    comments = "https://www.reddit.com/r/tubeArchivist/comments.json"

    HOOK_URL = environ.get("REDDIT_HOOK_URL")


    def send_last_comment(self):
        """testing to send only last comment to hook"""
        comments = self.get_comments()
        comment = comments[0]["data"]
        message = self.build_comment_message(comment)
        status = self.send_hook(message)
        print(status)

    @staticmethod
    def build_post_message(post):
        """build comment message str"""
        post_message = post.get("selftext")
        if len(post_message) > 200:
            post_message = post_message[:200] + " ..."

        url = post.get("url")
        print(url)

    @staticmethod
    def build_comment_message(comment):
        """build comment message str"""
        comment_message = comment.get("body")
        link_permalink = comment.get("link_permalink")

        if len(comment_message) > 200:
            comment_message = comment_message[:200] + " ..."

        message = (
            "**New comment:**\n" +
            f"{comment_message}\n" +
            f"[link]({link_permalink})"
        )

        return message

    def send_hook(self, message):
        """send the message to discord"""
        data = {
            "content": message
        }
        response = requests.post(self.HOOK_URL, json=data)
        if not response.ok:
            print(response.json())
            return {"success": False}

        return {"success": True}

    def get_comments(self):
        """get a list of latest comments"""
        return self._get_children(self.comments)

    def get_posts(self):
        """get a list of newest posts"""
        return self._get_children(self.posts)

    def _get_children(self, url):
        """return a list of children from url"""
        response = requests.get(url, headers=self.headers)
        if response.ok:
            children = response.json()["data"]["children"]
        else:
            children = False

        return children
