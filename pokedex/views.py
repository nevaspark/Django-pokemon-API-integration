from django.shortcuts import render, redirect
from django.conf import settings
import logging
from . import services
from .utils import (
    validate_pokemon_name, validate_team_names, validate_page_number, 
    validate_page_size, sanitize_query_param, log_api_request, handle_api_errors
)

logger = logging.getLogger(__name__)

@log_api_request
@handle_api_errors
def pokemon_list(request):
    error = None
    try:
        types = services.get_types().get("results", [])
        abilities = services.get_all_abilities()
    except Exception as e:
        types, abilities = [], []
        error = f"Failed to load filter lists: {e}"

    q = sanitize_query_param(request.GET.get("q"))
    type_name = sanitize_query_param(request.GET.get("type"))
    ability = sanitize_query_param(request.GET.get("ability"))
    page = validate_page_number(request.GET.get("page", "1"))
    page_size = validate_page_size(request.GET.get("page_size", str(settings.PAGE_SIZE)))

    try:
        if type_name:
            data = services.filter_pokemon_by_type(type_name, page=page, page_size=page_size)
            results = data["results"]; total = data["count"]
        elif ability:
            data = services.filter_pokemon_by_ability(ability, page=page, page_size=page_size)
            results = data["results"]; total = data["count"]
        elif q:
            data = services.search_pokemon(q, page=page, page_size=page_size)
            results = data["results"]; total = data["count"]
        else:
            offset = (page-1) * page_size
            data = services.list_pokemon(offset=offset, limit=page_size)
            total = data.get("count", 0)
            results = []
            for item in data.get("results", []):
                try:
                    results.append(services.get_pokemon(item["name"]))
                except Exception:
                    pass
        has_next = page * page_size < total
        has_prev = page > 1
    except services.PokeAPIError as e:
        error = str(e)
        results, total, has_next, has_prev = [], 0, False, False

    return render(request, "pokedex/list.html", {
        "types": types,
        "abilities": abilities,
        "pokemon_list": results,
        "page": page, "page_size": page_size,
        "has_next": has_next, "has_prev": has_prev,
        "q": q or "", "type_selected": type_name or "", "ability_selected": ability or "",
        "total": total, "error": error,
    })

@log_api_request
@handle_api_errors
def pokemon_detail(request, identifier):
    error = None
    try:
        identifier = validate_pokemon_name(identifier) if isinstance(identifier, str) else str(identifier)
        pokemon = services.get_pokemon(identifier)
        species = services.get_pokemon_species(identifier)
        evolution_names = services.evo_chain_names(services.get_evolution_chain_by_pokemon(identifier))
    except Exception as e:
        logger.error(f"Failed to load Pokemon {identifier}: {e}")
        pokemon, species, evolution_names = None, None, []
        error = f"Could not load Pokémon: {e}"

    if request.GET.get("compare_with"):
        other = request.GET["compare_with"].strip()
        if other:
            return redirect(f"/compare/?a={identifier}&b={other}")

    return render(request, "pokedex/detail.html", {
        "pokemon": pokemon, "species": species, "evolution_names": evolution_names, "error": error
    })

# def compare_view(request):
#     a = request.GET.get("a", "").strip() or "pikachu"
#     b = request.GET.get("b", "").strip() or "bulbasaur"
#     error = None
#     try:
#         pa = services.get_pokemon(a)
#         pb = services.get_pokemon(b)
#     except Exception as e:
#         pa = pb = None
#         error = f"Compare failed: {e}"
#     return render(request, "pokedex/compare.html", {"a": pa, "b": pb, "a_name": a, "b_name": b, "error": error})
def compare_view(request):
    a_name = sanitize_query_param(request.GET.get("a") or "pikachu")
    b_name = sanitize_query_param(request.GET.get("b") or "bulbasaur")

    error = None
    try:
        a_name = validate_pokemon_name(a_name)
        a = services.get_pokemon(a_name)
    except Exception as e:
        a, error = None, f"Couldn't load {a_name}: {e}"
        logger.warning(f"Failed to load Pokemon A: {a_name} - {e}")
    
    try:
        b_name = validate_pokemon_name(b_name)
        b = services.get_pokemon(b_name)
    except Exception as e:
        b = None
        error = (error + " | " if error else "") + f"Couldn't load {b_name}: {e}"
        logger.warning(f"Failed to load Pokemon B: {b_name} - {e}")

    # 👉 pass a real list to the template
    pair = [p for p in (a, b) if p]

    return render(
        request,
        "pokedex/compare.html",
        {"pair": pair, "a_name": a_name, "b_name": b_name, "error": error},
    )

@log_api_request
@handle_api_errors
def coverage_view(request):
    team_param = request.GET.get("team", "pikachu,bulbasaur,charizard")
    names = [x.strip() for x in team_param.split(",") if x.strip()]
    error = None
    
    try:
        validated_names = validate_team_names(names)
        summary = services.team_coverage(validated_names)
    except Exception as e:
        logger.error(f"Coverage calculation failed: {e}")
        summary = {}
        error = f"Coverage failed: {e}"
        validated_names = names[:6]
    
    return render(request, "pokedex/coverage.html", {"team": validated_names, "summary": summary, "error": error})

@log_api_request
@handle_api_errors
def average_view(request):
    team_param = request.GET.get("team", "pikachu,bulbasaur,charizard")
    names = [x.strip() for x in team_param.split(",") if x.strip()]
    error = None
    
    try:
        validated_names = validate_team_names(names)
        avg = services.average_stats(validated_names)
    except Exception as e:
        logger.error(f"Average stats calculation failed: {e}")
        avg = {}
        error = f"Average calc failed: {e}"
        validated_names = names[:6]
    
    return render(request, "pokedex/average.html", {"team": validated_names, "avg": avg, "error": error})

@log_api_request
@handle_api_errors
def evolution_view(request, identifier):
    try:
        identifier = validate_pokemon_name(identifier) if isinstance(identifier, str) else str(identifier)
        evo = services.get_evolution_chain_by_pokemon(identifier)
    except Exception as e:
        logger.error(f"Failed to load evolution chain for {identifier}: {e}")
        evo = {"error": str(e)}
    return render(request, "pokedex/evolution.html", {"evo": evo})
