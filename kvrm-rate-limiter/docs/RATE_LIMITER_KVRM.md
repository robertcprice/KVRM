# Rate Limiter KVRM - Comprehensive Documentation

## Critical Distinction: Decision Engine vs Enforcement

**KVRM is NOT a rate limiter.** It is a **decision engine** that predicts what action to take.

### What KVRM Does
- Takes structured input (user context, request info, system state, pattern flags)
- Outputs a **recommendation**: allow, throttle, block, captcha, etc.
- Runs in ~2.7ms with 99.1% accuracy on test scenarios

### What KVRM Does NOT Do
- Track state per user/IP (you need Redis, database, or in-memory store)
- Enforce delays (the caller must implement actual sleep/queue logic)
- Block connections (needs integration with load balancer/reverse proxy)
- Maintain sliding windows (requires external time-series tracking)

### How KVRM Would Integrate With Actual Rate Limiting

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION RATE LIMITING SYSTEM                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │ Incoming │───▶│ State Lookup │───▶│ KVRM Decision Engine     │  │
│  │ Request  │    │ (Redis/DB)   │    │ (Neural Network)         │  │
│  └──────────┘    │              │    │                          │  │
│                  │ • user_id    │    │ Input: RateLimitInput    │  │
│                  │ • req/min    │    │ Output: Action + params  │  │
│                  │ • req/hour   │    │                          │  │
│                  │ • history    │    │ ~2.7ms latency           │  │
│                  └──────────────┘    └──────────────────────────┘  │
│                                                │                    │
│                                                ▼                    │
│                                      ┌──────────────────┐          │
│                                      │ Action Enforcer  │          │
│                                      ├──────────────────┤          │
│                                      │ ALLOW → pass     │          │
│                                      │ THROTTLE → delay │          │
│                                      │ BLOCK → 429      │          │
│                                      │ CAPTCHA → verify │          │
│                                      └──────────────────┘          │
│                                                │                    │
│                                                ▼                    │
│                                      ┌──────────────────┐          │
│                                      │ Backend Service  │          │
│                                      └──────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

## Scenario Definitions

The KVRM is trained to distinguish between these scenarios based on **concrete, measurable criteria**:

### 1. Normal Traffic (55% of training data)

**Light Usage** (25%)
- requests_last_minute: 0-5
- requests_last_hour: 0-50
- account_age_days: 30+
- request_variance: 0.5-2.0 (natural human variation)
- ip_reputation_score: 0.8-1.0
- No abuse flags

**Moderate Usage** (20%)
- requests_last_minute: 5-20
- requests_last_hour: 50-300
- Same healthy indicators as light

**Heavy Usage** (10%)
- requests_last_minute: 20-80
- requests_last_hour: 500-1500
- tier: Professional or Enterprise
- account_age_days: 180+ (established user)

### 2. Legitimate Burst (10% of training data)

**Definition**: Sudden spike from a trusted user (e.g., product launch, viral moment)

**Concrete Criteria**:
- requests_last_minute: 30-100 (high, but not extreme)
- account_age_days: 90-500 (established account)
- previous_throttles: 0-1 (good history)
- ip_reputation_score: 0.85-1.0 (trusted IP)
- burst_detected: TRUE
- scripted_behavior: FALSE (human patterns)

**Expected Action**: ALLOW or WARN (trust the established user)

### 3. Suspicious Burst (Subset of "suspicious_burst" scenarios)

**Definition**: A burst pattern with indicators suggesting possible abuse

**Concrete Criteria** (ALL must be true):
- burst_detected: TRUE
- account_age_days: < 90 (newer account)
- PLUS one or more of:
  - ip_reputation_score: < 0.7
  - request_variance: < 0.5 (too consistent, bot-like)
  - previous_throttles: > 2
  - scripted_behavior: TRUE

**Why It's Different From "Legitimate Burst"**:
| Factor | Legitimate Burst | Suspicious Burst |
|--------|------------------|------------------|
| Account age | 90+ days | < 90 days |
| IP reputation | 0.85+ | < 0.7 |
| Request variance | 0.5+ (human) | < 0.5 (bot-like) |
| Previous throttles | 0-1 | 2+ |
| Scripted behavior | FALSE | TRUE |

**Expected Action**: THROTTLE_SOFT or THROTTLE_HARD (slow down until we know intent)

### 4. Scraping Pattern (5% of training data)

**Definition**: Systematic data extraction, typically from bots

**Concrete Criteria**:
- scraping_pattern: TRUE (flagged by upstream pattern detector)
- tier: FREE or BASIC (not paying for API access)
- requests_last_minute: 50-200
- requests_last_hour: 500-3000
- request_variance: 0.1-0.5 (very consistent timing)
- account_age_days: 1-30 (new account)
- previous_throttles: 2-10 (already been warned)
- ip_reputation_score: 0.2-0.6 (known scraper IPs)
- scripted_behavior: TRUE

**Expected Action**: THROTTLE_HARD or BLOCK_TEMPORARY

### 5. Credential Stuffing (3% of training data)

**Definition**: Automated login attempts with stolen credentials

**Concrete Criteria**:
- credential_stuffing_pattern: TRUE
- endpoint: /api/v1/auth/login
- requests_last_minute: 20-100 (rapid fire logins)
- error_rate_last_minute: 0.3-0.7 (many failed attempts)
- ip_reputation_score: 0.0-0.3 (very bad IP)
- request_variance: 0.05-0.2 (extremely consistent, automated)
- new_ip: TRUE
- account_age_days: 0-10

**Expected Action**: BLOCK_EXTENDED or CAPTCHA

### 6. DDoS Pattern (2% of training data)

**Definition**: Denial of service attack pattern

**Concrete Criteria**:
- requests_last_minute: 100-500
- requests_last_hour: 1000-10000
- requests_last_day: 5000-50000
- system.current_load: 0.8-1.0 (system stressed)
- ip_reputation_score: 0.0-0.2
- request_variance: 0.0-0.1 (perfectly consistent)
- previous_throttles: 5-20
- previous_blocks: 2-10

**Expected Action**: BLOCK_EXTENDED

### 7. System Overload (5% of training data)

**Definition**: System under stress, even good users may need throttling

**Concrete Criteria**:
- system.current_load: 0.85-0.98
- system.available_capacity_percent: 5-20%
- User can be any tier/profile (overload affects everyone)

**Expected Action**:
- Enterprise users: ALLOW (priority access)
- Others: THROTTLE_SOFT or THROTTLE_HARD based on severity

### 8. New User (8% of training data)

**Definition**: Account too new to have trust signals

**Concrete Criteria**:
- account_age_days: 0-7
- new_ip: TRUE
- ip_reputation_score: 0.5-0.9 (uncertain)

**Expected Action**: Based on behavior
- Low activity → ALLOW
- High activity + bad signals → THROTTLE_SOFT
- High activity + good signals → WARN

### 9. Premium User (7% of training data)

**Definition**: Enterprise tier with established trust

**Concrete Criteria**:
- tier: ENTERPRISE
- payment_current: TRUE
- account_age_days: 365+
- previous_throttles: 0

**Expected Action**: ALLOW (even for bursts)

## Threat Score Calculation

The KVRM learns to compute an implicit "threat score" from these weighted factors:

```python
def _compute_threat_score(input_data) -> float:
    """
    Threat score from 0 (safe) to 1 (definite abuse).
    This is what the neural network learns to approximate.
    """
    score = 0.0

    # Abuse pattern flags (hard signals)
    if credential_stuffing_pattern: score += 0.5
    if scraping_pattern: score += 0.3
    if scripted_behavior: score += 0.2

    # IP reputation (soft signal)
    score += (1.0 - ip_reputation_score) * 0.3

    # History of abuse
    score += min(previous_throttles / 10, 0.3)
    score += min(previous_blocks / 5, 0.3)

    # New account + high activity (suspicious combo)
    if account_age_days < 7 and requests_last_minute > 20:
        score += 0.2

    # Bot-like consistency
    if request_variance < 0.5 and requests_last_minute > 30:
        score += 0.15

    return min(score, 1.0)
```

## Why KVRM vs Rule-Based?

### The Problem With Rules

Traditional rate limiting uses fixed rules:
```python
if requests_per_minute > 60:
    return BLOCK
elif requests_per_minute > 30:
    return THROTTLE
```

This fails for:
- **Legitimate burst**: Good user hits 100 req/min during product launch → wrongly blocked
- **Sneaky scraper**: Bot stays at 29 req/min to avoid detection → never caught
- **Context blindness**: Ignores account age, IP reputation, system load

### What KVRM Learns

KVRM learns the **interaction of 30+ features simultaneously**:

| Rules Can't Handle | KVRM Can |
|-------------------|----------|
| "High traffic from old account with good IP" = OK | ✅ Learns trust signals |
| "Moderate traffic from new account at 3am from bad IP" = suspicious | ✅ Learns suspicion signals |
| "Enterprise user during system overload" = prioritize | ✅ Learns tier-based priority |
| "Previous abuser now behaving well" = cautious allow | ✅ Learns rehabilitation |

### Results Comparison

| Method | Accuracy | Suspicious Burst | Legitimate Burst |
|--------|----------|------------------|------------------|
| Token Bucket | 70.3% | 0% (can't distinguish) | 45.6% |
| Rule-Based | 81.1% | 0% (same rules for both) | 45.6% |
| **KVRM** | **99.1%** | **100%** | **100%** |

## Implementation Checklist

To build a complete rate limiting system with KVRM:

### Required Infrastructure (NOT provided by KVRM)
- [ ] State store (Redis/Memcached) for per-user counters
- [ ] Time-series tracking for requests_last_minute/hour/day
- [ ] IP reputation service or database
- [ ] Pattern detection for scraping/credential_stuffing flags
- [ ] Request queue for enforcing delays
- [ ] Connection handler for 429 responses

### KVRM Provides
- [x] Decision engine (99.1% accuracy)
- [x] Sub-3ms inference latency
- [x] Multi-factor judgment (30+ features)
- [x] Trained model weights (2.65 MB)

### Integration Code Example

```python
from kvrm_rate_limiter import RateLimiterInference
from my_infrastructure import RedisStateStore, IPReputationService

# Initialize
kvrm = RateLimiterInference(model_path="models/best.pt", use_lite=True)
state_store = RedisStateStore()
ip_service = IPReputationService()

def rate_limit_middleware(request):
    # 1. Gather state (YOUR infrastructure)
    user_state = state_store.get_user_state(request.user_id)
    ip_rep = ip_service.get_score(request.ip)

    # 2. Build KVRM input
    kvrm_input = RateLimitInput(
        request=RequestContext(...),
        user=UserContext(
            user_id=request.user_id,
            requests_last_minute=user_state.req_per_min,  # From Redis
            # ... more fields from your state store
        ),
        patterns=PatternFlags(
            ip_reputation_score=ip_rep,  # From your IP service
            # ... more pattern flags from your detection systems
        ),
    )

    # 3. Get KVRM decision (~2.7ms)
    decision = kvrm.predict(kvrm_input)

    # 4. Enforce decision (YOUR infrastructure)
    if decision.action == Action.BLOCK_TEMPORARY:
        return Response(status=429, retry_after=decision.quota_reset_seconds)
    elif decision.action == Action.THROTTLE_HARD:
        time.sleep(decision.delay_ms / 1000)  # Your enforcement
        return proceed_with_request()
    # ... etc
```

## Model Details

- **Architecture**: Transformer encoder with multi-head output
- **Parameters**: 686,903
- **Size**: 2.65 MB
- **Inference**: ~2.7ms (MPS), ~1ms (CUDA)
- **Training**: 30 epochs, 10k samples, ~2 minutes on M4 Pro

## Project Location

```
/Users/bobbyprice/projects/KVRM/kvrm-rate-limiter/
├── src/
│   ├── model.py          # Neural network architecture
│   ├── tokenizer.py      # Input/output encoding
│   ├── inference.py      # Production inference engine
│   ├── baseline.py       # Traditional rate limiters for comparison
│   └── schemas.py        # Input/output data structures
├── data/
│   ├── generator.py      # Synthetic training data
│   ├── train.jsonl       # 10k training samples
│   └── val.jsonl         # 2k validation samples
├── scripts/
│   ├── train.py          # Training script
│   └── evaluate.py       # Evaluation vs baselines
└── models/
    └── best.pt           # Trained model (97.8% val accuracy)
```
