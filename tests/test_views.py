import pytest
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, Mock
from pokedex import services
from pokedex.utils import PokeAPIError
import json


class TestViews(TestCase):
    
    def setUp(self):
        self.client = Client()
    
    @patch('pokedex.views.services.get_types')
    @patch('pokedex.views.services.get_all_abilities')
    def test_pokemon_list_view(self, mock_abilities, mock_types):
        """Test Pokemon list view"""
        mock_types.return_value = {
            'results': [
                {'name': 'electric'},
                {'name': 'fire'}
            ]
        }
        mock_abilities.return_value = ['static', 'blaze']
        
        response = self.client.get(reverse('pokemon_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'electric')
        self.assertContains(response, 'fire')
    
    @patch('pokedex.views.services.get_pokemon')
    @patch('pokedex.views.services.get_pokemon_species')
    @patch('pokedex.views.services.get_evolution_chain_by_pokemon')
    def test_pokemon_detail_view(self, mock_evo, mock_species, mock_pokemon):
        """Test Pokemon detail view"""
        mock_pokemon.return_value = {
            'id': 25,
            'name': 'pikachu',
            'types': [{'type': {'name': 'electric'}}]
        }
        mock_species.return_value = {
            'name': 'pikachu',
            'flavor_text_entries': [
                {'language': {'name': 'en'}, 'flavor_text': 'Mouse Pokemon'}
            ]
        }
        mock_evo.return_value = {'chain': {'species': {'name': 'pichu'}}}
        
        response = self.client.get(reverse('pokemon_detail', args=['pikachu']))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pikachu')
    
    @patch('pokedex.views.services.get_pokemon')
    def test_pokemon_detail_view_not_found(self, mock_pokemon):
        """Test Pokemon detail view with non-existent Pokemon"""
        mock_pokemon.side_effect = PokeAPIError("Not found")
        
        response = self.client.get(reverse('pokemon_detail', args=['nonexistent']))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Could not load Pokémon')
    
    @patch('pokedex.views.services.get_pokemon')
    def test_compare_view(self, mock_pokemon):
        """Test Pokemon comparison view"""
        mock_pokemon.side_effect = [
            {'id': 25, 'name': 'pikachu', 'stats': [{'stat': {'name': 'hp'}, 'base_stat': 35}]},
            {'id': 1, 'name': 'bulbasaur', 'stats': [{'stat': {'name': 'hp'}, 'base_stat': 45}]}
        ]
        
        response = self.client.get(reverse('compare_view') + '?a=pikachu&b=bulbasaur')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pikachu')
        self.assertContains(response, 'bulbasaur')
    
    @patch('pokedex.views.services.average_stats')
    def test_average_view(self, mock_average):
        """Test average stats view"""
        mock_average.return_value = {
            'hp': 40.0,
            'attack': 60.0,
            'defense': 50.0
        }
        
        response = self.client.get(reverse('average_view') + '?team=pikachu,bulbasaur')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '40.0')
        self.assertContains(response, '60.0')
    
    @patch('pokedex.views.services.team_coverage')
    def test_coverage_view(self, mock_coverage):
        """Test team coverage view"""
        mock_coverage.return_value = {
            'fire': {'weak': 2, 'resist': 1, 'immune': 0},
            'water': {'weak': 1, 'resist': 2, 'immune': 0}
        }
        
        response = self.client.get(reverse('coverage_view') + '?team=pikachu,bulbasaur')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'fire')
        self.assertContains(response, 'water')
    
    @patch('pokedex.views.services.get_evolution_chain_by_pokemon')
    def test_evolution_view(self, mock_evo):
        """Test evolution view"""
        mock_evo.return_value = {
            'chain': {
                'species': {'name': 'pichu'},
                'evolves_to': [
                    {
                        'species': {'name': 'pikachu'},
                        'evolves_to': [
                            {'species': {'name': 'raichu'}, 'evolves_to': []}
                        ]
                    }
                ]
            }
        }
        
        response = self.client.get(reverse('evolution_view', args=['pikachu']))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pichu')
        self.assertContains(response, 'pikachu')
        self.assertContains(response, 'raichu')


class TestAPIViews(TestCase):
    
    def setUp(self):
        self.client = Client()
    
    @patch('pokedex.api.services.get_pokemon')
    def test_pokemon_detail_api(self, mock_pokemon):
        """Test Pokemon detail API endpoint"""
        mock_pokemon.return_value = {
            'id': 25,
            'name': 'pikachu',
            'types': [{'type': {'name': 'electric'}}],
            'stats': [{'stat': {'name': 'hp'}, 'base_stat': 35}],
            'abilities': [{'ability': {'name': 'static'}}],
            'sprites': {'front_default': 'http://example.com/pikachu.png'}
        }
        
        response = self.client.get(reverse('pokemon_detail_api', args=['pikachu']))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['pokemon']['name'], 'pikachu')
        self.assertEqual(data['pokemon']['id'], 25)
    
    @patch('pokedex.api.services.get_pokemon')
    def test_pokemon_detail_api_not_found(self, mock_pokemon):
        """Test Pokemon detail API with non-existent Pokemon"""
        mock_pokemon.side_effect = PokeAPIError("Not found")
        
        response = self.client.get(reverse('pokemon_detail_api', args=['nonexistent']))
        
        self.assertEqual(response.status_code, 502)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    @patch('pokedex.api.services.get_pokemon')
    def test_compare_api(self, mock_pokemon):
        """Test compare API endpoint"""
        mock_pokemon.side_effect = [
            {
                'id': 25, 'name': 'pikachu', 'types': [{'type': {'name': 'electric'}}],
                'stats': [{'stat': {'name': 'hp'}, 'base_stat': 35}],
                'sprites': {'front_default': 'http://example.com/pikachu.png'}
            },
            {
                'id': 1, 'name': 'bulbasaur', 'types': [{'type': {'name': 'grass'}}],
                'stats': [{'stat': {'name': 'hp'}, 'base_stat': 45}],
                'sprites': {'front_default': 'http://example.com/bulbasaur.png'}
            }
        ]
        
        response = self.client.get(reverse('compare_api') + '?a=pikachu&b=bulbasaur')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['a']['name'], 'pikachu')
        self.assertEqual(data['b']['name'], 'bulbasaur')
    
    def test_compare_api_missing_params(self):
        """Test compare API with missing parameters"""
        response = self.client.get(reverse('compare_api') + '?a=pikachu')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    @patch('pokedex.api.services.get_types')
    def test_types_api(self, mock_types):
        """Test types API endpoint"""
        mock_types.return_value = {
            'results': [
                {'name': 'electric'},
                {'name': 'fire'},
                {'name': 'water'}
            ]
        }
        
        response = self.client.get(reverse('types_api'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 3)
    
    @patch('pokedex.api.services.get_all_abilities')
    def test_abilities_api(self, mock_abilities):
        """Test abilities API endpoint"""
        mock_abilities.return_value = ['static', 'blaze', 'overgrow']
        
        response = self.client.get(reverse('abilities_api'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['count'], 3)
        self.assertEqual(len(data['results']), 3)
    
    @patch('pokedex.api.services.average_stats')
    def test_average_api(self, mock_average):
        """Test average stats API endpoint"""
        mock_average.return_value = {
            'hp': 40.0,
            'attack': 60.0,
            'defense': 50.0
        }
        
        response = self.client.get(reverse('average_api') + '?team=pikachu,bulbasaur')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['average_stats']['hp'], 40.0)
        self.assertEqual(data['team'], ['pikachu', 'bulbasaur'])
    
    @patch('pokedex.api.services.team_coverage')
    def test_coverage_api(self, mock_coverage):
        """Test team coverage API endpoint"""
        mock_coverage.return_value = {
            'fire': {'weak': 2, 'resist': 1, 'immune': 0},
            'water': {'weak': 1, 'resist': 2, 'immune': 0}
        }
        
        response = self.client.get(reverse('coverage_api') + '?team=pikachu,bulbasaur')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('coverage', data)
        self.assertIn('fire', data['coverage'])
    
    @patch('pokedex.api.services.get_evolution_chain_by_pokemon')
    def test_evolution_api(self, mock_evo):
        """Test evolution API endpoint"""
        mock_evo.return_value = {
            'chain': {
                'species': {'name': 'pichu'},
                'evolves_to': [
                    {
                        'species': {'name': 'pikachu'},
                        'evolves_to': [
                            {'species': {'name': 'raichu'}, 'evolves_to': []}
                        ]
                    }
                ]
            }
        }
        
        response = self.client.get(reverse('evolution_api', args=['pikachu']))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['names'], ['pichu', 'pikachu', 'raichu'])


class TestInputValidation(TestCase):
    
    def setUp(self):
        self.client = Client()
    
    def test_xss_prevention(self):
        """Test that XSS attempts are sanitized"""
        response = self.client.get(reverse('pokemon_list') + '?q=<script>alert("xss")</script>')
        
        # Should not contain the script tag
        self.assertNotContains(response, '<script>')
        self.assertEqual(response.status_code, 200)
    
    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are handled"""
        response = self.client.get(reverse('pokemon_detail', args=["'; DROP TABLE users; --"]))
        
        # Should handle gracefully without crashing
        self.assertEqual(response.status_code, 200)
    
    def test_large_input_handling(self):
        """Test handling of very large inputs"""
        long_name = 'a' * 1000
        response = self.client.get(reverse('pokemon_list') + f'?q={long_name}')
        
        # Should handle gracefully
        self.assertEqual(response.status_code, 200)
    
    def test_invalid_page_numbers(self):
        """Test handling of invalid page numbers"""
        response = self.client.get(reverse('pokemon_list') + '?page=-1')
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('pokemon_list') + '?page=abc')
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('pokemon_list') + '?page_size=1000')
        self.assertEqual(response.status_code, 200)
