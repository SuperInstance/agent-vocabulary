interface TermDefinition {
  id: string;
  term: string;
  definition: string;
  category: string;
  createdAt: number;
  updatedAt: number;
  usageCount: number;
  agents: string[];
  relatedTerms: string[];
  status: 'active' | 'deprecated' | 'proposed';
}

interface VocabularyEvolution {
  timestamp: number;
  termId: string;
  changeType: 'created' | 'updated' | 'deprecated';
  previousDefinition?: string;
  newDefinition?: string;
  agentId: string;
}

interface GlossaryResponse {
  terms: TermDefinition[];
  total: number;
  categories: string[];
}

interface DefineRequest {
  term: string;
  definition: string;
  category: string;
  agentId: string;
  relatedTerms?: string[];
}

interface EvolutionResponse {
  events: VocabularyEvolution[];
  period: {
    start: number;
    end: number;
  };
}

class VocabularyStore {
  private terms: Map<string, TermDefinition> = new Map();
  private evolutionLog: VocabularyEvolution[] = [];

  async defineTerm(request: DefineRequest): Promise<TermDefinition> {
    const existing = this.findTerm(request.term);
    const now = Date.now();
    
    if (existing) {
      const previousDefinition = existing.definition;
      existing.definition = request.definition;
      existing.updatedAt = now;
      existing.usageCount++;
      existing.agents = [...new Set([...existing.agents, request.agentId])];
      existing.relatedTerms = request.relatedTerms || existing.relatedTerms;
      
      this.evolutionLog.push({
        timestamp: now,
        termId: existing.id,
        changeType: 'updated',
        previousDefinition,
        newDefinition: request.definition,
        agentId: request.agentId
      });
      
      return existing;
    }
    
    const newTerm: TermDefinition = {
      id: `term_${now}_${Math.random().toString(36).substr(2, 9)}`,
      term: request.term.toLowerCase().trim(),
      definition: request.definition,
      category: request.category,
      createdAt: now,
      updatedAt: now,
      usageCount: 1,
      agents: [request.agentId],
      relatedTerms: request.relatedTerms || [],
      status: 'active'
    };
    
    this.terms.set(newTerm.id, newTerm);
    
    this.evolutionLog.push({
      timestamp: now,
      termId: newTerm.id,
      changeType: 'created',
      newDefinition: request.definition,
      agentId: request.agentId
    });
    
    return newTerm;
  }

  async getTerms(category?: string): Promise<GlossaryResponse> {
    let terms = Array.from(this.terms.values())
      .filter(term => term.status === 'active')
      .sort((a, b) => b.usageCount - a.usageCount);
    
    if (category) {
      terms = terms.filter(term => term.category === category);
    }
    
    const categories = Array.from(new Set(terms.map(term => term.category)));
    
    return {
      terms,
      total: terms.length,
      categories
    };
  }

  async getEvolution(startTime?: number, endTime?: number): Promise<EvolutionResponse> {
    let events = this.evolutionLog;
    
    if (startTime) {
      events = events.filter(event => event.timestamp >= startTime);
    }
    
    if (endTime) {
      events = events.filter(event => event.timestamp <= endTime);
    }
    
    events.sort((a, b) => b.timestamp - a.timestamp);
    
    return {
      events: events.slice(0, 100),
      period: {
        start: startTime || 0,
        end: endTime || Date.now()
      }
    };
  }

  private findTerm(term: string): TermDefinition | undefined {
    const searchTerm = term.toLowerCase().trim();
    return Array.from(this.terms.values())
      .find(t => t.term === searchTerm && t.status === 'active');
  }
}

const store = new VocabularyStore();

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json"
};

const securityHeaders = {
  "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'",
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff"
};

async function handleRequest(request: Request): Promise<Response> {
  const url = new URL(request.url);
  
  if (request.method === "OPTIONS") {
    return new Response(null, {
      headers: corsHeaders
    });
  }
  
  if (url.pathname === "/health") {
    return new Response(JSON.stringify({ status: "healthy", timestamp: Date.now() }), {
      headers: { ...corsHeaders, ...securityHeaders }
    });
  }
  
  if (url.pathname === "/api/terms") {
    if (request.method !== "GET") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { ...corsHeaders, ...securityHeaders }
      });
    }
    
    const category = url.searchParams.get("category") || undefined;
    const glossary = await store.getTerms(category);
    
    return new Response(JSON.stringify(glossary), {
      headers: { ...corsHeaders, ...securityHeaders }
    });
  }
  
  if (url.pathname === "/api/define") {
    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { ...corsHeaders, ...securityHeaders }
      });
    }
    
    try {
      const body = await request.json() as DefineRequest;
      
      if (!body.term || !body.definition || !body.category || !body.agentId) {
        return new Response(JSON.stringify({ error: "Missing required fields" }), {
          status: 400,
          headers: { ...corsHeaders, ...securityHeaders }
        });
      }
      
      const term = await store.defineTerm(body);
      
      return new Response(JSON.stringify(term), {
        headers: { ...corsHeaders, ...securityHeaders }
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: "Invalid request body" }), {
        status: 400,
        headers: { ...corsHeaders, ...securityHeaders }
      });
    }
  }
  
  if (url.pathname === "/api/evolution") {
    if (request.method !== "GET") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { ...corsHeaders, ...securityHeaders }
      });
    }
    
    const startTime = url.searchParams.get("start") ? parseInt(url.searchParams.get("start")!) : undefined;
    const endTime = url.searchParams.get("end") ? parseInt(url.searchParams.get("end")!) : undefined;
    
    const evolution = await store.getEvolution(startTime, endTime);
    
    return new Response(JSON.stringify(evolution), {
      headers: { ...corsHeaders, ...securityHeaders }
    });
  }
  
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Vocabulary</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: #0a0a0f;
            color: #ffffff;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        header {
            text-align: center;
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid #1a1a2e;
        }
        h1 {
            font-size: 3rem;
            background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        .subtitle {
            color: #94a3b8;
            font-size: 1.2rem;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }
        .stat-card {
            background: #1a1a2e;
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #ec4899;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #ec4899;
        }
        .stat-label {
            color: #94a3b8;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .endpoints {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 3rem;
        }
        .endpoint {
            background: #0a0a0f;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 1px solid #2d2d4d;
        }
        .method {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.9rem;
            margin-right: 1rem;
        }
        .get { background: #10b981; color: white; }
        .post { background: #ec4899; color: white; }
        .path {
            font-family: 'Monaco', 'Courier New', monospace;
            color: #60a5fa;
        }
        footer {
            text-align: center;
            padding: 2rem;
            color: #64748b;
            font-size: 0.9rem;
            border-top: 1px solid #1a1a2e;
            margin-top: 3rem;
        }
        .health-link {
            color: #ec4899;
            text-decoration: none;
            margin-left: 1rem;
        }
        .health-link:hover {
            text-decoration: underline;
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <header>
            <h1>Agent Vocabulary</h1>
            <p class="subtitle">Build and track shared vocabulary across the fleet</p>
        </header>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-value">0</div>
                <div class="stat-label">Active Terms</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">0</div>
                <div class="stat-label">Categories</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">0</div>
                <div class="stat-label">Evolution Events</div>
            </div>
        </div>
        
        <div class="endpoints">
            <h2 style="margin-bottom: 1.5rem; color: #ec4899;">API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <span class="path">/api/terms</span>
                <p style="margin-top: 0.5rem; color: #94a3b8;">Retrieve all active terms, optionally filtered by category</p>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <span class="path">/api/define</span>
                <p style="margin-top: 0.5rem; color: #94a3b8;">Define or update a term in the vocabulary</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <span class="path">/api/evolution</span>
                <p style="margin-top: 0.5rem; color: #94a3b8;">Track vocabulary evolution over time</p>
            </div>
        </div>
    </div>
    
    <footer>
        <div>Agent Vocabulary Service</div>
        <div style="margin-top: 0.5rem;">
            Fleet Glossary Management
            <a href="/health" class="health-link">/health</a>
        </div>
    </footer>
    
    <script>
        async function updateStats() {
            try {
                const response = await fetch('/api/terms');
                const data = await response.json();
                
                const evolutionResponse = await fetch('/api/evolution');
                const evolutionData = await evolutionResponse.json();
                
                const stats = document.getElementById('stats');
                stats.children[0].querySelector('.stat-value').textContent = data.total;
                stats.children[1].querySelector('.stat-value').textContent = data.categories.length;
                stats.children[2].querySelector('.stat-value').textContent = evolutionData.events.length;
            } catch (error) {
                console.error('Failed to fetch stats:', error);
            }
        }
        
        updateStats();
    </script>
</body>
</html>
  `;
  
  return new Response(html, {
    headers: {
      "Content-Type": "text/html;charset=UTF-8",
      ...securityHeaders
    }
  });
}

export default {
  async fetch(request: Request, env: unknown, ctx: ExecutionContext): Promise<Response> {
    return handleRequest(request);
  }
};