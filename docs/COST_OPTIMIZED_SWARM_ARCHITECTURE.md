# Cost-Optimized Large-Scale Swarm Architecture

## Executive Summary

This document outlines the architecture changes needed to support 100+ clip batch operations while minimizing costs and maximizing agentic capability. The goal is a system that scales from 1 agent on free tier to 1000+ agents on enterprise, with costs growing sub-linearly to clip count.

---

## 1. Cost Structure Analysis (Current)

| Operation | Cost/Agent | Current Max | Cost at Max |
|-----------|-----------|-------------|-------------|
| Hook Gen | $0.05 | 10 agents | $0.50 |
| Remix | $0.20 | 10 agents | $2.00 |
| Post | $0.01 | 10 agents | $0.10 |
| A/B Test | $0.03 | 10 agents | $0.30 |
| Music Match | $0.02 | 10 agents | $0.20 |
| Thumbnail | $0.01 | 10 agents | $0.10 |
| Safety | $0.01 | 10 agents | $0.10 |
| Hooks Analysis | $0.08 | 10 agents | $0.80 |
| Segment Analysis | $0.05 | 10 agents | $0.50 |
| Edit Recipe | $0.15 | 10 agents | $0.50 |

**Problem:** 100 clips × 10 agents × $0.05 = $50 for just hooks. At scale, this is unsustainable.

**Target:** 100 clips × 1 agent × $0.01 = $1 for basic analysis, with selective deep analysis on top performers.

---

## 2. Three-Tier Cost Optimization Strategy

### Tier 1: Smart Defaults (Free - No API Calls)
- **Rule-based hook generation** using templates + transcript analysis (local)
- **FFmpeg-based segment detection** (local, no AI)
- **Static safety screening** against known patterns
- **No cloud AI calls** for basic operations
- **Cost: $0**

### Tier 2: Selective AI (Basic/Pro - Targeted API Calls)
- Run AI only on **top 20%** of clips by base score
- **Shared context** across clips from same source (one transcript → multiple hooks)
- **Cached embeddings** reused across operations
- **Batched API calls** where possible
- **Cost: ~70% reduction** vs naive approach

### Tier 3: Full Swarm (Enterprise - Parallel AI)
- Full multi-agent orchestration
- Cross-clip learning (agents learn from all clips in batch)
- Genetic algorithm optimization
- **Cost: premium but justified by output quality**

---

## 3. Batch Processing Architecture

### New Endpoint: `/swarm/batch`

Accepts arrays of clip IDs and processes them as a single swarm job:

```python
class SwarmBatchRequest(BaseModel):
    clip_ids: List[str]  # Up to 100 clips
    pool_type: SwarmJobType
    agent_count: Optional[int] = None
    strategy_filter: Optional[List[str]] = None
    # Batch-specific options
    shared_context: bool = True  # Share source analysis across clips
    top_k: Optional[int] = None  # Only process top N clips
    priority: str = "balanced"  # "speed", "quality", "cost"
```

### Processing Strategy by Priority

```python
async def execute_batch_swarm(
    clip_ids: List[str],
    pool_type: str,
    user_id: str,
    priority: str = "balanced"
):
    if priority == "cost":
        # Sequential processing, shared context, minimal agents
        return await _batch_cost_optimized(clip_ids, pool_type, user_id)
    elif priority == "speed":
        # Max parallel, process all simultaneously
        return await _batch_speed_optimized(clip_ids, pool_type, user_id)
    else:
        # Smart: analyze all, deep-dive on top performers
        return await _batch_balanced(clip_ids, pool_type, user_id)
```

### Shared Context Pattern

```python
class BatchContext:
    """Shared analysis results reused across clips from same source."""
    
    def __init__(self, source_id: str):
        self.source_id = source_id
        self.transcript: Optional[str] = None
        self.energy_peaks: List[float] = []
        self.face_segments: List[dict] = []
        self.audio_fingerprint: Optional[dict] = None
        self._loaded = False
    
    async def load(self):
        if self._loaded:
            return
        # Load once, reuse for all clips
        self.transcript = await get_cached_transcript(self.source_id)
        self.energy_peaks = await analyze_energy(self.source_id)
        self.face_segments = await detect_faces(self.source_id)
        self._loaded = True
    
    def get_context_for_clip(self, clip_id: str, segment: dict) -> dict:
        """Extract relevant portion of shared context for a specific clip."""
        start, end = segment["start"], segment["end"]
        return {
            "transcript": self._extract_transcript_slice(start, end),
            "energy_peak": self._find_peak_in_range(start, end),
            "has_faces": self._has_faces_in_range(start, end),
        }
```

---

## 4. Caching Layer

### Multi-Level Cache

```python
class SwarmCache:
    """Three-tier caching for swarm operations."""
    
    # L1: In-memory (per-request, ~10ms)
    _memory: Dict[str, Any] = {}
    
    # L2: Redis (cross-request, ~5ms network)
    _redis: Optional[Redis] = None
    
    # L3: Supabase (persistent, ~50ms)
    _db: Optional[SupabaseService] = None
    
    @staticmethod
    def key(pool_type: str, clip_id: str, strategy: str) -> str:
        return f"swarm:{pool_type}:{clip_id}:{hashlib.md5(strategy.encode()).hexdigest()[:8]}"
    
    async def get(self, pool_type: str, clip_id: str, strategy: str) -> Optional[dict]:
        key = self.key(pool_type, clip_id, strategy)
        
        # L1
        if key in self._memory:
            return self._memory[key]
        
        # L2
        if self._redis:
            cached = await self._redis.get(key)
            if cached:
                result = json.loads(cached)
                self._memory[key] = result  # Promote to L1
                return result
        
        return None
    
    async def set(self, pool_type: str, clip_id: str, strategy: str, result: dict, ttl: int = 3600):
        key = self.key(pool_type, clip_id, strategy)
        
        # L1 + L2
        self._memory[key] = result
        if self._redis:
            await self._redis.setex(key, ttl, json.dumps(result))
```

### Cache Invalidation Rules

- **Transcript analysis**: Cache 24h (content doesn't change)
- **Hook generation**: Cache 1h (same clip + same persona = same result)
- **Safety screening**: Cache 72h (content is static)
- **Segment analysis**: Cache 12h (source video is static)
- **A/B test results**: Cache 7d (historical data)

---

## 5. Genetic Agent Evolution

### Evolving Hook Personas

```python
class GeneticHookPersona:
    """A hook persona that evolves based on performance data."""
    
    def __init__(self, base_persona: str, generation: int = 0):
        self.base = base_persona
        self.generation = generation
        self.mutation_rate = 0.1 * (1 + generation * 0.05)
        self.traits = self._derive_traits(base_persona)
        self.fitness_history: List[float] = []
    
    def _derive_traits(self, persona: str) -> dict:
        """Decompose a persona into adjustable traits."""
        return {
            "urgency": random.uniform(0.3, 0.9),
            "curiosity_gap": random.uniform(0.2, 0.8),
            "emotional_valence": random.uniform(-0.5, 0.5),
            "length_preference": random.choice(["short", "medium", "long"]),
            "question_ratio": random.uniform(0.0, 0.5),
        }
    
    def mutate(self) -> "GeneticHookPersona":
        """Create a mutated offspring."""
        child = GeneticHookPersona(self.base, self.generation + 1)
        
        for trait, value in self.traits.items():
            if random.random() < self.mutation_rate:
                if isinstance(value, float):
                    child.traits[trait] = max(0, min(1, value + random.gauss(0, 0.15)))
                elif isinstance(value, str):
                    child.traits[trait] = random.choice(["short", "medium", "long"])
        
        return child
    
    def update_fitness(self, retention_score: float):
        """Record performance for this persona."""
        self.fitness_history.append(retention_score)
        # Decay old scores
        if len(self.fitness_history) > 50:
            self.fitness_history = self.fitness_history[-50:]
```

### Population Management

```python
class HookPersonaPopulation:
    """Manages a population of evolving hook personas per user."""
    
    POPULATION_SIZE = 20
    ELITE_COUNT = 3
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.personas: List[GeneticHookPersona] = []
        self.generation = 0
    
    async def evolve(self, performance_data: List[dict]):
        """Evolve population based on recent performance."""
        # Update fitness for each persona
        for persona in self.personas:
            matching = [p for p in performance_data if p["persona"] == persona.base]
            if matching:
                avg_retention = sum(p["retention"] for p in matching) / len(matching)
                persona.update_fitness(avg_retention)
        
        # Sort by fitness
        self.personas.sort(key=lambda p: p.average_fitness(), reverse=True)
        
        # Keep elites
        elites = self.personas[:self.ELITE_COUNT]
        
        # Generate offspring through mutation and crossover
        offspring = []
        while len(offspring) < (self.POPULATION_SIZE - self.ELITE_COUNT):
            parent = random.choice(elites)
            child = parent.mutate()
            offspring.append(child)
        
        self.personas = elites + offspring
        self.generation += 1
        
        # Persist
        await self._save_population()
```

---

## 6. Tier Scaling for 100+ Clip Operations

### Current vs Future Tier Limits

| Tier | Agents | Clip Batch | Cost/100 Clips (Hook) | Cost/100 Clips (Remix) |
|------|--------|-----------|----------------------|----------------------|
| Free | 1 | 5 | $0.25 | $1.00 |
| Basic | 2 | 10 | $0.50 | $2.00 |
| Pro | 5 | 25 | $1.25 | $5.00 |
| Enterprise | 10 | 100 | $5.00 | $20.00 |
| **Scale** | **50** | **500** | **$25.00** | **$100.00** |
| **Mega** | **100** | **1000** | **$50.00** | **$200.00** |

### Batch Pricing Model

Instead of per-agent pricing, offer **per-batch pricing**:

```python
BATCH_COSTS = {
    "hook": {
        "base": 50,      # $0.50 base for batch
        "per_clip": 3,   # $0.03 per clip
        "per_agent": 2,  # $0.02 per agent (sub-linear)
    },
    "remix": {
        "base": 200,
        "per_clip": 15,
        "per_agent": 5,
    },
    # ... etc
}

def calculate_batch_cost(pool_type: str, clip_count: int, agent_count: int) -> int:
    pricing = BATCH_COSTS[pool_type]
    return (
        pricing["base"] +
        pricing["per_clip"] * clip_count +
        pricing["per_agent"] * agent_count
    )
```

**Result:** 100 clips × 5 agents for hooks = $0.50 + $3.00 + $0.10 = **$3.60** (vs $25 at old pricing)

---

## 7. Implementation Roadmap

### Phase 1: Batch Endpoints (Week 1)
- [ ] Add `/swarm/batch` endpoint
- [ ] Add `BatchContext` shared analysis
- [ ] Update frontend to support multi-select clips

### Phase 2: Caching Layer (Week 2)
- [ ] Integrate Redis for L2 cache
- [ ] Add cache keys to all swarm operations
- [ ] Cache invalidation on clip update

### Phase 3: Smart Defaults (Week 3)
- [ ] Rule-based fallback when AI budget exhausted
- [ ] Top-K selection (only AI-process best clips)
- [ ] Shared context across same-source clips

### Phase 4: Genetic Evolution (Week 4)
- [ ] Implement `GeneticHookPersona`
- [ ] Add performance tracking tables
- [ ] Evolution loop on weekly basis

### Phase 5: Mega Tier (Week 5)
- [ ] Add "Scale" and "Mega" tiers
- [ ] Batch UI for 100+ clip selection
- [ ] Progress tracking for long batches

---

## 8. Database Schema Additions

```sql
-- Batch job tracking
CREATE TABLE IF NOT EXISTS public.swarm_batch_jobs (
    batch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    pool_type TEXT NOT NULL,
    clip_ids UUID[] NOT NULL,
    total_clips INTEGER NOT NULL,
    processed_clips INTEGER DEFAULT 0,
    status TEXT DEFAULT 'queued',
    shared_context JSONB DEFAULT '{}',
    cost_cents INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Performance tracking for genetic evolution
CREATE TABLE IF NOT EXISTS public.swarm_agent_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    agent_persona TEXT NOT NULL,
    pool_type TEXT NOT NULL,
    job_id UUID REFERENCES public.swarm_jobs(job_id),
    clip_id UUID REFERENCES public.clips(id),
    retention_score FLOAT,
    engagement_score FLOAT,
    cost_cents INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cache entries
CREATE TABLE IF NOT EXISTS public.swarm_cache (
    cache_key TEXT PRIMARY KEY,
    pool_type TEXT NOT NULL,
    clip_id UUID REFERENCES public.clips(id),
    strategy_hash TEXT,
    result_data JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_swarm_cache_lookup ON public.swarm_cache(pool_type, clip_id, strategy_hash);
CREATE INDEX idx_swarm_cache_expires ON public.swarm_cache(expires_at);
CREATE INDEX idx_swarm_batch_jobs_user ON public.swarm_batch_jobs(user_id, created_at DESC);
CREATE INDEX idx_swarm_performance_persona ON public.swarm_agent_performance(user_id, agent_persona, created_at DESC);
```

---

## 9. Frontend Batch UI

### Multi-Select Clip List

```tsx
// In pipeline or library view
const [selectedClips, setSelectedClips] = useState<string[]>([]);
const [batchModalOpen, setBatchModalOpen] = useState(false);

// Long-press or checkbox to select
const toggleClip = (id: string) => {
  setSelectedClips(prev => 
    prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
  );
};

// Batch action bar appears when clips selected
{selectedClips.length > 0 && (
  <View style={styles.batchBar}>
    <Text>{selectedClips.length} clips selected</Text>
    <TouchableOpacity onPress={() => setBatchModalOpen(true)}>
      <Text>Run Swarm Batch</Text>
    </TouchableOpacity>
  </View>
)}
```

### Batch Config Modal

```tsx
interface BatchSwarmConfig {
  clipIds: string[];
  poolType: SwarmPoolType;
  agentCount: number;
  strategyFilter: string[];
  priority: 'cost' | 'balanced' | 'speed';
  topK?: number;  // Only process top N clips
}
```

---

## 10. Cost Tracking Dashboard

Add a cost visibility screen so users understand their spend:

```tsx
// Cost breakdown per batch
const CostBreakdown = ({ batchJob }: { batchJob: SwarmBatchJob }) => (
  <View>
    <Text>Batch Cost Breakdown</Text>
    <Text>Base fee: {batchJob.pricing.base}¢</Text>
    <Text>Per-clip: {batchJob.pricing.perClip}¢ × {batchJob.totalClips}</Text>
    <Text>Per-agent: {batchJob.pricing.perAgent}¢ × {batchJob.agentCount}</Text>
    <Text>Total: {batchJob.costCents}¢</Text>
    
    <Text>Savings vs individual: {batchJob.savingsPercent}%</Text>
  </View>
);
```

---

## Summary

To maximize capability while minimizing costs:

1. **Batch everything** — shared context reduces per-clip cost by ~60%
2. **Cache aggressively** — avoid re-analyzing the same content
3. **Tiered depth** — free gets rules, paid gets AI, enterprise gets swarms
4. **Sub-linear pricing** — batch discounts make 100 clips affordable
5. **Genetic evolution** — agents get better over time, reducing needed iterations
6. **Smart selection** — only deep-analyze top-performing candidates

The target is **$3-5 per 100 clips** for hook analysis at Pro tier, with genetic agents that improve weekly.
