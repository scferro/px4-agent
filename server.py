"""
PX4 Agent Flask Server
Hosts the complete PX4Agent with LLM and mission management via HTTP APIs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from typing import Dict, Any, Optional
import traceback
import logging

from core import PX4Agent
from config import get_settings, reload_settings, update_takeoff_settings, get_current_takeoff_settings


class PX4AgentServer:
    """Flask server hosting PX4Agent"""
    
    def __init__(self, verbose: bool = False):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for all routes
        
        # Initialize PX4Agent
        self.agent: Optional[PX4Agent] = None
        self.verbose = verbose
        
        # Setup logging
        if not verbose:
            logging.getLogger('werkzeug').setLevel(logging.WARNING)
        
        self._setup_routes()
        self._initialize_agent()
    
    def _clean_result_for_json(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean result dictionary to ensure JSON serialization"""
        if not isinstance(result, dict):
            return result
        
        cleaned = {}
        for key, value in result.items():
            if key == 'intermediate_steps':
                # Convert LangChain messages to serializable format in verbose mode
                if self.verbose and isinstance(value, list):
                    cleaned[key] = []
                    for item in value:
                        if hasattr(item, 'content'):
                            cleaned[key].append({
                                'type': type(item).__name__,
                                'content': str(item.content) if item.content else None
                            })
                        else:
                            cleaned[key].append(str(item))
                else:
                    # Skip intermediate_steps if not verbose
                    continue
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _initialize_agent(self):
        """Initialize the PX4Agent instance"""
        try:
            self.agent = PX4Agent(verbose=self.verbose)
            print(f"🚁 PX4Agent initialized (verbose={self.verbose})")
        except Exception as e:
            print(f"❌ Failed to initialize PX4Agent: {e}")
            self.agent = None
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/', methods=['GET'])
        def index():
            """Serve the main web chat interface"""
            return send_file('static/index.html')
        
        @self.app.route('/static/<path:filename>', methods=['GET'])
        def static_files(filename):
            """Serve static files (CSS, JS, etc.)"""
            return send_from_directory('static', filename)
        
        @self.app.route('/api/status', methods=['GET'])
        def status():
            """Server health check"""
            return jsonify({
                "status": "running",
                "agent_initialized": self.agent is not None,
                "verbose": self.verbose
            })
        
        @self.app.route('/api/mission', methods=['POST'])
        def mission_mode():
            """Execute mission mode request"""
            if not self.agent:
                return jsonify({
                    "success": False,
                    "error": "PX4Agent not initialized",
                    "output": "Server error: Agent not available"
                }), 500
            
            try:
                data = request.get_json()
                if not data or 'user_input' not in data:
                    return jsonify({
                        "success": False,
                        "error": "Missing user_input in request",
                        "output": "Invalid request format"
                    }), 400
                
                user_input = data['user_input']
                result = self.agent.mission_mode(user_input)
                
                # Clean result for JSON serialization
                clean_result = self._clean_result_for_json(result)
                return jsonify(clean_result)
                
            except Exception as e:
                error_msg = str(e)
                if self.verbose:
                    error_msg += f"\n{traceback.format_exc()}"
                
                return jsonify({
                    "success": False,
                    "mode": "mission",
                    "error": error_msg,
                    "output": f"Mission request failed: {str(e)}"
                }), 500
        
        @self.app.route('/api/command', methods=['POST'])
        def command_mode():
            """Execute command mode request"""
            if not self.agent:
                return jsonify({
                    "success": False,
                    "error": "PX4Agent not initialized",
                    "output": "Server error: Agent not available"
                }), 500
            
            try:
                data = request.get_json()
                if not data or 'user_input' not in data:
                    return jsonify({
                        "success": False,
                        "error": "Missing user_input in request",
                        "output": "Invalid request format"
                    }), 400
                
                user_input = data['user_input']
                result = self.agent.command_mode(user_input)
                
                # Clean result for JSON serialization
                clean_result = self._clean_result_for_json(result)
                return jsonify(clean_result)
                
            except Exception as e:
                error_msg = str(e)
                if self.verbose:
                    error_msg += f"\n{traceback.format_exc()}"
                
                return jsonify({
                    "success": False,
                    "mode": "command",
                    "error": error_msg,
                    "output": f"Command request failed: {str(e)}"
                }), 500
        
        @self.app.route('/api/mission/current', methods=['GET'])
        def get_current_mission():
            """Get current mission state"""
            if not self.agent:
                return jsonify({
                    "success": False,
                    "error": "PX4Agent not initialized"
                }), 500
            
            try:
                mission_summary = self.agent.get_mission_summary()
                mission = self.agent.mission_manager.get_mission() if self.agent.mission_manager else None
                
                return jsonify({
                    "success": True,
                    "mission_summary": mission_summary,
                    "mission_state": mission.to_dict(convert_to_absolute=True) if mission else None
                })
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/mission/show', methods=['POST'])
        def show_mission():
            """Show mission for review (like CLI 'show' command)"""
            if not self.agent:
                return jsonify({
                    "success": False,
                    "error": "PX4Agent not initialized"
                }), 500
            
            try:
                mission = self.agent.mission_manager.get_mission() if self.agent.mission_manager else None
                
                if mission and mission.items:
                    return jsonify({
                        "success": True,
                        "mode": "mission_review",
                        "output": f"Mission review: {len(mission.items)} items",
                        "mission_state": mission.to_dict(convert_to_absolute=True)
                    })
                else:
                    return jsonify({
                        "success": True,
                        "mode": "mission_review",
                        "output": "Mission is empty",
                        "mission_state": None
                    })
                    
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/config', methods=['POST'])
        def update_config():
            """Reload configuration"""
            try:
                data = request.get_json()
                config_path = data.get('config_path') if data else None
                
                if config_path:
                    reload_settings(config_path)
                
                # Reinitialize agent with new settings
                self._initialize_agent()
                
                return jsonify({
                    "success": True,
                    "message": "Configuration reloaded"
                })
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/settings/takeoff', methods=['GET'])
        def get_takeoff_settings():
            """Get current takeoff settings"""
            try:
                settings = get_current_takeoff_settings()
                return jsonify({
                    "success": True,
                    "settings": settings
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/settings/takeoff', methods=['POST'])
        def update_takeoff_settings_endpoint():
            """Update takeoff settings at runtime"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": "No data provided"
                    }), 400
                
                # Check if at least one field is provided
                provided_fields = [field for field in ['latitude', 'longitude', 'heading'] if field in data]
                if not provided_fields:
                    return jsonify({
                        "success": False,
                        "error": "At least one field (latitude, longitude, heading) must be provided"
                    }), 400
                
                # Get current settings first
                current_settings = get_current_takeoff_settings()
                
                # Extract and validate provided fields
                latitude = current_settings['latitude']
                longitude = current_settings['longitude']
                heading = current_settings['heading']
                
                try:
                    if 'latitude' in data:
                        latitude = float(data['latitude'])
                    if 'longitude' in data:
                        longitude = float(data['longitude'])
                    if 'heading' in data:
                        heading = str(data['heading']).strip()
                except (ValueError, TypeError) as e:
                    return jsonify({
                        "success": False,
                        "error": f"Invalid data format: {str(e)}"
                    }), 400
                
                # Update settings with merged values
                update_takeoff_settings(latitude, longitude, heading)
                
                return jsonify({
                    "success": True,
                    "message": "Takeoff settings updated successfully",
                    "settings": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "heading": heading
                    }
                })
                
            except ValueError as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 400
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Failed to update settings: {str(e)}"
                }), 500
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the Flask server"""
        print(f"🌐 Starting PX4Agent server on http://{host}:{port}")
        print(f"📍 Mission endpoint: POST http://{host}:{port}/api/mission")
        print(f"⚡ Command endpoint: POST http://{host}:{port}/api/command")
        print(f"💚 Status endpoint: GET http://{host}:{port}/api/status")
        
        self.app.run(host=host, port=port, debug=debug)


def main():
    """Main server entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PX4 Agent Flask Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    parser.add_argument("--config", "-c", type=str, help="Path to configuration file")
    
    args = parser.parse_args()
    
    # Load configuration if specified
    if args.config:
        try:
            reload_settings(args.config)
            print(f"📝 Loaded configuration from {args.config}")
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return 1
    
    # Create and run server
    try:
        server = PX4AgentServer(verbose=args.verbose)
        server.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())