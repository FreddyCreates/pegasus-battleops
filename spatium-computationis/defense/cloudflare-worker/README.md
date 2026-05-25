# Spatium Computationis Defense Worker

⛨ **Cloudflare Edge Security Integration**

This Cloudflare Worker provides edge-level security for the Spatium Computationis AI defense system. It intercepts traffic at Cloudflare's global network before it reaches your origin server.

## Features

- **Bot Detection**: Uses Cloudflare's Bot Management to identify suspicious visitors
- **Threat Scoring**: Analyzes threat levels and makes real-time decisions
- **Honeypot Integration**: Routes attackers to honeypot endpoints for intelligence gathering
- **Challenge Pages**: Presents verification challenges to suspicious visitors
- **Telemetry**: Sends threat data to the Spatium API for analysis and learning

## Setup

### Prerequisites

- [Cloudflare Account](https://dash.cloudflare.com/sign-up)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- Node.js 18+

### Installation

```bash
# Navigate to the worker directory
cd spatium-computationis/defense/cloudflare-worker

# Install dependencies
npm install

# Login to Cloudflare
npx wrangler login
```

### Configuration

1. **Edit `wrangler.toml`**:
   - Update `name` if desired
   - Configure routes for your domain

2. **Set Secrets**:
   ```bash
   # API secret for Spatium backend
   npx wrangler secret put SPATIUM_API_SECRET
   
   # Webhook verification secret
   npx wrangler secret put WEBHOOK_SECRET
   ```

3. **Set Environment Variables**:
   ```bash
   npx wrangler secret put SPATIUM_API_URL
   # Enter: https://your-domain.com/api
   ```

### Development

```bash
# Start local development server
npm run dev

# The worker will be available at http://localhost:8787
```

### Deployment

```bash
# Deploy to Cloudflare
npm run deploy

# Or deploy to specific environment
npm run deploy:staging
npm run deploy:production
```

## Architecture

```
                    ┌─────────────────┐
                    │   Cloudflare    │
    Internet ──────►│     Edge        │
                    │   (Worker)      │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │  Block   │      │ Challenge│      │ Honeypot │
    │   Page   │      │   Page   │      │  Route   │
    └──────────┘      └──────────┘      └────┬─────┘
                                              │
                                              ▼
                                       ┌──────────┐
                                       │  Spatium │
                                       │   API    │
                                       │   ⌬      │
                                       └──────────┘
```

## Decision Logic

The worker makes decisions based on:

| Condition | Action |
|-----------|--------|
| Verified bot (Googlebot, etc.) | Allow |
| Threat score ≥ 80 | Block |
| Threat score ≥ 50 | Challenge |
| Bot score < 30 + honeypot path | Engage |
| Bot score < 30 | Challenge |
| Honeypot path + uncertain visitor | Route to honeypot |
| Scanner tool detected | Challenge/Engage |
| Default | Allow |

## Honeypot Paths

The worker recognizes these paths as honeypot targets:

- `/.env`, `/.env.local`, `/.env.production`
- `/config.php`, `/wp-config.php`
- `/wp-admin`, `/wp-login.php`
- `/phpmyadmin`, `/admin`, `/administrator`
- `/.git`, `/.git/config`, `/.git/HEAD`
- `/backup.sql`, `/database.sql`, `/db.sql`
- `/api/admin`, `/api/debug`, `/graphql`
- `/phpinfo.php`, `/server-status`

## Telemetry

The worker sends the following data to your Spatium API:

```typescript
{
  rayId: string;
  clientIP: string;
  path: string;
  method: string;
  userAgent: string | null;
  botScore: number;
  verifiedBot: boolean;
  threatScore: number;
  country: string;
  asn: number;
  asnOrg: string;
  ja3Hash: string | null;
  ja4: string | null;
  timestamp: string;
  decision: string;
  decisionReason: string;
  decisionConfidence: number;
}
```

## Glyphs

| Glyph | Meaning |
|-------|---------|
| ⛨ | Active defense |
| ◎ | Monitoring |
| ⚠ | Threat detected |
| ⌬ | Spatium Computationis |

## License

MIT
