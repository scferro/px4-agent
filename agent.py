"""
PX4 Agent Main Class
Handles different modes: command, mission_new, mission_update
"""

from typing import Dict, Any, Optional, List
import json
import uuid
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage

from tools import get_px4_tools
from models import create_ollama_interface, check_ollama_setup
from prompts import get_system_prompt
from config import get_settings
from core import MissionManager

class PX4Agent:
    """Main PX4 mission planning agent"""
    
    def __init__(self, verbose: bool = False):
        self.settings = get_settings()
        self.verbose = verbose or self.settings.agent.verbose_default
        
        # Initialize components
        self.ollama_interface = create_ollama_interface()
        self.tools = get_px4_tools()
        self.mission_manager = self._get_shared_mission_manager()
        
        # Debug: print tool info
        if self.verbose:
            print(f"🔧 DEBUG: Loaded {len(self.tools)} tools:")
            for tool in self.tools:
                print(f"  - {tool.name}: {tool.description}")
        
        # Agent state
        self.current_mode = None
        self.agent_executor = None
        self.chat_history = []
        
        # Initialize agent
        self._initialize_agent()
    
    def _get_shared_mission_manager(self) -> MissionManager:
        """Get shared mission manager instance from tools"""
        # Find a tool with mission manager and share it
        for tool in self.tools:
            if hasattr(tool, 'mission_manager'):
                return tool.mission_manager
        return MissionManager()
    
    def _initialize_agent(self):
        """Initialize the LangGraph agent"""
        try:
            # Get LLM
            llm = self.ollama_interface.get_llm()
            
            # Create a simple system message for LangGraph
            from langchain_core.messages import SystemMessage
            
            # Create the LangGraph ReAct agent with a checkpointer for state management
            from langgraph.checkpoint.memory import InMemorySaver
            checkpointer = InMemorySaver()
            
            # Debug: Check if LLM supports tool calling
            if self.verbose:
                print(f"🔧 DEBUG: LLM type: {type(llm)}")
                print(f"🔧 DEBUG: LLM has bind_tools: {hasattr(llm, 'bind_tools')}")
                try:
                    bound_llm = llm.bind_tools(self.tools)
                    print(f"🔧 DEBUG: Successfully bound tools to LLM")
                except Exception as e:
                    print(f"🔧 DEBUG: Failed to bind tools: {e}")
            
            # Create the agent graph - this will continue until no more tool calls
            self.agent_graph = create_react_agent(
                model=llm,
                tools=self.tools,
                checkpointer=checkpointer
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize agent: {str(e)}")
    
    
    def check_system_status(self) -> Dict[str, Any]:
        """Check system status and readiness"""
        # Check Ollama setup
        ollama_ok, ollama_issues = check_ollama_setup()
        
        # Get system info
        system_info = self.ollama_interface.get_system_info()
        
        return {
            "ollama_ready": ollama_ok,
            "ollama_issues": ollama_issues,
            "system_info": system_info,
            "tools_loaded": len(self.tools),
            "agent_initialized": self.agent_graph is not None,
            "current_mode": self.current_mode,
            "current_mission_exists": self.mission_manager.has_mission()
        }
    
    def command_mode(self, user_input: str) -> Dict[str, Any]:
        """Execute single command mode"""
        self.current_mode = "command"
        
        system_prompt = get_system_prompt("command")
        
        try:
            # LangGraph uses messages instead of system_prompt/input format
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]
            
            # Need to provide thread_id for checkpointer
            config = {"configurable": {"thread_id": "command_thread"}}
            result = self.agent_graph.invoke({
                "messages": messages
            }, config=config)
            
            # LangGraph returns messages, extract the final AI response
            final_message = result["messages"][-1]
            output = final_message.content if hasattr(final_message, 'content') else str(final_message)
            
            return {
                "success": True,
                "mode": "command",
                "input": user_input,
                "output": output,
                "intermediate_steps": result.get("messages", []) if self.verbose else []
            }
            
        except Exception as e:
            return {
                "success": False,
                "mode": "command",
                "input": user_input,
                "error": str(e),
                "output": f"Command execution failed: {str(e)}"
            }
    
    def mission_mode_new(self, user_input: str) -> Dict[str, Any]:
        """Execute mission mode with new mission"""
        self.current_mode = "mission_new"
        
        
        # Only clear chat history and create new mission if no mission exists
        if not self.mission_manager.has_mission():
            self.chat_history = []
            self.mission_manager.create_mission()
        
        # Get current mission state for prompt
        mission_state = "Empty mission - no items yet"
        mission = self.mission_manager.get_mission()
        if mission and mission.items:
                mission_state = f"Current items: {len(mission.items)}\n"
                for i, item in enumerate(mission.items, 1):
                    cmd_name = self._get_command_name(item.command)
                    mission_state += f"{i}. {cmd_name} - Lat: {item.x:.6f}, Lon: {item.y:.6f}, Alt: {item.z:.1f}m\n"
        
        system_prompt = get_system_prompt("mission_new", current_mission_state=mission_state)
        
        try:
            # Save debug prompt before calling model
            with open("current_prompt_debug.txt", "w") as f:
                f.write(f"=== SYSTEM PROMPT ===\n{system_prompt}\n\n=== CHAT HISTORY ===\n{self.chat_history}\n\n=== USER INPUT ===\n{user_input}\n")
            
            # LangGraph uses messages instead of system_prompt/input format
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]
            
            
            # Add chat history messages if any
            for msg in self.chat_history:
                if isinstance(msg, (HumanMessage, AIMessage)):
                    messages.append(msg)
            
            
            # Let LangGraph handle the conversation flow - it will continue until no more tool calls
            config = {"configurable": {"thread_id": "mission_thread"}}
            
            result = self.agent_graph.invoke({
                "messages": messages
            }, config=config)
            
            # In verbose mode, print the full conversation chain
            if self.verbose:
                print("\n🔍 VERBOSE: Agent Conversation Chain")
                print("=" * 50)
                for i, msg in enumerate(result["messages"]):
                    msg_type = type(msg).__name__
                    print(f"{i}. {msg_type}:")
                    if hasattr(msg, 'content') and msg.content:
                        content_preview = msg.content
                        print(f"   Content: {content_preview}")
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        print(f"   Tool calls: {msg.tool_calls}")
                    if hasattr(msg, 'name') and msg.name:
                        print(f"   Tool name: {msg.name}")
                    print()
                
                # Count executions
                tool_calls = sum(len(msg.tool_calls) if hasattr(msg, 'tool_calls') and msg.tool_calls else 0 
                               for msg in result["messages"])
                tool_executions = len([msg for msg in result["messages"] if msg.__class__.__name__ == 'ToolMessage'])
                print(f"📊 Summary: {tool_calls} tool calls made, {tool_executions} tools executed")
                print("=" * 50)

            # Find the last AI message (not ToolMessage)
            final_ai_message = None
            for msg in reversed(result["messages"]):
                if msg.__class__.__name__ == 'AIMessage':
                    final_ai_message = msg
                    break
            
            if final_ai_message:
                output = final_ai_message.content if hasattr(final_ai_message, 'content') else str(final_ai_message)
                # Debug: show what we actually got
                if self.verbose:
                    print(f"🔧 DEBUG: Final AI message content: {repr(output)}")
            else:
                output = "No AI response found"
            
            

            # Save intermediate steps to chat history
            if self.verbose:
                self.chat_history.extend(result.get("messages", []))

            # Get final mission state  
            mission = self.mission_manager.get_mission()
            
            mission_state = mission.to_dict() if mission else None
            
            return {
                "success": True,
                "mode": "mission_new", 
                "input": user_input,
                "output": output,
                "mission_state": mission_state,
                "intermediate_steps": result.get("messages", []) if self.verbose else []
            }
            
        except Exception as e:
            return {
                "success": False,
                "mode": "mission_new",
                "input": user_input,
                "error": str(e),
                "output": f"Mission creation failed: {str(e)}"
            }
    
    def mission_mode_update(self, user_input: str, current_mission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mission mode with existing mission update"""
        self.current_mode = "mission_update"
        
        # Load current mission into mission manager
        self._load_mission_from_data(current_mission_data)
        
        # Create system prompt with mission context
        mission_context = json.dumps(current_mission_data, indent=2)
        system_prompt = get_system_prompt("mission_update", mission_context)
        
        # Enhance input with mission context
        enhanced_input = f"Update Request: {user_input}"
        
        try:
            # LangGraph uses messages instead of system_prompt/input format
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=enhanced_input)
            ]
            
            # Need to provide thread_id for checkpointer
            config = {"configurable": {"thread_id": "update_thread"}}
            result = self.agent_graph.invoke({
                "messages": messages
            }, config=config)
            
            # Get updated mission state
            mission = self.mission_manager.get_mission()
            mission_state = mission.to_dict() if mission else None
            
            # LangGraph returns messages, extract the final AI response
            final_message = result["messages"][-1]
            output = final_message.content if hasattr(final_message, 'content') else str(final_message)
            
            return {
                "success": True,
                "mode": "mission_update",
                "input": user_input,
                "output": output,
                "original_mission": current_mission_data,
                "updated_mission_state": mission_state,
                "intermediate_steps": result.get("messages", []) if self.verbose else []
            }
            
        except Exception as e:
            return {
                "success": False,
                "mode": "mission_update",
                "input": user_input,
                "error": str(e),
                "output": f"Mission update failed: {str(e)}"
            }
    
    def _load_mission_from_data(self, mission_data: Dict[str, Any]):
        """Load mission data into mission manager"""
        try:
            # Create new current mission
            self.mission_manager.create_mission()
            mission = self.mission_manager.get_mission()
            if mission:
                # Clear existing items
                mission.clear_items()
                
                # Load items from data
                items_data = mission_data.get('items', [])
                for item_data in items_data:
                    from core.mission import MissionItem
                    item = MissionItem(
                        seq=item_data.get('seq', 0),
                        frame=item_data.get('frame', 0),
                        command=item_data.get('command', 0),
                        current=item_data.get('current', 0),
                        autocontinue=item_data.get('autocontinue', 1),
                        param1=item_data.get('param1', 0.0),
                        param2=item_data.get('param2', 0.0),
                        param3=item_data.get('param3', 0.0),
                        param4=item_data.get('param4', 0.0),
                        x=item_data.get('x', 0.0),
                        y=item_data.get('y', 0.0),
                        z=item_data.get('z', 0.0)
                    )
                    mission.items.append(item)
                
        except Exception as e:
            raise RuntimeError(f"Failed to load mission data: {str(e)}")
    
    def get_mission_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of current mission"""
        mission = self.mission_manager.get_mission()
        if not mission:
            return None
        
        # Validate mission
        valid, errors = self.mission_manager.validate_mission()
        
        # Count different command types
        command_counts = {}
        for item in mission.items:
            cmd_name = self._get_command_name(item.command)
            command_counts[cmd_name] = command_counts.get(cmd_name, 0) + 1
        
        return {
            "total_items": len(mission.items),
            "valid": valid,
            "errors": errors,
            "command_counts": command_counts,
            "created_at": mission.created_at.isoformat(),
            "modified_at": mission.modified_at.isoformat()
        }
    
    def _get_command_name(self, command_id: int) -> str:
        """Get human-readable command name"""
        from core.constants import MAV_CMD
        
        command_map = {
            MAV_CMD.NAV_WAYPOINT: "Waypoint",
            MAV_CMD.NAV_TAKEOFF: "Takeoff", 
            MAV_CMD.NAV_RETURN_TO_LAUNCH: "Return to Launch",
            MAV_CMD.NAV_LOITER_TIME: "Loiter (Timed)",
            MAV_CMD.NAV_LOITER_UNLIM: "Loiter (Unlimited)",
            MAV_CMD.DO_CHANGE_SPEED: "Change Speed"
        }
        
        return command_map.get(command_id, f"Command {command_id}")
    
    def get_current_mission_status(self) -> Optional[Dict[str, Any]]:
        """Get current mission status"""
        return self.get_mission_summary()
    
    def list_missions(self) -> List[Dict[str, Any]]:
        """List current mission (single mission approach)"""
        mission_summary = self.get_mission_summary()
        if mission_summary:
            return [mission_summary]
        else:
            return []