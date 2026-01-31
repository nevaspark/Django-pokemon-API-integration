import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.cache import cache
from pokedex import services
from pokedex.utils import PokeAPIError


class TestServices(TestCase):
    
    def setUp(self):
        cache.clear()
    
    @patch('pokedex.services.requests.get')
    def test_get_pokemon_success(self, mock_get):
        """Test successful Pokemon retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 25,
            'name': 'pikachu',
            'height': 4,
            'weight': 60,
            'types': [{'type': {'name': 'electric'}}],
            'stats': [{'stat': {'name': 'hp'}, 'base_stat': 35}]
        }
        mock_get.return_value = mock_response
        
        result = services.get_pokemon('pikachu')
        
        self.assertEqual(result['name'], 'pikachu')
        self.assertEqual(result['id'], 25)
        mock_get.assert_called_once()
    
    @patch('pokedex.services.requests.get')
    def test_get_pokemon_not_found(self, mock_get):
        """Test Pokemon not found error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Not Found'
        mock_get.return_value = mock_response
        
        with self.assertRaises(PokeAPIError):
            services.get_pokemon('nonexistent')
    
    @patch('pokedex.services.requests.get')
    def test_get_pokemon_network_error(self, mock_get):
        """Test network error handling"""
        mock_get.side_effect = Exception("Network error")
        
        with self.assertRaises(PokeAPIError):
            services.get_pokemon('pikachu')
    
    @patch('pokedex.services.get_type_detail')
    def test_filter_pokemon_by_type(self, mock_get_type):
        """Test filtering Pokemon by type"""
        mock_get_type.return_value = {
            'pokemon': [
                {'pokemon': {'name': 'pikachu'}},
                {'pokemon': {'name': 'raichu'}},
            ]
        }
        
        with patch('pokedex.services.get_pokemon') as mock_get_pokemon:
            mock_get_pokemon.return_value = {'name': 'pikachu', 'id': 25}
            
            result = services.filter_pokemon_by_type('electric', page=1, page_size=10)
            
            self.assertEqual(result['count'], 2)
            self.assertEqual(len(result['results']), 2)
    
    def test_validate_pokemon_name_valid(self):
        """Test valid Pokemon name validation"""
        from pokedex.utils import validate_pokemon_name
        
        result = validate_pokemon_name('pikachu')
        self.assertEqual(result, 'pikachu')
        
        result = validate_pokemon_name('Pikachu')
        self.assertEqual(result, 'pikachu')
        
        result = validate_pokemon_name('tapu-koko')
        self.assertEqual(result, 'tapu-koko')
    
    def test_validate_pokemon_name_invalid(self):
        """Test invalid Pokemon name validation"""
        from pokedex.utils import validate_pokemon_name
        from django.core.exceptions import ValidationError
        
        with self.assertRaises(ValidationError):
            validate_pokemon_name('')
        
        with self.assertRaises(ValidationError):
            validate_pokemon_name('pikachu<script>')
        
        with self.assertRaises(ValidationError):
            validate_pokemon_name('a' * 101)  # Too long
    
    def test_validate_team_names(self):
        """Test team names validation"""
        from pokedex.utils import validate_team_names
        
        names = ['pikachu', 'bulbasaur', 'charizard']
        result = validate_team_names(names)
        self.assertEqual(result, ['pikachu', 'bulbasaur', 'charizard'])
        
        # Test with too many Pokemon
        names = ['pikachu'] * 7
        result = validate_team_names(names)
        self.assertEqual(len(result), 6)  # Should limit to 6
    
    def test_average_stats(self):
        """Test average stats calculation"""
        with patch('pokedex.services.get_pokemon') as mock_get_pokemon:
            mock_get_pokemon.side_effect = [
                {
                    'stats': [
                        {'stat': {'name': 'hp'}, 'base_stat': 35},
                        {'stat': {'name': 'attack'}, 'base_stat': 55}
                    ]
                },
                {
                    'stats': [
                        {'stat': {'name': 'hp'}, 'base_stat': 45},
                        {'stat': {'name': 'attack'}, 'base_stat': 65}
                    ]
                }
            ]
            
            result = services.average_stats(['pikachu', 'bulbasaur'])
            
            self.assertEqual(result['hp'], 40.0)  # (35 + 45) / 2
            self.assertEqual(result['attack'], 60.0)  # (55 + 65) / 2
    
    def test_evo_chain_names(self):
        """Test evolution chain name extraction"""
        evo_data = {
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
        
        result = services.evo_chain_names(evo_data)
        self.assertEqual(result, ['pichu', 'pikachu', 'raichu'])
    
    def test_search_pokemon_exact_match(self):
        """Test Pokemon search with exact match"""
        with patch('pokedex.services.get_pokemon') as mock_get_pokemon:
            mock_get_pokemon.return_value = {'name': 'pikachu', 'id': 25}
            
            result = services.search_pokemon('pikachu')
            
            self.assertEqual(result['count'], 1)
            self.assertEqual(result['results'][0]['name'], 'pikachu')
    
    def test_search_pokemon_partial_match(self):
        """Test Pokemon search with partial match"""
        with patch('pokedex.services.get_pokemon') as mock_get_pokemon, \
             patch('pokedex.services.list_pokemon') as mock_list_pokemon:
            
            mock_get_pokemon.side_effect = PokeAPIError("Not found")
            mock_list_pokemon.return_value = {
                'results': [
                    {'name': 'pikachu'},
                    {'name': 'pichu'}
                ]
            }
            
            # Mock the second get_pokemon call for the actual Pokemon data
            mock_get_pokemon.side_effect = [
                PokeAPIError("Not found"),  # First call for exact match
                {'name': 'pikachu', 'id': 25},  # Second call for pikachu
                {'name': 'pichu', 'id': 172}    # Third call for pichu
            ]
            
            result = services.search_pokemon('pika')
            
            self.assertGreater(result['count'], 0)


class TestCacheBehavior(TestCase):
    
    def setUp(self):
        cache.clear()
    
    @patch('pokedex.services.requests.get')
    def test_caching_behavior(self, mock_get):
        """Test that API responses are cached"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'name': 'pikachu', 'id': 25}
        mock_get.return_value = mock_response
        
        # First call should make API request
        result1 = services.get_pokemon('pikachu')
        self.assertEqual(mock_get.call_count, 1)
        
        # Second call should use cache
        result2 = services.get_pokemon('pikachu')
        self.assertEqual(mock_get.call_count, 1)  # Should not increase
        
        self.assertEqual(result1, result2)
