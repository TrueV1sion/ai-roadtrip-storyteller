"""
Sound library configuration for spatial audio system.
Contains all sound definitions and mappings.
"""

from typing import Dict, List


class SoundLibrary:
    """Centralized sound library with all audio asset definitions."""
    
    def __init__(self):
        self.environments = {
            "forest": ["forest_birds", "leaves_rustling", "stream", "wind_trees"],
            "city": ["traffic", "people_talking", "car_horns", "construction"],
            "beach": ["waves", "seagulls", "beach_crowd", "wind_shore"],
            "mountain": ["high_wind", "eagle_calls", "rocks_tumbling", "distant_stream"],
            "desert": ["wind_sand", "rattlesnake", "coyote", "silence"],
            "small_town": ["light_traffic", "distant_conversation", "shop_bells", "children_playing"],
            "park": ["playground", "picnic_crowd", "park_birds", "sports_activity"],
            "suburban": ["lawn_mower", "sprinklers", "bicycle_bell", "backyard_bbq"],
            "rural": ["farm_animals", "tractor", "crickets", "farm_work"],
            "historical_site": ["tour_guide", "camera_clicks", "shuffling_feet", "hushed_voices"],
            "museum": ["quiet_murmur", "docent_tour", "exhibit_audio", "children_groups"],
            "tourist_attraction": ["excited_crowd", "tour_guide", "photo_taking", "souvenir_vendors"],
            "restaurant": ["dining_ambiance", "kitchen_sounds", "clinking_glasses", "conversation"],
            "highway": ["passing_cars", "engine_rumble", "wind_rushing", "radio_static"],
            "amusement_park": ["rides", "screaming", "carnival_music", "vendors"],
            "night": ["crickets", "owls", "distant_traffic", "wind"],
            "rain": ["light_rain", "heavy_rain", "thunder", "rain_on_roof"],
            "snow": ["crunching_snow", "winter_wind", "snowball_play", "quiet_snowfall"],
        }
        
        self.transitions = {
            "forest_to_city": ["forest_edge", "increasing_traffic", "birds_fading"],
            "city_to_forest": ["decreasing_traffic", "increasing_birds", "natural_ambiance"],
            "beach_to_city": ["fading_waves", "increasing_urban", "gulls_to_traffic"],
            "mountain_to_forest": ["decreasing_wind", "increasing_birds", "denser_foliage"],
            "desert_to_rural": ["wind_calming", "increasing_life_sounds", "coyote_to_dog"],
        }
        
        self.weather = {
            "sunny": ["birds_active", "people_outdoors", "bright_ambiance"],
            "cloudy": ["muted_sounds", "wind_gusts", "distant_rumble"],
            "rain": ["rain_drops", "splashing", "windshield_wipers", "thunder"],
            "snow": ["muffled_sounds", "snow_crunch", "winter_wind"],
            "fog": ["dampened_sounds", "fog_horn", "cautious_movement"],
            "windy": ["howling_wind", "rustling_leaves", "creaking_signs"],
            "storm": ["heavy_rain", "thunder_cracks", "wind_howling"],
        }
        
        self.time_of_day = {
            "dawn": ["early_birds", "dew_dripping", "distant_rooster"],
            "morning": ["birds_chirping", "morning_commute", "breakfast_sounds"],
            "noon": ["active_bustle", "lunch_crowds", "peak_activity"],
            "afternoon": ["steady_activity", "school_release", "warm_ambiance"],
            "dusk": ["evening_birds", "dinner_preparation", "settling_down"],
            "night": ["crickets", "owl_hoots", "distant_nightlife", "quiet_streets"],
        }
        
        self.music_genres = {
            "adventure": ["epic_orchestra", "heroic_theme", "journey_motif"],
            "peaceful": ["ambient_pads", "nature_harmony", "calm_strings"],
            "mysterious": ["dark_atmosphere", "subtle_tension", "enigmatic_melody"],
            "uplifting": ["major_progression", "building_energy", "triumphant_brass"],
            "nostalgic": ["warm_piano", "vintage_strings", "melancholic_harmony"],
            "exciting": ["driving_rhythm", "action_theme", "energetic_percussion"],
        }
        
        self.special_effects = {
            "magic": ["sparkle_chime", "mystical_whoosh", "enchanted_bell"],
            "discovery": ["revelation_swell", "wonder_chord", "discovery_sting"],
            "danger": ["tension_rise", "warning_drone", "threat_pulse"],
            "achievement": ["victory_fanfare", "success_chime", "accomplishment_swell"],
        }
    
    def get_environment_sounds(self, environment: str) -> List[str]:
        """Get sounds for a specific environment."""
        return self.environments.get(environment, [])
    
    def get_transition_sounds(self, from_env: str, to_env: str) -> List[str]:
        """Get transition sounds between environments."""
        key = f"{from_env}_to_{to_env}"
        return self.transitions.get(key, [])
    
    def get_weather_sounds(self, weather: str) -> List[str]:
        """Get sounds for weather conditions."""
        return self.weather.get(weather, [])
    
    def get_time_sounds(self, time: str) -> List[str]:
        """Get sounds for time of day."""
        return self.time_of_day.get(time, [])
    
    def get_music_genre(self, genre: str) -> List[str]:
        """Get music tracks for a genre."""
        return self.music_genres.get(genre, [])
    
    def get_special_effect(self, effect: str) -> List[str]:
        """Get special effect sounds."""
        return self.special_effects.get(effect, [])