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

    # Initial takeoff location must be defined to start mission
    takeoff_initial_latitude: float = 0.0  
    takeoff_initial_longitude: float = 0.0
    
    # === CURRENT ACTION PARAMETERS (for command mode) ===
    current_action_type: str = "takeoff"
    current_action_latitude: float = 0.0
    current_action_longitude: float = 0.0
    current_action_altitude: float = 150.0
    current_action_altitude_units: str = "feet"
    current_action_radius: float = 400.0  # For loiter/survey
    current_action_radius_units: str = "feet"
    current_action_heading: str = ""  # For takeoff VTOL direction  
    
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
    takeoff_default_heading: str = ""
    
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
    model_command: ModelConfig
    model_mission: ModelConfig
    agent: AgentConfig
    
    # Class variable to store singleton instance
    _instance: Optional['PX4AgentSettings'] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PX4AgentSettings':
        """Create settings from dictionary"""
        # Handle both new format (model_command/model_mission) and legacy format (model)
        if 'model_command' in data and 'model_mission' in data:
            # New format
            return cls(
                model_command=ModelConfig(**data.get('model_command', {})),
                model_mission=ModelConfig(**data.get('model_mission', {})),
                agent=AgentConfig(**data.get('agent', {}))
            )
        elif 'model' in data:
            # Legacy format - use same model for both modes
            model_config = ModelConfig(**data.get('model', {}))
            return cls(
                model_command=model_config,
                model_mission=model_config,
                agent=AgentConfig(**data.get('agent', {}))
            )
        else:
            # No model config - use defaults
            return cls(
                model_command=ModelConfig(),
                model_mission=ModelConfig(),
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
                model_command=ModelConfig(),
                model_mission=ModelConfig(),
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

def get_model_settings(mode: str = "command") -> Dict[str, Any]:
    """Get model settings as dictionary for specified mode"""
    settings = get_settings()
    if mode == "mission":
        return settings.model_mission.__dict__
    else:
        return settings.model_command.__dict__

def get_agent_settings() -> Dict[str, Any]:
    """Get agent settings as dictionary"""
    settings = get_settings()
    return settings.agent.__dict__

def reload_settings(config_path: Optional[str] = None):
    """Reload settings from file"""
    global _settings
    _settings = PX4AgentSettings.load(config_path)

def update_takeoff_settings(latitude: float, longitude: float, heading: str):
    """Update takeoff settings at runtime"""
    global _settings
    if _settings is None:
        _settings = PX4AgentSettings.load()
    
    # Validate inputs
    if not (-90 <= latitude <= 90):
        raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")
    if not (-180 <= longitude <= 180):
        raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")
    if not heading or not isinstance(heading, str):
        raise ValueError("Heading must be a non-empty string")
    
    # Update runtime settings
    _settings.agent.takeoff_initial_latitude = latitude
    _settings.agent.takeoff_initial_longitude = longitude
    _settings.agent.takeoff_default_heading = heading

def get_current_takeoff_settings() -> Dict[str, Any]:
    """Get current takeoff settings"""
    settings = get_settings()
    return {
        "latitude": settings.agent.takeoff_initial_latitude,
        "longitude": settings.agent.takeoff_initial_longitude,
        "heading": settings.agent.takeoff_default_heading
    }

def update_current_action_settings(action_type: str, latitude: float = None, longitude: float = None, 
                                 altitude: float = None, altitude_units: str = None,
                                 radius: float = None, radius_units: str = None, 
                                 heading: str = None):
    """Update current action settings at runtime"""
    global _settings
    if _settings is None:
        _settings = load_settings()
    
    # Validate action type
    allowed_types = ['takeoff', 'waypoint', 'loiter', 'survey']
    if action_type not in allowed_types:
        raise ValueError(f"Invalid action type '{action_type}'. Allowed types: {', '.join(allowed_types)}")
    
    # Update provided fields
    _settings.agent.current_action_type = action_type
    if latitude is not None:
        _settings.agent.current_action_latitude = latitude
    if longitude is not None:
        _settings.agent.current_action_longitude = longitude
    if altitude is not None:
        _settings.agent.current_action_altitude = altitude
    if altitude_units is not None:
        _settings.agent.current_action_altitude_units = altitude_units
    if radius is not None:
        _settings.agent.current_action_radius = radius
    if radius_units is not None:
        _settings.agent.current_action_radius_units = radius_units
    if heading is not None:
        _settings.agent.current_action_heading = heading

def get_current_action_settings() -> Dict[str, Any]:
    """Get current action settings"""
    settings = get_settings()
    return {
        "type": settings.agent.current_action_type,
        "latitude": settings.agent.current_action_latitude,
        "longitude": settings.agent.current_action_longitude,
        "altitude": settings.agent.current_action_altitude,
        "altitude_units": settings.agent.current_action_altitude_units,
        "radius": settings.agent.current_action_radius,
        "radius_units": settings.agent.current_action_radius_units,
        "heading": settings.agent.current_action_heading
    }