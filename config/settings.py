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
    name: str = ""
    base_url: str = ""
    temperature: float = 0.0
    top_p: float = 0.0
    top_k: int = 0
    timeout: int = 0
    max_tokens: Optional[int] = None

@dataclass
class AgentConfig:
    """Agent behavior configuration with comprehensive parameter defaults"""
    
    # Core behavior settings
    max_mission_items: int = 0
    auto_validate: bool = False
    verbose_default: bool = False
    
    # Mission structure validation
    single_takeoff_only: bool = False
    single_rtl_only: bool = False
    takeoff_must_be_first: bool = False
    rtl_must_be_last: bool = False
    auto_fix_positioning: bool = False
    
    # Parameter completion behavior
    auto_add_missing_takeoff: bool = False
    auto_add_missing_rtl: bool = False
    auto_complete_parameters: bool = False
    
    # === TAKEOFF PARAMETERS ===
    takeoff_default_altitude: float = 0.0
    takeoff_altitude_units: str = ""
    takeoff_min_altitude: float = 0.0
    takeoff_max_altitude: float = 0.0
    takeoff_default_latitude: float = 0.0      # Used when no origin available
    takeoff_default_longitude: float = 0.0     # Used when no origin available
    
    # === WAYPOINT PARAMETERS ===
    waypoint_default_altitude: float = 0.0
    waypoint_altitude_units: str = ""
    waypoint_min_altitude: float = 0.0
    waypoint_max_altitude: float = 0.0
    waypoint_use_previous_altitude: bool = False  # Smart altitude inheritance
    waypoint_use_last_waypoint_location: bool = False  # Inherit coordinates from last waypoint
    
    # === LOITER PARAMETERS ===
    loiter_default_altitude: float = 0.0
    loiter_altitude_units: str = ""
    loiter_min_altitude: float = 0.0
    loiter_max_altitude: float = 0.0
    loiter_use_previous_altitude: bool = False
    loiter_default_radius: float = 0.0
    loiter_radius_units: str = ""
    loiter_min_radius: float = 0.0
    loiter_max_radius: float = 0.0
    loiter_use_last_waypoint_location: bool = False  # Smart location defaulting
    
    # === RTL PARAMETERS ===
    rtl_default_altitude: float = 0.0
    rtl_altitude_units: str = ""
    rtl_min_altitude: float = 0.0
    rtl_max_altitude: float = 0.0
    rtl_use_takeoff_altitude: bool = False       # Smart altitude inheritance
    
    # === SURVEY PARAMETERS ===
    survey_default_altitude: float = 100.0
    survey_altitude_units: str = ""
    survey_min_altitude: float = 0.0
    survey_max_altitude: float = 0.0
    survey_use_previous_altitude: bool = False
    survey_default_radius: float = 0.0
    survey_radius_units: str = ""
    survey_min_radius: float = 0.0
    survey_max_radius: float = 0.0
    survey_use_last_waypoint_location: bool = False
    
    # === SEARCH PARAMETERS (for all command types) ===
    default_search_target: str = ""             # Empty = no search
    default_detection_behavior: str = "tag_and_continue"
    
    # === DISTANCE/HEADING PARAMETERS ===
    default_distance_units: str = ""



@dataclass
class PX4AgentSettings:
    """Complete PX4 Agent configuration"""
    model: ModelConfig
    agent: AgentConfig
    
    # Class variable to store singleton instance
    _instance: Optional['PX4AgentSettings'] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PX4AgentSettings':
        """Create settings from dictionary"""
        return cls(
            model=ModelConfig(**data.get('model', {})),
            agent=AgentConfig(**data.get('agent', {}))
        )
    
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

# Global settings instance
_settings: Optional[PX4AgentSettings] = None

def get_settings() -> PX4AgentSettings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = PX4AgentSettings.load()
    return _settings

def get_model_settings() -> Dict[str, Any]:
    """Get model settings as dictionary"""
    settings = get_settings()
    return settings.model.__dict__

def get_agent_settings() -> Dict[str, Any]:
    """Get agent settings as dictionary"""
    settings = get_settings()
    return settings.agent.__dict__