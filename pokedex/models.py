from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class Pokemon(models.Model):
    """Cached Pokemon data from PokeAPI"""
    pokemon_id = models.PositiveIntegerField(unique=True, validators=[MinValueValidator(1)])
    name = models.CharField(max_length=100)
    height = models.PositiveIntegerField(null=True, blank=True)
    weight = models.PositiveIntegerField(null=True, blank=True)
    base_experience = models.PositiveIntegerField(null=True, blank=True)
    sprites = models.JSONField(default=dict)
    types = models.JSONField(default=list)
    abilities = models.JSONField(default=list)
    stats = models.JSONField(default=dict)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pokemon_id']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['pokemon_id']),
        ]

    def __str__(self):
        return f"{self.name} (#{self.pokemon_id})"

    def get_main_type(self):
        """Get the primary type of the Pokemon"""
        if self.types and len(self.types) > 0:
            return self.types[0]['type']['name']
        return None

    def get_stat(self, stat_name):
        """Get a specific stat value"""
        return self.stats.get(stat_name, 0)


class PokemonSpecies(models.Model):
    """Cached Pokemon species data"""
    pokemon = models.OneToOneField(Pokemon, on_delete=models.CASCADE, related_name='species')
    name = models.CharField(max_length=100)
    flavor_text = models.TextField(blank=True)
    generation = models.CharField(max_length=50, blank=True)
    habitat = models.CharField(max_length=50, blank=True)
    is_legendary = models.BooleanField(default=False)
    is_mythical = models.BooleanField(default=False)
    evolution_chain_url = models.URLField(blank=True)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pokemon__pokemon_id']

    def __str__(self):
        return f"{self.name} species"


class Type(models.Model):
    """Pokemon types"""
    name = models.CharField(max_length=50, unique=True)
    damage_relations = models.JSONField(default=dict)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name.capitalize()


class Ability(models.Model):
    """Pokemon abilities"""
    name = models.CharField(max_length=100, unique=True)
    effect_text = models.TextField(blank=True)
    is_main_series = models.BooleanField(default=True)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name.replace('-', ' ').title()


class EvolutionChain(models.Model):
    """Evolution chain data"""
    chain_id = models.PositiveIntegerField(unique=True, validators=[MinValueValidator(1)])
    chain_data = models.JSONField(default=dict)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['chain_id']

    def __str__(self):
        return f"Evolution Chain #{self.chain_id}"

    def get_evolution_names(self):
        """Extract all Pokemon names from the evolution chain"""
        names = []
        
        def walk(node):
            if node and 'species' in node:
                names.append(node['species']['name'])
            for nxt in node.get('evolves_to', []):
                walk(nxt)
        
        if self.chain_data and 'chain' in self.chain_data:
            walk(self.chain_data['chain'])
        
        return names


class UserTeam(models.Model):
    """User-created Pokemon teams for analysis"""
    name = models.CharField(max_length=100)
    pokemon_names = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Team: {self.name}"

    def get_pokemon_count(self):
        return len(self.pokemon_names)


class APIRequestLog(models.Model):
    """Log API requests for monitoring and debugging"""
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    status_code = models.PositiveIntegerField()
    response_time_ms = models.PositiveIntegerField()
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['endpoint']),
            models.Index(fields=['status_code']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code}"
