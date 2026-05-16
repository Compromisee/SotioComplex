import requests, trafilatura, feedparser
from bs4 import BeautifulSoup
from collections import Counter
from urllib.parse import urlparse
from rapidfuzz import fuzz
from .cleaner import TextCleaner

class SiteScraper:
    def __init__(self, logger, config, cache=None, source_health=None):
        self.logger = logger; self.config = config; self.cache = cache; self.health = source_health
        self.headers = {'User-Agent': config['scraping']['user_agent']}
        self.seen_titles = []

    def extract_themes(self, sites):
        self.logger.log(f"Scraping themes from {len(sites)} sites","info")
        counter = Counter()
        bl = {'home','about','contact','login','menu','search','more','subscribe','privacy'}
        for i, site in enumerate(sites):
            self.logger.progress("themes", int(i/max(len(sites),1)*100), site)
            try:
                if not site.startswith('http'): site = 'https://' + site
                if self._is_bl(site): continue
                if self.cache:
                    cached = self.cache.get("themes_html", site)
                    if cached: html = cached
                    else:
                        html = requests.get(site, headers=self.headers, timeout=self.config['scraping']['timeout']).text
                        self.cache.set(html, "themes_html", site)
                else:
                    html = requests.get(site, headers=self.headers, timeout=15).text
                soup = BeautifulSoup(html,'lxml')
                for nav in soup.find_all(['nav','header']):
                    for a in nav.find_all('a'):
                        t = a.get_text(strip=True).lower()
                        if t and 3<len(t)<25 and t not in bl: counter[t] += 2
                meta = soup.find('meta',{'name':'keywords'})
                if meta and meta.get('content'):
                    for k in meta['content'].split(','):
                        k = k.strip().lower()
                        if k and k not in bl: counter[k] += 3
                if self.health: self.health.record(site, True)
                self.logger.log(f"✓ {site}","success")
            except Exception as e:
                if self.health: self.health.record(site, False)
                self.logger.log(f"✗ {site}: {e}","error")
        mx = max(counter.values()) if counter else 1
        themes = [{"name":k,"count":v,"confidence":int(v/mx*100)} for k,v in counter.most_common(60)]
        self.logger.progress("themes",100,"done")
        return themes

    def scrape_by_themes(self, themes, max_per=3):
        self.logger.log(f"Scraping articles · {len(themes)} themes","info")
        articles = []
        for i, theme in enumerate(themes):
            self.logger.progress("articles", int(i/max(len(themes),1)*100), theme)
            try:
                if self.cache:
                    cached = self.cache.get("feed", theme)
                    if cached: feed_entries = cached
                    else:
                        feed = feedparser.parse(f"https://news.google.com/rss/search?q={theme.replace(' ','+')}")
                        feed_entries = [{"title":e.title,"link":e.link,"published":getattr(e,'published','')} for e in feed.entries]
                        self.cache.set(feed_entries, "feed", theme)
                else:
                    feed = feedparser.parse(f"https://news.google.com/rss/search?q={theme.replace(' ','+')}")
                    feed_entries = [{"title":e.title,"link":e.link,"published":getattr(e,'published','')} for e in feed.entries]
                for entry in feed_entries[:max_per]:
                    try:
                        if any(fuzz.ratio(entry['title'], t) > 85 for t in self.seen_titles): continue
                        self.seen_titles.append(entry['title'])
                        if self.cache:
                            c = self.cache.get("article", entry['link'])
                            content = c if c else (trafilatura.extract(trafilatura.fetch_url(entry['link'])) or "")
                            if not c and content: self.cache.set(content, "article", entry['link'])
                        else:
                            content = trafilatura.extract(trafilatura.fetch_url(entry['link'])) or ""
                        content = TextCleaner.dedupe_paragraphs(TextCleaner.clean(content))
                        if not TextCleaner.filter_short(content, self.config['filters']['min_words']): continue
                        domain = urlparse(entry['link']).netloc.replace('www.','')
                        trust = self.config['source_trust'].get(domain, self.config['source_trust']['default'])
                        articles.append({'title':entry['title'],'content':content,'url':entry['link'],
                                        'theme':theme,'source':domain,'trust':trust,
                                        'date':entry['published'],'preview':content[:200]+'...'})
                    except Exception as e: self.logger.log(f"art fail: {e}","warn")
                self.logger.log(f"✓ {theme}","success")
            except Exception as e: self.logger.log(f"theme {theme}: {e}","error")
        articles.sort(key=lambda a:a['trust'], reverse=True)
        return articles

    def _is_bl(self, url):
        d = urlparse(url).netloc
        bl = self.config['filters']['blacklist_sites']; wl = self.config['filters']['whitelist_sites']
        if wl and not any(w in d for w in wl): return True
        return any(b in d for b in bl)