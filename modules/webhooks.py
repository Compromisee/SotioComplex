import requests

class WebhookManager:
    def __init__(self, logger, config):
        self.logger = logger; self.config = config

    def notify_discord(self, message):
        url = self.config['webhooks'].get('discord_url')
        if not url: return
        try: requests.post(url, json={"content":message[:1900]})
        except Exception as e: self.logger.log(f"discord wh: {e}","error")

    def notify_slack(self, message):
        url = self.config['webhooks'].get('slack_url')
        if not url: return
        try: requests.post(url, json={"text":message})
        except Exception as e: self.logger.log(f"slack wh: {e}","error")

    def notify_all(self, message):
        self.notify_discord(message); self.notify_slack(message)