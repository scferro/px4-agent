# PX4 Agent

Intelligent drone mission planning agent using natural language. Built with LangChain and Ollama.

## Quick Start

### Prerequisites
1. **Ollama with Qwen3:1.7b model**
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

## Core Features

### Mission Tools
- **add_takeoff** - Launch drone to specified altitude
- **add_waypoint** - Navigate to GPS coordinates or relative positions
- **add_loiter** - Create circular orbit patterns with specified radius
- **add_rtl** - Return to launch and land
- **update_mission_item** - Modify position, altitude, radius of existing items
- **delete_mission_item** - Remove items from mission

### Position Specification
- **Lat/Long Coordinates**: `"37.7749, -122.4194"`
- **Relative Positioning**: `"2 miles north"`, `"500 feet southeast"`
- **MGRS Grid**: `"MGRS 11SMT1234567890"`

## Modes

### Mission Mode
- **Interactive mission building** with conversation history
- **Persistent state** - previous request context maintained during chat
- **Complete mission planning** with validation
- Use for: Complex multi-step missions

### Command Mode  
- **Single command execution** with reset after each response
- **Fresh state** - request context not saved between commands
- **Quick operations** with relaxed validation
- Use for: Individual commands, simple operations
