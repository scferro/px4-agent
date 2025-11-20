# PX4 Agent with TensorRT-LLM

Intelligent drone mission planning agent using natural language. Built with LangChain and NVIDIA TensorRT-LLM for GPU-accelerated inference with the Qwen3-4B language model.

## Overview

Transform natural language commands into validated PX4 drone missions. Say "take off to 150 feet heading north, fly to the park, then survey the area" and the agent handles the rest.

**Key Features:**
- Natural language mission planning
- TensorRT-LLM optimized inference (INT4 AWQ quantization, ~4-5GB VRAM)
- VTOL support with transition heading control
- AI-powered search and detection integration
- Auto-validation and parameter completion
- RESTful API and interactive CLI
- Containerized deployment with Docker

**Requirements:**
- NVIDIA GPU (Ampere+: RTX 3000+/4000+, A series)
- NVIDIA Driver 525+
- Docker with GPU support
- ~20GB disk space

---

## Quick Start

**For existing installations with pre-built containers and engines.**

### 1. Start the Server

```bash
cd <path-to-repo>/px4-agent

# Start server
docker compose up -d

# View logs
docker compose logs -f
```

Server runs on http://localhost:5000

### 2. Test the API

```bash
# Check status
curl http://localhost:5000/api/status

# Send command
curl -X POST http://localhost:5000/api/command \
  -H "Content-Type: application/json" \
  -d '{"command": "add takeoff to 150 feet heading north"}'

# Mission planning
curl -X POST http://localhost:5000/api/mission \
  -H "Content-Type: application/json" \
  -d '{"message": "create mission with takeoff, waypoint at 41.8840, -87.6330, and RTL"}'
```

### Stop the Server

```bash
docker compose down
```

---

## Building from Scratch

**For first-time setup or rebuilding from clean slate.**

### Prerequisites

**Verify GPU and Docker support:**
```bash
# Check NVIDIA driver
nvidia-smi

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

**If GPU test fails:**
```bash
sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### Step 1: Clone Repository with Submodules

The Qwen3-4B model is included as a git submodule:

```bash
# Clone with submodules
git clone --recursive <your-repo-url>

# Or if already cloned, initialize submodules
cd <path-to-repo>/px4-agent
git submodule update --init --recursive
```

This downloads the Qwen3-4B-Instruct-2507 tokenizer (~8GB) into `models/Qwen3-4B-Instruct-2507/`.

### Step 2: Build AWQ Checkpoint 

```bash
cd <path-to-repo>/px4-agent

# Start TensorRT-LLM container
docker run --rm -it \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v $(pwd):/workspace \
  -w /workspace \
  nvcr.io/nvidia/tensorrt-llm/release:1.0.0 \
  bash
```

```bash
python3 TensorRT-LLM/examples/models/core/qwen/convert_checkpoint.py \
  --model_dir /workspace/models/Qwen3-4B-Instruct-2507 \
  --output_dir /workspace/models/qwen3_4b_trtllm_checkpoint \
  --dtype float16 \
  --use_weight_only \
  --weight_only_precision int4_awq
```

### Step 3: Build TensorRT Engine

Compile the checkpoint into optimized TensorRT engine (~5-15 minutes):

**Inside container, build engine:**
```bash
trtllm-build \
  --checkpoint_dir /workspace/models/qwen3_4b_trtllm_checkpoint \
  --output_dir /workspace/models/qwen3_4b_trtllm_engine \
  --gemm_plugin float16 \
  --max_batch_size 1 \
  --max_input_len 32768 \
  --max_seq_len 32768
```

**Parameters:**
- `--max_batch_size 1`: Concurrent requests
- `--max_input_len 32768`: Max prompt tokens
- `--max_seq_len 32768`: Max total tokens (input + output)
- `--gemm_plugin float16`: Matrix operation precision

**Test engine:**
```bash
python /workspace/TensorRT-LLM/examples/run.py \
  --engine_dir /workspace/models/qwen3_4b_trtllm_engine \
  --tokenizer_dir /workspace/models/Qwen3-4B-Instruct-2507 \
  --input_text "Explain how to create a drone waypoint mission" \
  --max_output_len 100
```

Exit container when done:
```bash
exit
```

### Step 4: Build PX4 Agent Docker Image

```bash
cd <path-to-repo>/px4-agent

# Build image
docker compose build px4-agent
```

### Step 5: Configure Paths

Verify `config/default_config.json` uses container paths:

```json
{
  "model_command": {
    "type": "tensorrt",
    "model_path": "/models/qwen3_4b_trtllm_engine/",
    "tokenizer_path": "/models/Qwen3-4B-Instruct-2507/",
    "gpu_memory_fraction": 0.7,
    "temperature": 0.3
  }
}
```

**Path mapping (docker-compose.yml):**
- Host: `./models/Qwen3-4B-Instruct-2507` (git submodule)
- Container: `/models/Qwen3-4B-Instruct-2507/`
- Host: `./models/qwen3_4b_trtllm_engine` (built locally)
- Container: `/models/qwen3_4b_trtllm_engine/`

### Step 6: Run the Server

```bash
docker compose up -d
```

Test with Quick Start instructions above.

---

## Docker Architecture

```
┌──────────────────────────────────────────┐
│  Container: px4-agent-server             │
│  Base: tensorrt-llm:1.0.0                │
│                                           │
│  Flask API (:5000)                       │
│    ↓                                     │
│  LangChain Agent                         │
│    ↓                                     │
│  TensorRT ModelRunner (Qwen3-4B INT4)    │
│    ↓                                     │
│  NVIDIA GPU (~4-5GB VRAM)                │
└──────────────────────────────────────────┘
          ↑
    Volume Mounts:
    - Qwen3-4B-Instruct-2507 (ro)
    - trtllm_engine (ro)
    - config (rw)
```

**docker-compose.yml key settings:**
```yaml
runtime: nvidia
ports:
  - "5000:5000"
volumes:
  - ./models/Qwen3-4B-Instruct-2507:/models/Qwen3-4B-Instruct-2507:ro
  - ./models/qwen3_4b_trtllm_engine:/models/qwen3_4b_trtllm_engine:ro
  - ./config:/app/config
```

---

## Configuration

### Model Settings

**File:** `config/default_config.json`

```json
{
  "model_command": {
    "type": "tensorrt",
    "model_path": "/models/qwen3_4b_trtllm_engine/",
    "tokenizer_path": "/models/Qwen3-4B-Instruct-2507/",
    "gpu_memory_fraction": 0.7,
    "temperature": 0.3,
    "top_p": 0.6,
    "top_k": 30,
    "max_tokens": 32768
  },
  "model_mission": {
    "type": "tensorrt",
    "model_path": "/models/qwen3_4b_trtllm_engine/",
    "tokenizer_path": "/models/Qwen3-4B-Instruct-2507/",
    "gpu_memory_fraction": 0.7,
    "temperature": 0.3
  }
}
```

**Parameters:**
- `type`: `"tensorrt"` or `"ollama"`
- `model_path`: TensorRT engine directory (container path)
- `tokenizer_path`: Tokenizer files (container path)
- `gpu_memory_fraction`: GPU memory allocation (0.0-1.0)
- `temperature`: Generation randomness (0.0-1.0, lower = deterministic)
- `top_p`: Nucleus sampling threshold
- `top_k`: Top-k sampling
- `max_tokens`: Max output length

**Mixed configuration example:**
```json
{
  "model_command": {
    "type": "tensorrt",
    "model_path": "/models/qwen3_4b_trtllm_engine/"
  },
  "model_mission": {
    "type": "ollama",
    "name": "qwen3:4b-instruct",
    "base_url": "http://host.docker.internal:11434"
  }
}
```

### Agent Settings

```json
{
  "agent": {
    "max_mission_items": 100,
    "auto_validate": true,

    "takeoff_initial_latitude": 41.8832,
    "takeoff_initial_longitude": -87.6324,
    "takeoff_default_heading": "north",

    "auto_add_missing_takeoff": true,
    "auto_add_missing_rtl": true,
    "auto_complete_parameters": true,

    "takeoff_default_altitude": 150.0,
    "waypoint_default_altitude": 300.0,
    "loiter_default_altitude": 300.0,
    "loiter_default_radius": 500.0,
    "survey_default_altitude": 300.0,
    "rtl_default_altitude": 150.0
  }
}
```

**Key settings:**
- `auto_validate`: Validate missions automatically
- `auto_complete_parameters`: Fill missing values from defaults
- `auto_add_missing_takeoff/rtl`: Add if missing
- Altitude/radius defaults per mission item type

---

## Usage

### Mission Item Types

**Takeoff** - Launch with altitude and heading
```
"Take off to 150 feet heading north"
"Takeoff to 200 feet heading southwest"
```

**Waypoint** - Navigate to coordinates
```
"Add waypoint at 41.8840, -87.6330 at 300 feet"
"Fly 2 miles north at 400 feet"
"Go to MGRS 11SMT1234567890"
"Add waypoint searching for vehicles"
```

**Loiter** - Circular orbit pattern
```
"Loiter with 500 foot radius"
"Circle the area at 300 feet with 1000 foot radius"
"Loiter here searching for people"
```

**Survey** - Systematic area coverage
```
"Survey the area with 100 foot spacing"
"Survey 500 foot radius at 200 feet"
```

**RTL** - Return to launch
```
"Return to launch"
"RTL at 200 feet"
```

### Position Specification

**Absolute:**
```
"41.8840, -87.6330"
"Lat 41.8840, Long -87.6330"
```

**Relative:**
```
"2 miles north"
"500 feet southeast"
"1 kilometer northeast of last waypoint"
```

**MGRS Grid:**
```
"MGRS 11SMT1234567890"
```

### Mission Management

**Update items:**
```
"Change item 2 altitude to 400 feet"
"Update loiter radius to 800 feet"
```

**Move items:**
```
"Move item 3 to 41.8850, -87.6340"
"Relocate waypoint 2 half a mile east"
```

**Delete items:**
```
"Delete item 5"
"Remove waypoint 3"
```

**Reorder:**
```
"Move item 5 to position 2"
```

### AI Search Integration

Add search to waypoints, loiter, and survey:
```
"Waypoint at 41.8840, -87.6330 searching for vehicles"
"Loiter here looking for people"
"Survey the area detecting buildings"
```

**Detection behaviors:**
- `tag_and_continue`: Mark objects, continue mission
- `detect_and_monitor`: Stop and orbit detected objects

---

## API Reference

### GET /api/status

Check server status.

**Response:**
```json
{
  "status": "ready",
  "models": {
    "command": "Qwen3-4B-Instruct",
    "mission": "Qwen3-4B-Instruct"
  }
}
```

### POST /api/command

Execute single command (stateless).

**Request:**
```json
{
  "command": "add takeoff to 150 feet heading north"
}
```

**Response:**
```json
{
  "success": true,
  "mission_items": [
    {
      "sequence": 0,
      "type": "takeoff",
      "latitude": 41.8832,
      "longitude": -87.6324,
      "altitude": 150.0,
      "heading": "north"
    }
  ]
}
```

### POST /api/mission

Interactive mission planning (stateful).

**Request:**
```json
{
  "message": "create mission with takeoff, waypoint at the park, and RTL"
}
```

**Response:**
```json
{
  "success": true,
  "response": "Created mission with 3 items",
  "mission_items": [...]
}
```

---

## Development Workflow

### Rebuild After Code Changes

```bash
cd /home/stephen/px4-agent/px4-agent

# Rebuild and restart
docker compose up -d --build
```

### View Logs

```bash
# Follow logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail=100
```

### Debug Inside Container

```bash
docker exec -it px4-agent-server bash

# Inside container
python3
>>> from llm_backends.tensorrt import TensorRTInterface
```

### Update Configuration

Edit `config/default_config.json`, then:
```bash
docker compose restart
```

---

## Troubleshooting

### Docker Compose Version Error

**Symptoms:**
- `URLSchemeUnknown: Not supported URL scheme http+docker`
- `docker-compose` v1.x fails with Python package errors

**Cause:** Old Python-based `docker-compose` (v1) incompatible with newer Python packages.

**Solution:**

Install Docker Compose V2 (modern Go-based version):
```bash
# Install Docker Compose V2 plugin
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# Verify installation
docker compose version
```

Then use `docker compose` (with space) instead of `docker-compose` (with hyphen). All commands in this README use the V2 syntax.

### Container Can't See GPU

```bash
# Verify GPU
nvidia-smi

# Test Docker GPU
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# If fails, install nvidia-docker2
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### Port 5000 Already in Use

**Option A:** Change port in docker-compose.yml:
```yaml
ports:
  - "5001:5000"
```

**Option B:** Kill process:
```bash
sudo lsof -i :5000
sudo kill -9 <PID>
```

### Out of Memory (Build)

Reduce sequence lengths:
```bash
trtllm-build \
  --checkpoint_dir /workspace/awq_ckpt/qwen3-4b-awq-gs128 \
  --output_dir /workspace/trtllm_engine/qwen3-4b-instruct-2507/awq/tp1 \
  --gemm_plugin float16 \
  --max_batch_size 4 \
  --max_input_len 512 \
  --max_seq_len 1024
```

### Out of Memory (Inference)

Reduce GPU memory in config:
```json
{
  "model_command": {
    "gpu_memory_fraction": 0.5
  }
}
```

### Engine Deserialization Error

**Cause:** Engine built with different TensorRT version than runtime.

**Solution:** Always use same Docker image (1.0.0) for build and runtime. Dockerfile already uses correct version.

### Config Changes Not Applied

Restart container:
```bash
docker compose restart
```

### First Request Slow

Engine loads on first request (~30s). Subsequent requests are fast. This is normal.

---

## Cleanup and Rebuild

### Delete Everything

```bash
cd <path-to-repo>/px4-agent

# Delete built engine
rm -rf models/qwen3_4b_trtllm_engine/*

# Delete AWQ checkpoint (optional)
rm -rf awq_ckpt/

# Delete Docker images
docker compose down
docker rmi px4-agent:tensorrt
docker rmi nvcr.io/nvidia/tensorrt-llm/release:1.0.0
```

**Note:** Don't delete `models/Qwen3-4B-Instruct-2507/` - it's a git submodule. Use `git submodule deinit` if you need to remove it.

### Rebuild

Follow "Building from Scratch" section.

---

## Production Deployment

### Health Checks

Add to docker-compose.yml:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/api/status"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      memory: 16G
    reservations:
      memory: 8G
```

### Logging

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name px4-agent.example.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Performance Tuning

### Optimization Tips

1. **Batch Size**: Increase for throughput, decrease for latency
2. **Sequence Length**: Use only what you need
3. **GPU Memory**: Higher fraction = more KV cache = longer contexts
4. **Precision**: INT4 AWQ already optimal

### Monitoring

```bash
# GPU usage
watch -n 1 nvidia-smi

# Container stats
docker stats px4-agent-server
```

---

## License

MIT License

## Support

- **Issues**: https://github.com/yourusername/px4-agent/issues
- **TensorRT-LLM**: https://github.com/NVIDIA/TensorRT-LLM

## Acknowledgments

- [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM)
- [Qwen3-4B-Instruct](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- [LangChain](https://github.com/langchain-ai/langchain)
