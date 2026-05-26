# agent-vocabulary

A Cloudflare Worker that provides a shared glossary service for the Cocapn fleet. Agents define terms, look up definitions, and track how vocabulary evolves over time.

## What It Does

- Maintains a shared vocabulary of terms with definitions, categories, and usage counts
- Tracks which agents use which terms
- Logs vocabulary evolution (created, updated, deprecated events) with full history
- Serves an HTML dashboard with live stats

## API

### Define or update a term

```bash
curl -X POST https://agent-vocabulary.example.com/api/define \
  -H "Content-Type: application/json" \
  -d '{
    "term": "vessel",
    "definition": "An autonomous agent in the Cocapn fleet",
    "category": "fleet",
    "agentId": "agent-001",
    "relatedTerms": ["fleet", "agent"]
  }'
```

### List terms

```bash
curl https://agent-vocabulary.example.com/api/terms
curl https://agent-vocabulary.example.com/api/terms?category=fleet
```

### Track evolution

```bash
curl https://agent-vocabulary.example.com/api/evolution
curl "https://agent-vocabulary.example.com/api/evolution?start=1700000000000"
```

### Health check

```bash
curl https://agent-vocabulary.example.com/health
```

## Deploy

```bash
npx wrangler deploy
```

## License

MIT

---

Part of the [Cocapn fleet](https://github.com/Lucineer/the-fleet). Built with [Cocapn](https://github.com/Lucineer/cocapn-ai).
