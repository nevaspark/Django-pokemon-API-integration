from django.urls import path
from . import views, api

urlpatterns = [
    path("pokemon/", views.pokemon_list, name="pokemon_list"),
    path("pokemon/<slug:identifier>/", views.pokemon_detail, name="pokemon_detail"),
    path("compare/", views.compare_view, name="compare"),
    path("coverage/", views.coverage_view, name="coverage"),
    path("average/", views.average_view, name="average"),
    path("api/abilities/", api.abilities_api, name="api_abilities"),
    path("api/evolution/<slug:identifier>/", api.evolution_api, name="api_evolution"),
    path("api/coverage/", api.coverage_api, name="api_coverage"),
    path("api/average/", api.average_api, name="api_average"),
]
