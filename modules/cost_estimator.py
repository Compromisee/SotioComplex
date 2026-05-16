class CostEstimator:
    def __init__(self, config):
        self.config = config
        self.costs = config['cost_per_1k_tokens']

    def estimate(self, articles_count, opts):
        provider = opts.get('provider','ollama')
        avg_tokens_per_article = 1500
        total_tokens = articles_count * avg_tokens_per_article
        cost_key = {'openai':'openai_gpt4o_mini','anthropic':'anthropic_haiku','groq':'groq','gemini':'gemini'}.get(provider,'ollama')
        ai_cost = (total_tokens/1000) * self.costs.get(cost_key, 0)
        # Time estimate
        per_article_sec = 30  # AI
        if opts.get('gen_tts'): per_article_sec += 10
        if opts.get('gen_video'): per_article_sec += 60
        if opts.get('gen_images'): per_article_sec += 5
        if opts.get('gen_thumb'): per_article_sec += 3
        if opts.get('use_whisper'): per_article_sec += 20
        total_sec = articles_count * per_article_sec
        return {
            "articles": articles_count,
            "estimated_seconds": total_sec,
            "estimated_cost_usd": round(ai_cost, 4),
            "videos": articles_count if opts.get('gen_video') else 0,
            "images": articles_count * opts.get('image_count',2) if opts.get('gen_images') else 0,
            "human_time": f"~{total_sec//60}m {total_sec%60}s"
        }