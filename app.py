from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from flask_socketio import SocketIO
import threading, time, os
from modules import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'html-dash-4'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

CFG = load_config(); PRESETS = load_presets(); THEMES = load_themes()
PIPE_TPL = load_pipeline_templates()
ensure_dirs(CFG)

logger = Logger(socketio, CFG['paths']['log_dir'])
cache = SmartCache(logger, CFG['paths']['cache_dir'], CFG['cache']['ttl_hours'])
health = SourceHealth(logger)
scraper = SiteScraper(logger, CFG, cache, health)
ai = AIHandler(logger, CFG, PRESETS, cache)
tts = TTSHandler(logger, CFG['paths']['audio_dir'])
whisper = WhisperHandler(logger)
video = VideoHandler(logger, CFG['paths']['video_dir'], CFG['paths']['stock_dir'], CFG['paths']['music_dir'], CFG['paths']['preview_dir'])
image = ImageHandler(logger, CFG['paths']['image_dir'])
thumb = ThumbnailGenerator(logger, CFG['paths']['thumb_dir'])
exporter = Exporter(logger, CFG['paths']['export_dir'])
history = HistoryManager(logger, CFG['paths']['history_dir'])
scheduler = JobScheduler(logger)
queue = QueueManager(logger, CFG['queue']['max_concurrent'])
cost = CostEstimator(CFG)
publishers = Publishers(logger, CFG, CFG['paths']['history_dir'])
analyzers = Analyzers(logger)
webhooks = WebhookManager(logger, CFG)
auth = AuthManager(logger)

STATE = {"themes":[], "articles":[], "results":[], "paused":False, "stop":False, "pending_edits":{}}

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/bootstrap')
def bootstrap():
    return jsonify({"config":CFG,"presets":PRESETS,"themes":THEMES,"pipeline_templates":PIPE_TPL,
                    "models":ai.detect_models(),"voices":CFG['tts']['voices'],
                    "history":history.list_jobs(),"cache_stats":cache.stats(),
                    "source_health":health.report()})

@app.route('/api/scrape-themes', methods=['POST'])
def scrape_themes():
    sites = request.json.get('sites', [])
    def job():
        STATE['themes'] = scraper.extract_themes(sites)
        socketio.emit('themes_ready',{'themes':STATE['themes']})
    threading.Thread(target=job).start()
    return jsonify({"status":"started"})

@app.route('/api/scrape-articles', methods=['POST'])
def scrape_articles():
    d = request.json
    def job():
        if d.get('article'):
            STATE['articles'] = [{"title":"Custom","content":TextCleaner.clean(d['article']),"url":"","source":"custom","trust":100,"preview":d['article'][:200],"date":""}]
        else:
            STATE['articles'] = scraper.scrape_by_themes(d.get('themes',[]))
            for a in STATE['articles']: a['sentiment'] = analyzers.sentiment(a['content'])
        # Trends (#33)
        trends = analyzers.detect_trends(STATE['articles'])
        socketio.emit('articles_ready',{'articles':STATE['articles'],'trends':trends})
    threading.Thread(target=job).start()
    return jsonify({"status":"started"})

@app.route('/api/estimate', methods=['POST'])
def estimate():
    """#4 Cost estimator endpoint"""
    opts = request.json
    n = min(opts.get('max_articles',2), len(STATE['articles']))
    return jsonify(cost.estimate(n, opts))

@app.route('/api/summarize-preview', methods=['POST'])
def summarize_preview():
    """#3 Hot-swap editor: summarize first, return for editing"""
    opts = request.json
    summaries = []
    for art in STATE['articles'][:opts.get('max_articles',2)]:
        s = ai.summarize(art['content'], provider=opts.get('provider','ollama'),
                        model=opts.get('model','llama3'), style=opts.get('style','concise'),
                        api_key=opts.get('api_key',''), translate_to=opts.get('translate_to'))
        summaries.append({"title":art['title'],"summary":s,"sentiment":analyzers.sentiment(art['content'])})
    STATE['pending_edits'] = {i:s for i,s in enumerate(summaries)}
    return jsonify({"summaries":summaries})

@app.route('/api/generate', methods=['POST'])
def generate():
    opts = request.json
    STATE['stop']=False; STATE['paused']=False; STATE['results']=[]
    edited = opts.get('edited_summaries') or {}

    def process_one(i, art):
        if STATE['stop']: return None
        while STATE['paused']: time.sleep(0.4)
        logger.log(f"▶ {art['title']}","info")
        lang = ai.detect_language(art['content'])
        summary = edited.get(str(i)) or ai.summarize(art['content'],
            provider=opts.get('provider','ollama'), model=opts.get('model','llama3'),
            style=opts.get('style','concise'), api_key=opts.get('api_key',''),
            translate_to=opts.get('translate_to'))
        result = {"title":art['title'],"source":art.get('source',''),"url":art.get('url',''),
                 "trust":art.get('trust',0),"summary":summary,"language":lang,"assets":{},
                 "sentiment":analyzers.sentiment(summary)}

        # TTS
        if opts.get('gen_tts',True):
            if opts.get('dialogue_mode'):
                audio = tts.generate_dialogue(summary, opts.get('voice','en-US-GuyNeural'), opts.get('voice2','en-US-AriaNeural'))
            elif opts.get('clone_sample'):
                audio = tts.clone_voice(summary, opts['clone_sample'], opts.get('elevenlabs_key',''))
            else:
                audio = tts.generate(summary, opts.get('voice','en-US-AriaNeural'))
            result['assets']['audio'] = audio

        # Whisper captions (#8)
        caption_words = None
        if opts.get('use_whisper') and result['assets'].get('audio'):
            caption_words = whisper.transcribe(result['assets']['audio'])
            srt = result['assets']['audio'].replace('.mp3','_whisper.srt')
            whisper.to_srt(caption_words, srt); result['assets']['srt'] = srt

        # Video
        if opts.get('gen_video',True):
            bg = video.fetch_background(prompt=opts.get('video_prompt') or art['title'],
                                       url=opts.get('video_url',''), shorts=opts.get('shorts',True), cache=cache)
            result['assets']['videos'] = video.build_video(bg, summary,
                audio_path=result['assets'].get('audio'),
                shorts=opts.get('shorts',True), split=opts.get('split',True),
                captions_words=caption_words, add_music=opts.get('add_music',True))

        # Images / thumb
        if opts.get('gen_images',True):
            result['assets']['images'] = image.create_cards(summary, count=opts.get('image_count',2))
        if opts.get('gen_thumb',True):
            result['assets']['thumbnail'] = thumb.generate(art['title'], theme=opts.get('template','tech'))

        # A/B test variant (#12)
        if opts.get('ab_test'):
            v2 = ai.summarize(art['content'], provider=opts.get('provider','ollama'),
                model=opts.get('model','llama3'), style='social_hook', api_key=opts.get('api_key',''))
            result['variant_b'] = v2

        # Auto-publish (#25-27)
        if opts.get('auto_publish'):
            if opts.get('publish_yt') and result['assets'].get('videos'):
                publishers.youtube_upload(result['assets']['videos'][0], art['title'], summary)
            if opts.get('publish_wp'):
                publishers.wordpress_post(art['title'], summary)

        socketio.emit('result_ready', result)
        return result

    def job():
        articles = STATE['articles'][:opts.get('max_articles',2)]
        total = max(len(articles),1)
        # Concurrent (#13)
        if opts.get('concurrent') and len(articles) > 1:
            futures = [queue.submit(process_one, i, a) for i,a in enumerate(articles)]
            results = queue.wait_all()
            STATE['results'] = [r for r in results if r]
        else:
            for i, a in enumerate(articles):
                logger.progress("pipeline", int(i/total*100), f"Article {i+1}/{total}")
                r = process_one(i, a)
                if r: STATE['results'].append(r)

        # Clustering (#31)
        clusters = analyzers.cluster_topics(STATE['articles'][:opts.get('max_articles',2)])

        history.save_job({"title":f"Run · {len(STATE['results'])} items","results":STATE['results'],"clusters":clusters})
        webhooks.notify_all(f"✅ Html Dash: generated {len(STATE['results'])} items")
        # RSS rebuild (#28)
        publishers.export_rss()
        logger.progress("pipeline",100,"complete")
        logger.notify("Pipeline Complete",f"{len(STATE['results'])} items","success")
        socketio.emit('job_complete',{"results":STATE['results'],"clusters":clusters})
    threading.Thread(target=job).start()
    return jsonify({"status":"started"})

@app.route('/api/control', methods=['POST'])
def control():
    a = request.json.get('action')
    if a=='pause': STATE['paused']=True
    elif a=='resume': STATE['paused']=False
    elif a=='stop': STATE['stop']=True
    return jsonify({"status":a})

@app.route('/api/fact-check', methods=['POST'])
def fact_check():
    """#32"""
    claim = request.json.get('claim','')
    return jsonify(analyzers.fact_check(claim, STATE['articles']))

@app.route('/api/export', methods=['POST'])
def export():
    fmt = request.json.get('format','json')
    if fmt == 'notion':
        ok = exporter.push_notion(STATE['results'], request.json.get('notion_key'), request.json.get('database_id'))
        return jsonify({"ok":ok})
    path = exporter.export(STATE['results'], fmt)
    return jsonify({"path":f"/{path}" if path else None})

@app.route('/api/cache/clear', methods=['POST'])
def cache_clear(): cache.clear(); return jsonify({"ok":True})

@app.route('/api/source-health')
def src_health(): return jsonify(health.report())

@app.route('/api/scheduled')
def list_sched(): return jsonify(scheduler.list_jobs())

@app.route('/api/schedule', methods=['POST'])
def add_sched():
    d = request.json
    def task(): logger.log(f"Scheduled run: {d.get('id')}","info")  # extend
    if d.get('cron'):
        scheduler.schedule_cron(task, d['hour'], d['minute'], d['id'])
    else:
        scheduler.schedule(task, d.get('interval',60), d['id'])
    return jsonify({"ok":True})

@app.route('/api/pipeline/save', methods=['POST'])
def save_pipeline():
    """#1 Save visual pipeline"""
    p = request.json
    name = p.get('name', f"pipeline_{int(time.time())}")
    PIPE_TPL[name] = p
    save_json('pipeline_templates.json', PIPE_TPL)
    return jsonify({"ok":True,"name":name})

@app.route('/api/pipeline/run', methods=['POST'])
def run_pipeline():
    """Execute visual pipeline"""
    p = request.json
    # Translate nodes → standard opts
    opts = {}
    for node in p.get('nodes',[]):
        if node['type']=='source': opts['sites'] = PRESETS['source_presets'].get(node.get('preset','tech'),[])
        if node['type']=='ai': opts['style'] = node.get('style','concise')
        if node['type']=='tts': opts['voice'] = node.get('voice','en-US-AriaNeural'); opts['gen_tts']=True
        if node['type']=='video': opts['gen_video']=True; opts['shorts']=node.get('shorts',True)
        if node['type']=='publish': opts['auto_publish']=True
    return jsonify({"opts":opts})

@app.route('/api/trigger', methods=['POST'])
def trigger():
    """#15 External webhook trigger"""
    threading.Thread(target=lambda: socketio.emit('external_trigger', request.json)).start()
    return jsonify({"ok":True})

@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.json
    token = auth.login(d.get('user'), d.get('password'))
    return jsonify({"token":token} if token else {"error":"invalid"}), (200 if token else 401)

@app.route('/api/auth/register', methods=['POST'])
def register():
    d = request.json
    ok = auth.register(d.get('user'), d.get('password'))
    return jsonify({"ok":ok})

@app.route('/api/notifications')
def notifs(): return jsonify(logger.notifications)

@app.route('/api/history')
def hist(): return jsonify(history.list_jobs())

@app.route('/api/history/<jid>')
def loadhist(jid): return jsonify(history.load_job(jid))

@app.route('/feed.xml')
def rss_feed():
    p = publishers.export_rss()
    if p and os.path.exists(p): return Response(open(p).read(), mimetype='application/rss+xml')
    return "no feed", 404

@app.route('/output/<path:f>')
def out(f): return send_from_directory('output', f)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)