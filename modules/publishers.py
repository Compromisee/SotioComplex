import os, json, requests, datetime

class Publishers:
    def __init__(self, logger, config, history_dir='output/history'):
        self.logger = logger; self.config = config; self.history_dir = history_dir

    def youtube_upload(self, video_path, title, description, tags=None):
        """#25 YouTube upload via OAuth"""
        if not self.config['publishers'].get('youtube_enabled'):
            self.logger.log("YouTube disabled in config","warn"); return None
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file('yt_token.json')
            yt = build('youtube','v3',credentials=creds)
            body = {"snippet":{"title":title[:100],"description":description,"tags":tags or [],"categoryId":"22"},
                    "status":{"privacyStatus":"private"}}
            req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(video_path))
            r = req.execute()
            self.logger.log(f"YT uploaded: {r['id']}","success")
            return r['id']
        except Exception as e: self.logger.log(f"YT: {e}","error"); return None

    def wordpress_post(self, title, content, thumbnail=None):
        """#27 WordPress publisher"""
        url = self.config['publishers'].get('wordpress_url')
        user = self.config['publishers'].get('wordpress_user')
        pw = self.config['publishers'].get('wordpress_pass')
        if not all([url,user,pw]): self.logger.log("WP not configured","warn"); return None
        try:
            r = requests.post(f"{url}/wp-json/wp/v2/posts", auth=(user,pw),
                json={"title":title,"content":content,"status":"draft"})
            self.logger.log(f"WP draft created: {r.json().get('id')}","success")
            return r.json().get('id')
        except Exception as e: self.logger.log(f"WP: {e}","error"); return None

    def export_rss(self):
        """#28 RSS feed output"""
        try:
            items = []
            for f in sorted(os.listdir(self.history_dir), reverse=True)[:50]:
                if not f.startswith('job_'): continue
                with open(f"{self.history_dir}/{f}") as jf:
                    data = json.load(jf)
                    for r in data.get('data',{}).get('results',[]):
                        items.append(f"""<item>
<title><![CDATA[{r.get('title','')}]]></title>
<description><![CDATA[{r.get('summary','')}]]></description>
<link>{r.get('url','')}</link>
<pubDate>{data['timestamp']}</pubDate>
</item>""")
            rss = f"""<?xml version="1.0"?><rss version="2.0"><channel>
<title>Html Dash Feed</title><link>http://localhost:5000</link>
<description>Auto-generated content</description>
{''.join(items)}
</channel></rss>"""
            out = "output/feed.xml"
            with open(out,'w',encoding='utf-8') as f: f.write(rss)
            return out
        except Exception as e: self.logger.log(f"RSS: {e}","error"); return None

    def tiktok_stub(self, video_path, caption):
        """#26 TikTok placeholder (requires business API)"""
        self.logger.log("TikTok upload requires TikTok Business API approval","warn")
        return None