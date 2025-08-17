"""
PX4 Agent Configuration Management
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import os

@dataclass
class ModelConfig:
    """Model configuration settings"""
    name: str = "qwen3:1.7b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.3
    top_p: float = 0.7
    top_k: int = 30
    timeout: int = 60
    max_tokens: Optional[int] = None

@dataclass
class AgentConfig:
    """Agent behavior configuration with comprehensive parameter defaults"""
    
    # Core behavior settings
    max_mission_items: int = 100
    auto_validate: bool = True
    verbose_default: bool = False
    
    # Mission structure validation
    single_takeoff_only: bool = True
    single_rtl_only: bool = True
    takeoff_must_be_first: bool = True
    rtl_must_be_last: bool = True
    auto_fix_positioning: bool = True
    
    # Parameter completion behavior
    auto_add_missing_takeoff: bool = True
    auto_add_missing_rtl: bool = True
    auto_complete_parameters: bool = True
    
    # === TAKEOFF PARAMETERS ===
    takeoff_default_altitude: float = 50.0
    takeoff_altitude_units: str = "meters"
    takeoff_min_altitude: float = 1.0
    takeoff_max_altitude: float = 1000.0
    takeoff_default_latitude: float = 0.0      # Used when no origin available
    takeoff_default_longitude: float = 0.0     # Used when no origin available
    
    # === WAYPOINT PARAMETERS ===
    waypoint_default_altitude: float = 100.0
    waypoint_altitude_units: str = "meters"
    waypoint_min_altitude: float = 1.0
    waypoint_max_altitude: float = 1000.0
    waypoint_use_previous_altitude: bool = True  # Smart altitude inheritance
    waypoint_require_coordinates: bool = True   # Lat/lon must be provided
    
    # === LOITER PARAMETERS ===
    loiter_default_altitude: float = 100.0
    loiter_altitude_units: str = "meters"
    loiter_min_altitude: float = 1.0
    loiter_max_altitude: float = 1000.0
    loiter_use_previous_altitude: bool = True
    loiter_default_radius: float = 50.0
    loiter_radius_units: str = "meters"
    loiter_min_radius: float = 10.0
    loiter_max_radius: float = 1000.0
    loiter_default_latitude: float = 0.0        # Used when no coordinates provided
    loiter_default_longitude: float = 0.0       # Used when no coordinates provided
    loiter_use_last_waypoint_location: bool = True  # Smart location defaulting
    
    # === RTL PARAMETERS ===
    rtl_default_altitude: float = 50.0
    rtl_altitude_units: str = "meters"
    rtl_min_altitude: float = 1.0
    rtl_max_altitude: float = 1000.0
    rtl_use_takeoff_altitude: bool = True       # Smart altitude inheritance
    
    # === SURVEY PARAMETERS ===
    survey_default_altitude: float = 100.0
    survey_altitude_units: str = "meters"
    survey_min_altitude: float = 10.0
    survey_max_altitude: float = 1000.0
    survey_use_previous_altitude: bool = True
    survey_default_radius: float = 100.0
    survey_radius_units: str = "meters"
    survey_min_radius: float = 50.0
    survey_max_radius: float = 5000.0
    survey_default_latitude: float = 0.0
    survey_default_longitude: float = 0.0
    survey_use_last_waypoint_location: bool = True
    
    # === SEARCH PARAMETERS (for all command types) ===
    default_search_target: str = ""             # Empty = no search
    default_detection_behavior: str = "tag_and_continue"
    
    # === DISTANCE/HEADING PARAMETERS ===
    default_distance_units: str = "meters"
    min_distance: float = 1.0
    max_distance: float = 50000.0               # 50km max distance
    
    # === GLOBAL CONSTRAINTS ===
    global_min_altitude: float = 0.1            # Absolute minimum for any command
    global_max_altitude: float = 2000.0         # Absolute maximum for any command
    global_min_radius: float = 1.0              # Absolute minimum radius
    global_max_radius: float = 10000.0          # Absolute maximum radius



@dataclass
class PX4AgentSettings:
    """Complete PX4 Agent configuration"""
    model: ModelConfig
    agent: AgentConfig
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PX4AgentSettings':
        """Create settings from dictionary"""
        return cls(
            model=ModelConfig(**data.get('model', {})),
            agent=AgentConfig(**data.get('agent', {}))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            'model': self.model.__dict__,
            'agent': self.agent.__dict__
        }
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'PX4AgentSettings':
        """Load settings from file or environment"""
        if config_path is None:
            # Look for config in common locations
            possible_paths = [
                Path.cwd() / "px4_agent_config.json",
                Path.home() / ".px4_agent" / "config.json",
                Path(__file__).parent / "default_config.json"
            ]
            
            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        else:
            # Return default settings
            return cls(
                model=ModelConfig(),
                agent=AgentConfig()
            )
    
    def update_from_env(self):
        """Update settings from environment variables"""
        # Model settings
        if os.getenv('PX4_MODEL_NAME'):
            self.model.name = os.getenv('PX4_MODEL_NAME')
        if os.getenv('PX4_MODEL_BASE_URL'):
            self.model.base_url = os.getenv('PX4_MODEL_BASE_URL')
        if os.getenv('PX4_MODEL_TEMPERATURE'):
            self.model.temperature = float(os.getenv('PX4_MODEL_TEMPERATURE'))
        
        # Agent settings
        if os.getenv('PX4_VERBOSE'):
            self.agent.verbose_default = os.getenv('PX4_VERBOSE').lower() == 'true'

# Global settings instance
_settings: Optional[PX4AgentSettings] = None

def get_settings() -> PX4AgentSettings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = PX4AgentSettings.load()
        _settings.update_from_env()
    return _settings

def reload_settings(config_path: Optional[str] = None):
    """Reload settings from file"""
    global _settings
    _settings = PX4AgentSettings.load(config_path)
    _settings.update_from_env()