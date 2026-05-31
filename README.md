# ⚄ Arcane Dice — DnD Dice Roller

A full-stack DnD dice rolling application with a REST API, animated web UI, and complete Docker setup.

## Quick Start

```bash
git clone <repo>
cd dnd-dice
docker compose up --build
```

Open **http://localhost:8080** in your browser.

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Browser  →  http://localhost:8080      │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │  frontend (nginx:alpine)  :80    │   │
│  │  - Serves index.html             │   │
│  │  - Proxies /roll/* → api:8000    │   │
│  └──────────────┬───────────────────┘   │
│                 │  internal network     │
│  ┌──────────────▼───────────────────┐   │
│  │  api (python:3.12-slim)  :8000   │   │
│  │  - FastAPI + Uvicorn             │   │
│  │  - Random dice rolling logic     │   │
│  │  - /docs (Swagger UI)            │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## API Reference

### `GET /roll/{notation}`
Quick roll via URL path.

```bash
curl http://localhost:8080/roll/d20
curl http://localhost:8080/roll/2d6+3
curl http://localhost:8080/roll/4d6kh3
curl "http://localhost:8080/roll/d20?label=Attack+Roll"
```

### `POST /roll`
Roll with full request body.

```bash
curl -X POST http://localhost:8080/roll \
  -H "Content-Type: application/json" \
  -d '{"notation": "2d6+3", "label": "Fireball Damage"}'
```

**Response:**
```json
{
  "notation": "2d6+3",
  "label": "Fireball Damage",
  "dice_results": [
    {"die": 6, "value": 4, "kept": true},
    {"die": 6, "value": 5, "kept": true}
  ],
  "modifier": 3,
  "subtotal": 9,
  "total": 12,
  "breakdown": "(4+5) + 3 = 12",
  "success": true
}
```

### `POST /roll/multi`
Roll multiple dice groups at once.

```bash
curl -X POST http://localhost:8080/roll/multi \
  -H "Content-Type: application/json" \
  -d '[
    {"notation": "4d6kh3", "label": "Strength"},
    {"notation": "4d6kh3", "label": "Dexterity"},
    {"notation": "4d6kh3", "label": "Constitution"},
    {"notation": "4d6kh3", "label": "Intelligence"},
    {"notation": "4d6kh3", "label": "Wisdom"},
    {"notation": "4d6kh3", "label": "Charisma"}
  ]'
```

### `GET /dice`
Returns all supported dice and notation examples.

---

## Supported Dice Notation

| Notation     | Meaning                             |
|--------------|-------------------------------------|
| `d20`        | Single d20                          |
| `2d6`        | Two d6                              |
| `4d6kh3`     | Roll 4d6, keep highest 3            |
| `2d20kh1`    | Advantage (roll 2d20, keep highest) |
| `2d20kl1`    | Disadvantage (roll 2d20, keep lowest)|
| `1d8+5`      | d8 plus +5 modifier                 |
| `2d6-1`      | Two d6 minus 1                      |
| `1d100`      | Percentile (d100)                   |

**Valid die types:** d2, d4, d6, d8, d10, d12, d20, d100

---

## Swagger UI

Interactive API docs available at: **http://localhost:8080/docs**

---

## Development

### Run API only (without Docker)
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Run with Docker Compose (detached)
```bash
docker compose up -d --build
```

### Stop
```bash
docker compose down
```

### Logs
```bash
docker compose logs -f
```
