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
    name: str = "granite3.3:2b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    top_p: float = 0.9
    top_k: int = 40
    timeout: int = 60
    max_tokens: Optional[int] = None

@dataclass
class AgentConfig:
    """Agent behavior configuration"""
    max_mission_items: int = 100
    default_altitude: float = 50.0  # meters
    safety_checks: bool = True
    require_verification: bool = True
    auto_validate: bool = True
    verbose_default: bool = False

@dataclass
class OutputConfig:
    """Output formatting configuration"""
    use_colors: bool = True
    show_timestamps: bool = False
    log_level: str = "INFO"
    max_output_length: int = 10000

@dataclass
class SafetyConfig:
    """Safety and validation configuration"""
    max_altitude: float = 120.0  # meters
    min_altitude: float = 1.0    # meters
    max_speed: float = 25.0      # m/s
    min_speed: float = 1.0       # m/s
    max_waypoint_distance: float = 10000.0  # meters
    require_takeoff: bool = True
    require_landing_or_rtl: bool = True

@dataclass
class PX4AgentSettings:
    """Complete PX4 Agent configuration"""
    model: ModelConfig
    agent: AgentConfig
    output: OutputConfig
    safety: SafetyConfig
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PX4AgentSettings':
        """Create settings from dictionary"""
        return cls(
            model=ModelConfig(**data.get('model', {})),
            agent=AgentConfig(**data.get('agent', {})),
            output=OutputConfig(**data.get('output', {})),
            safety=SafetyConfig(**data.get('safety', {}))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            'model': self.model.__dict__,
            'agent': self.agent.__dict__,
            'output': self.output.__dict__,
            'safety': self.safety.__dict__
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
                agent=AgentConfig(),
                output=OutputConfig(),
                safety=SafetyConfig()
            )
    
    def save(self, config_path: str):
        """Save settings to file"""
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
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
        if os.getenv('PX4_MAX_ALTITUDE'):
            self.safety.max_altitude = float(os.getenv('PX4_MAX_ALTITUDE'))
        if os.getenv('PX4_VERBOSE'):
            self.agent.verbose_default = os.getenv('PX4_VERBOSE').lower() == 'true'
        if os.getenv('PX4_REQUIRE_VERIFICATION'):
            self.agent.require_verification = os.getenv('PX4_REQUIRE_VERIFICATION').lower() == 'true'

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