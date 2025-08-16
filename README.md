# PX4 Agent

Intelligent drone mission planning using LangChain and Granite 3.3 2B model running on Ollama.

## Quick Start

### Prerequisites
1. **Ollama running with Granite 3.3 2B**
```bash
# Install and start Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &

# Download model
ollama pull granite3.3:2b
```

2. **Install Python dependencies**
```bash
cd /home/stephen/px4-agent/px4-agent
pip install -r requirements.txt
```

### Test the Agent

1. **Check system status**
```bash
python run.py status
```

2. **Test command mode**
```bash
python run.py command "takeoff to 15 meters"
```

3. **Test mission mode**
```bash
python run.py mission new "Create a survey mission with takeoff to 20m, 3 waypoints, then RTL"
```

### Usage Examples

**Command Mode** (single actions):
```bash
python run.py command "add waypoint at 37.7749, -122.4194, 50 meters"
python run.py command "add return to launch"
```

**Mission Mode** (multi-step):
```bash
python run.py mission new "Plan a rectangular survey pattern at 50m altitude with 4 corners"
```

**Update Mission**:
```bash
python run.py mission update "add a 30-second loiter before landing"
```

**Verbose Mode** (show model reasoning):
```bash
python run.py --verbose mission new "Create takeoff, loiter 30 seconds, then land"
```

## How It Works

1. **Agent receives request** → Plans using mission tools
2. **Agent calls `show_mission_for_approval`** → User reviews mission
3. **User approves** → Mission saved to `current_mission.json`
4. **User rejects** → Agent updates mission based on feedback
5. **Updates** → Always work with `current_mission.json`

## Key Features

- ✅ RTL (Return to Launch) tool included
- ✅ Mission approval workflow with file save
- ✅ Chat history maintained for updates  
- ✅ Safety validation built-in
- ✅ No direct flight controller access (manual upload required)

## File Structure
```
px4-agent/
├── tools/mission_tools.py    # 8 core tools including RTL
├── agent.py                  # Main agent with 3 modes
├── cli.py                   # Command line interface
├── missions/                # Approved missions saved here
└── config/                  # Settings and prompts
```