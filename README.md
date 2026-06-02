<div align="center">

# ⌬ Spatium Computationis

### **The Intelligence Contracting Platform for Furniture, Interiors & Field Operations**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)
[![Nova Sovereign](https://img.shields.io/badge/Intelligence-Nova%20Sovereign-blueviolet?style=for-the-badge)](https://github.com/FreddyCreates/Decentralized-Production-NOVA-Protocol)
[![Version](https://img.shields.io/badge/Version-0.5.0-orange?style=for-the-badge)]()

---

**Spatium Computationis** transforms chaotic project data — PDFs, emails, photos, quotes, field notes — into structured estimates, bid documents, install packets, and actionable intelligence. Purpose-built for the furniture, interiors, and commercial contracting industry.

[Getting Started](#-getting-started) · [Architecture](#-architecture) · [API Reference](#-api-reference) · [Agents](#-intelligent-agent-network) · [Defense](#-defense-system) · [Documentation](#-documentation)

</div>

---

## 🎯 What It Does

> **One sentence:** An activated computing ecosystem that sits between interior designers, furniture vendors, contractors, and field installers — compressing all project information into estimates, documents, instructions, updates, and execution-ready intelligence.

### The Problem

Furniture and interiors contracting involves dozens of stakeholders — designers, dealers, vendors, manufacturers, installers, project managers, and clients — all exchanging information in incompatible formats. Critical data lives in emails, PDFs, handwritten notes, photos, and spreadsheets. Estimates are slow. Field coordination breaks down. Money leaks through the cracks.

### The Solution

Spatium Computationis is the **intelligence layer** between design intent and field execution. It ingests any format, routes data through specialized AI agents, and produces production-ready outputs:

| Input | → | Output |
|-------|---|--------|
| Furniture schedules, vendor quotes | → | **Furniture budgets & estimates** |
| Project scope, labor assumptions | → | **Labor bids & crew plans** |
| Designer drawings, room specs | → | **Install packets & field instructions** |
| Field photos, installer notes | → | **Punch lists & completion reports** |
| Change requests, RFIs | → | **Change orders & formal documents** |
| Project history, past bids | → | **Intelligent pricing & recommendations** |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SPATIUM COMPUTATIONIS ⌬                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐               │
│  │  →⌬ INGEST  │───▶│ ⌬ COMPRESS   │───▶│ ≡ ROUTE     │               │
│  │  (Any Input)│    │ (Intelligence)│    │ (Classify)  │               │
│  └─────────────┘    └──────────────┘    └──────┬──────┘               │
│                                                  │                      │
│         ┌────────────────────────────────────────┼───────────┐         │
│         ▼              ▼              ▼          ▼           ▼         │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌─────┐  ┌────────┐    │
│  │ ◈$ Furn.  │  │ ⚒$ Labor  │  │ ⟁✓ Field │  │ ▣✎  │  │ ✦⇄⚒   │    │
│  │ Estimator │  │ Estimator │  │ Inspector│  │Docs │  │Translate│    │
│  └───────────┘  └───────────┘  └──────────┘  └─────┘  └────────┘    │
│         │              │              │          │           │         │
│         └──────────────┴──────────────┴──────────┴───────────┘         │
│                                    │                                    │
│                          ┌─────────▼─────────┐                         │
│                          │  ⚡ ACTION OUTPUT  │                         │
│                          │  Estimates · Bids  │                         │
│                          │  Documents · Plans │                         │
│                          └─────────┬─────────┘                         │
│                                    │                                    │
│                          ┌─────────▼─────────┐                         │
│                          │  ↺ FIELD FEEDBACK  │                         │
│                          │  Reality → Memory  │                         │
│                          └───────────────────┘                         │
│                                                                         │
├────────────────────────────┬────────────────────────────────────────────┤
│  ⛨ DEFENSE SYSTEM          │  ⎈ PLATFORM SERVICES                      │
│  • Traffic Classification  │  • Agent Registry & Discovery              │
│  • Honeypot Network        │  • Task Queue & Delegation                 │
│  • Bot Fingerprinting      │  • Event Bus & Orchestration               │
│  • Cloudflare Edge Layer   │  • WebSocket Real-Time Feed                │
└────────────────────────────┴────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Nova Sovereign** intelligence backend ([setup guide](https://github.com/FreddyCreates/Decentralized-Production-NOVA-Protocol))

### Installation

```bash
# Clone the repository
git clone https://github.com/FreddyCreates/pegasus-battleops.git
cd pegasus-battleops

# Install dependencies
pip install -r spatium-computationis/requirements.txt

# Configure environment
export NOVA_SOVEREIGN_URL="https://your-nova-instance.com"
export NOVA_SOVEREIGN_TOKEN="your-auth-token"

# Launch the platform
uvicorn spatium_computationis.main:app --reload
```

### Verify Installation

```bash
curl http://localhost:8000/
# → {"system": "Spatium Computationis", "glyph": "⌬", "status": "active"}
```

---

## 📡 API Reference

### Core Pipeline

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ingest` | `POST` | Main intelligence pipeline — accepts any project input, returns actionable output |
| `/field-update` | `POST` | Field feedback loop — re-ingests field reality and cascades updates |
| `/memory/recall` | `POST` | Query project memory and historical intelligence |

### Direct Agent Endpoints

| Endpoint | Method | Agent | Description |
|----------|--------|-------|-------------|
| `/agents/estimate-furniture` | `POST` | Estimator Mobilia ◈$ | Generate furniture budgets & pricing |
| `/agents/estimate-labor` | `POST` | Estimator Laboris ⚒$ | Generate labor bids & crew plans |
| `/agents/punch-list` | `POST` | Inspector Campi ⟁✓ | Generate punch lists from field data |
| `/agents/install-packet` | `POST` | Interpres Designii ✦⇄⚒ | Create install packets from design intent |

### Defense & Platform

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ws/defense` | `WebSocket` | Real-time threat feed & defense metrics |
| `/api/defense/cloudflare/event` | `POST` | Cloudflare Worker webhook receiver |
| `/api/defense/cloudflare/rules` | `GET` | Cloudflare firewall rules template |
| `/api/platform/agents` | `GET` | List registered agents & capabilities |
| `/api/platform/tasks` | `POST` | Submit tasks to the delegation engine |

### Interactive Documentation

Once running, visit **http://localhost:8000/docs** for the full interactive Swagger UI.

---

## 🤖 Intelligent Agent Network

The platform operates through a hierarchical network of specialized AI agents:

### Prime Orchestrator

| Agent | Glyph | Function |
|-------|-------|----------|
| **Auctor Operis** | ⌬ | Master orchestration — routes data, identifies gaps, maintains project continuity |

### Core Estimating & Operations Agents

| Agent | Glyph | Function |
|-------|-------|----------|
| **Estimator Mobilia** | ◈$ | Furniture pricing, budgets, vendor quote normalization |
| **Estimator Laboris** | ⚒$ | Labor estimating, crew sizing, install scheduling |
| **Inspector Campi** | ⟁✓ | Field conditions, punch lists, completion verification |
| **Scriptor Documentorum** | ▣✎ | Document generation — bids, proposals, change orders, closeout packets |
| **Interpres Designii** | ✦⇄⚒ | Designer-to-field translation, install instructions |
| **Custos Memoriae** | ◉ | Project memory, historical patterns, client preferences |

### Extended Intelligence Agents

| Agent | Function |
|-------|----------|
| **Adaptio Mentis** | Adaptive learning — adjusts behavior from feedback patterns |
| **Adversary Lab** | Adversarial testing — stress-tests defenses and logic |
| **Analytics Inspector** | Performance metrics and project analytics |
| **Content Creator** | Marketing and project content generation |
| **Defensor Campi** | Field operations defense |
| **Error Eyes** | Anomaly detection and failure monitoring |
| **Gatekeeper Porta** | Access control and permission validation |
| **Marketing Strategist** | Outreach campaign planning and optimization |
| **Research Realm** | Market research, tools, and methods discovery |
| **SEO Optimizer** | Search visibility optimization |
| **Shadow Decryptor** | Unknown traffic analysis and classification |
| **Social Media Pilot** | Social presence management |
| **Vigil Operis** | Continuous health monitoring |
| **Webmaster GoDaddy** | Domain, DNS, and hosting management |

---

## 🛡️ Defense System

The integrated defense layer protects the platform with military-grade traffic classification:

```
                    ┌─────────────────┐
                    │  INCOMING TRAFFIC │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ ORGANISM CHARTER │
                    │  (Classifier)    │
                    └──┬─────┬─────┬──┘
                       │     │     │
              ┌────────┘     │     └────────┐
              ▼              ▼              ▼
     ┌──────────────┐ ┌───────────┐ ┌────────────┐
     │ COOPERATIVE  │ │  HOSTILE  │ │   SHADOW   │
     │ → Knowledge  │ │ → Adversary│ │ → Quarantine│
     │   Realm      │ │   Lab     │ │   + Decrypt │
     └──────────────┘ └───────────┘ └────────────┘
```

**Features:**
- 🕸️ **Honeypot Network** — Trap and analyze malicious actors
- 🔍 **Bot Fingerprinting** — Identify and classify automated traffic
- ☁️ **Cloudflare Edge Integration** — Block threats at the CDN level
- 📊 **Real-Time Dashboard** — Live threat visualization via WebSocket
- 🧬 **Behavioral Genome** — Pattern-based threat evolution tracking

---

## ⚖️ Governance

Authority is enforced through a 7-level hierarchy ensuring safe, ethical, and transparent operations:

| Level | Authority | Scope |
|-------|-----------|-------|
| 1 | **Constitutional** | Foundational rules — cannot be overridden |
| 2 | **Procedural** | Operational procedures and workflows |
| 3 | **Committee** | Multi-agent decision-making |
| 4 | **Personnel** | Agent roles and responsibilities |
| 5 | **Ethics** | Ethical constraints and guidelines |
| 6 | **Openness** | Transparency and data access policies |
| 7 | **Safety** | Safety constraints — has override power |

---

## 🔌 Intelligence Backend

Powered by **[Nova Sovereign](https://github.com/FreddyCreates/Decentralized-Production-NOVA-Protocol)** — a decentralized intelligence protocol providing reasoning, classification, summarization, and document generation capabilities.

### Configuration

| Variable | Description |
|----------|-------------|
| `NOVA_SOVEREIGN_URL` | Endpoint for the Nova Sovereign service |
| `NOVA_SOVEREIGN_TOKEN` | Authentication token |

---

## 📂 Project Structure

```
spatium-computationis/
├── main.py                    # FastAPI application entrypoint
├── schemas.py                 # Pydantic models & data contracts
├── requirements.txt           # Python dependencies
│
├── agents/                    # 🤖 Intelligent agent network
│   ├── auctor-operis/         #    Master orchestrator
│   ├── estimator-mobilia/     #    Furniture estimating
│   ├── estimator-laboris/     #    Labor estimating
│   ├── inspector-campi/       #    Field inspection
│   ├── scriptor-documentorum/ #    Document generation
│   ├── interpres-designii/    #    Design-to-field translation
│   ├── custos-memoriae/       #    Project memory
│   └── ... (14 more agents)
│
├── protocols/                 # ⚙️ Intelligence pipeline
│   ├── ingressus.py           #    →⌬ Information intake
│   ├── compressio.py          #    ⌬  Raw → compressed intelligence
│   ├── ordinatio.py           #    ≡  Route to correct region
│   ├── actio.py               #    ⚡ Action generation
│   ├── reductus.py            #    ↺  Field feedback loop
│   └── feedback.py            #    Outcome recording & learning
│
├── defense/                   # 🛡️ Security & threat management
│   ├── organism_charter.py    #    Traffic classification
│   ├── cloudflare-worker/     #    Edge defense
│   ├── honeypot/              #    Threat attraction
│   ├── fingerprinting/        #    Bot identification
│   └── threat_intel/          #    Intelligence feeds
│
├── governance/                # ⚖️ Authority & compliance
├── integrations/              # 🔌 External service connectors
├── platform/                  # ⎈  Registry, delegation, task queue
├── scaffolds/                 # 🧱 Agent lifecycle management
├── frontend/                  # 🖥️ Web UI & dashboard
├── documents/                 # 📄 Document generators
├── estimating/                # 💰 Pricing engines
└── field/                     # 📍 Field operations
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Architecture Charter](docs/CHARTER.md) | Full system charter and design philosophy |
| [API Guide](http://localhost:8000/docs) | Interactive Swagger documentation |
| [Agent Development](docs/AGENTS.md) | Guide to building custom agents |
| [Deployment Guide](docs/DEPLOY.md) | Production deployment instructions |

---

## 🔧 Development

```bash
# Run in development mode
uvicorn spatium_computationis.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest spatium-computationis/tests/

# Type checking
mypy spatium-computationis/
```

---

## 🌐 Industry Coverage

Spatium Computationis serves the complete **furniture, interiors, and commercial contracting** lifecycle:

- 🏢 **Commercial Office Furniture** — Dealer-to-installer coordination
- 🏥 **Healthcare & Hospitality** — Specialized install requirements
- 🏗️ **General Contracting** — Labor, scope, and bid management
- 🎨 **Interior Design Firms** — Design-to-execution bridge
- 🚚 **Logistics & Warehousing** — Delivery coordination and tracking
- 📐 **Architecture & Planning** — Specification management

---

<div align="center">

---

**⌬ Compressed Project Intelligence**

*Turning chaos into contracts since day one.*

Built with [FastAPI](https://fastapi.tiangolo.com) · Powered by [Nova Sovereign](https://github.com/FreddyCreates/Decentralized-Production-NOVA-Protocol)

---

© 2024–2026 FreddyCreates. All rights reserved.

</div>
