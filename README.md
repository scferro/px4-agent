# PX4 Agent

Intelligent drone mission planning agent using natural language. Built with LangChain and Ollama with advanced VTOL support and dynamic configuration.

## Quick Start

### Prerequisites
1. **Ollama with Qwen3:4b model**
```bash
# Install and start Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &

# Download model
ollama pull qwen3:4b-instruct
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

### Usage

Launch interactive mission planning:
```bash
# Mission mode - Build complete missions interactively
python3 cli.py mission

# Command mode - Single commands with reset after each
python3 cli.py command

# Verbose mode - Show agent reasoning
python3 cli.py -v mission
```

## Modes

### Mission Mode
- **Interactive mission building** with conversation history
- **Persistent state** - previous request context maintained during chat
- **Complete mission planning** with auto-validation and fixes
- **Smart parameter completion** from configuration defaults
- Use for: Complex multi-step missions, VTOL operations

### Command Mode  
- **Single command execution** with reset after each response
- **Fresh state** - request context not saved between commands
- **Quick operations** with relaxed validation
- Use for: Individual commands, testing, simple operations

## Core Features

### LLM Tools
- **add_takeoff** - Launch drone with VTOL heading support (`"takeoff to 200ft heading southwest"`)
- **add_waypoint** - Navigate to GPS coordinates or relative positions with AI search capability
- **add_loiter** - Create circular orbit patterns with specified radius and optional AI search
- **add_survey** - Generate systematic survey patterns (center+radius or polygon boundary)
- **add_rtl** - Return to launch and land at specified altitude
- **update_mission_item** - Modify position, altitude, radius, heading of existing items
- **delete_mission_item** - Remove items from mission by sequence number
- **move_mission_item** - Reorder mission items by moving to new positions

### Advanced Features
- **VTOL Support**: Specify transition heading for takeoff (`"takeoff heading north"`)
- **AI Search Integration**: Add search targets to waypoints, loiter, and survey commands
- **Smart Auto-Completion**: Automatic parameter completion from configuration
- **Dynamic Defaults**: Tool descriptions show actual default values from settings
- **Visual Mission Display**: Rich table format with separators between mission items

### Position Specification
- **Lat/Long Coordinates**: `"37.7749, -122.4194"`
- **Relative Positioning**: `"2 miles north"`, `"500 feet southeast of last waypoint"`
- **MGRS Grid**: `"MGRS 11SMT1234567890"`
- **Reference Frames**: Origin (takeoff point) or last waypoint

### Search & Detection
- **Search Targets**: `"search for vehicles"`, `"look for people"`
- **Detection Behaviors**: 
  - `tag_and_continue` - Mark targets and continue mission
  - `detect_and_monitor` - Stop and circle detected targets
