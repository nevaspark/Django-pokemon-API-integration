# Pokedex — Engineering Resume

## Overview
- Animated background + high-contrast buttons (no Admin button).
- Error-handled JSON API with stable `image` field.
- Search + Type filter + **Ability dropdown** filter.
- Detail page with evolution chain and **Compare With** action.
- Compare any two Pokémon.
- Average Stats (UI + API) and Team Coverage (UI + API).
- CORS on for dev.

## Endpoints
- `/api/pokemon/?q=&type=&ability=&page=&page_size=`
- `/api/pokemon/<id|name>/`
- `/api/compare/?a=&b=`
- `/api/types/` and `/api/abilities/`
- `/api/evolution/<id|name>/`
- `/api/coverage/?team=a,b,c`
- `/api/average/?team=a,b,c`

## Run
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
Open http://127.0.0.1:8000/pokemon/
