from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from rapidfuzz import fuzz
from collections import Counter

class Analyzers:
    def __init__(self, logger):
        self.logger = logger
        self.trend_history = []

    def sentiment(self, text):
        """#30"""
        try:
            blob = TextBlob(text)
            p = blob.sentiment.polarity
            label = "bullish" if p > 0.15 else "bearish" if p < -0.15 else "neutral"
            return {"polarity": round(p,3), "label": label}
        except: return {"polarity":0,"label":"neutral"}

    def cluster_topics(self, articles, n=3):
        """#31"""
        try:
            texts = [a['content'][:1500] for a in articles]
            if len(texts) < 2: return [{"cluster":0,"articles":articles}]
            vec = TfidfVectorizer(stop_words='english', max_features=100)
            X = vec.fit_transform(texts)
            n = min(n, len(texts))
            km = KMeans(n_clusters=n, n_init=10, random_state=42).fit(X)
            clusters = {}
            for i, lab in enumerate(km.labels_):
                clusters.setdefault(int(lab), []).append(articles[i])
            return [{"cluster":k,"size":len(v),"articles":v} for k,v in clusters.items()]
        except Exception as e: self.logger.log(f"cluster: {e}","error"); return [{"cluster":0,"articles":articles}]

    def fact_check(self, claim, all_articles):
        """#32 Cross-reference claim across sources"""
        try:
            matches = []
            for a in all_articles:
                score = fuzz.partial_ratio(claim.lower(), a['content'].lower())
                if score > 60: matches.append({"source":a['source'],"score":score})
            confidence = sum(m['score'] for m in matches)/max(len(matches),1) if matches else 0
            return {"confidence":int(confidence),"matches":len(matches),"sources":[m['source'] for m in matches[:5]]}
        except: return {"confidence":0,"matches":0,"sources":[]}

    def detect_trends(self, articles):
        """#33 Spike detection over time"""
        try:
            words = []
            for a in articles:
                for w in (a.get('title','')+' '+a.get('theme','')).lower().split():
                    if len(w) > 4: words.append(w)
            cnt = Counter(words)
            self.trend_history.append(cnt)
            if len(self.trend_history) > 10: self.trend_history.pop(0)
            if len(self.trend_history) < 2: return []
            prev = self.trend_history[-2] if len(self.trend_history)>=2 else Counter()
            trends = []
            for w, c in cnt.most_common(20):
                p = prev.get(w, 0)
                if c >= 3 and c > p * 1.5:
                    trends.append({"keyword":w,"count":c,"growth":int((c-p)/max(p,1)*100)})
            return trends[:10]
        except Exception as e: self.logger.log(f"trends: {e}","error"); return []