/**
 * PX4 Agent Web Chat Interface
 * JavaScript API client and chat functionality
 */

class PX4AgentClient {
    constructor() {
        this.baseUrl = window.location.origin;
        this.currentMode = 'mission';
        this.isConnected = false;
        this.isProcessing = false;
        
        this.initializeElements();
        this.attachEventListeners();
        this.checkServerConnection();
    }
    
    initializeElements() {
        // Get DOM elements
        this.elements = {
            // Status elements
            statusDot: document.getElementById('statusDot'),
            statusText: document.getElementById('statusText'),
            
            // Mode elements
            missionModeBtn: document.getElementById('missionModeBtn'),
            commandModeBtn: document.getElementById('commandModeBtn'),
            missionDesc: document.getElementById('missionDesc'),
            commandDesc: document.getElementById('commandDesc'),
            
            // Chat elements
            chatMessages: document.getElementById('chatMessages'),
            messageInput: document.getElementById('messageInput'),
            sendButton: document.getElementById('sendButton'),
            
            // Mission state elements
            missionItems: document.getElementById('missionItems'),
            
            // Loading elements
            loadingOverlay: document.getElementById('loadingOverlay')
        };
    }
    
    attachEventListeners() {
        // Mode switching
        this.elements.missionModeBtn.addEventListener('click', () => this.switchMode('mission'));
        this.elements.commandModeBtn.addEventListener('click', () => this.switchMode('command'));
        
        // Remove Enter key handling - now only use send button
        
        this.elements.messageInput.addEventListener('input', () => {
            this.updateSendButton();
        });
        
        this.elements.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Initial state
        this.updateSendButton();
    }
    
    async checkServerConnection() {
        try {
            const response = await fetch(`${this.baseUrl}/api/status`);
            const status = await response.json();
            
            this.isConnected = status.agent_initialized === true;
            this.updateConnectionStatus();
            
        } catch (error) {
            console.error('Connection check failed:', error);
            this.isConnected = false;
            this.updateConnectionStatus();
        }
    }
    
    updateConnectionStatus() {
        if (this.isConnected) {
            this.elements.statusDot.classList.add('connected');
            this.elements.statusText.textContent = 'Connected';
        } else {
            this.elements.statusDot.classList.remove('connected');
            this.elements.statusText.textContent = 'Disconnected';
        }
        
        this.updateSendButton();
    }
    
    switchMode(mode) {
        this.currentMode = mode;
        
        // Update button states
        this.elements.missionModeBtn.classList.toggle('active', mode === 'mission');
        this.elements.commandModeBtn.classList.toggle('active', mode === 'command');
        
        // Update descriptions
        this.elements.missionDesc.classList.toggle('active', mode === 'mission');
        this.elements.commandDesc.classList.toggle('active', mode === 'command');
        
        // Clear chat and mission state when switching modes
        this.clearChat();
        this.clearMissionState();
        
        if (mode === 'command') {
            this.addMessage('agent', 'Switched to Command Mode. Each command will create a fresh mission.');
        } else {
            this.addMessage('agent', 'Switched to Mission Mode. Build your mission step by step.');
        }
        
        // Focus input
        this.elements.messageInput.focus();
    }
    
    updateSendButton() {
        const hasText = this.elements.messageInput.value.trim().length > 0;
        const canSend = this.isConnected && hasText && !this.isProcessing;
        
        this.elements.sendButton.disabled = !canSend;
    }
    
    async sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message || !this.isConnected || this.isProcessing) {
            return;
        }
        
        // Handle special commands
        if (message.toLowerCase() === 'show' || message.toLowerCase() === 'review') {
            this.showMissionReview();
            this.elements.messageInput.value = '';
            this.updateSendButton();
            return;
        }
        
        if (message.toLowerCase() === 'clear') {
            this.clearChat();
            this.elements.messageInput.value = '';
            this.updateSendButton();
            return;
        }
        
        // Add user message to chat
        this.addMessage('user', message);
        
        // Clear input and show loading
        this.elements.messageInput.value = '';
        this.updateSendButton();
        this.showLoading(true);
        this.isProcessing = true;
        
        try {
            // Send request to appropriate endpoint
            const endpoint = this.currentMode === 'mission' ? '/api/mission' : '/api/command';
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_input: message
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Add agent response
                if (result.output) {
                    this.addMessage('agent', result.output);
                }
                
                // Update mission state
                if (result.mission_state) {
                    this.updateMissionState(result.mission_state);
                }
            } else {
                // Show error message
                this.addMessage('error', `Error: ${result.error || 'Unknown error occurred'}`);
            }
            
        } catch (error) {
            console.error('Request failed:', error);
            this.addMessage('error', `Connection failed: ${error.message}`);
            this.isConnected = false;
            this.updateConnectionStatus();
        } finally {
            this.showLoading(false);
            this.isProcessing = false;
            this.updateSendButton();
            this.elements.messageInput.focus();
        }
    }
    
    async showMissionReview() {
        this.showLoading(true);
        
        try {
            const response = await fetch(`${this.baseUrl}/api/mission/show`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.addMessage('agent', result.output || 'Mission reviewed');
                if (result.mission_state) {
                    this.updateMissionState(result.mission_state);
                }
            } else {
                this.addMessage('error', `Error: ${result.error || 'Failed to show mission'}`);
            }
            
        } catch (error) {
            console.error('Mission review failed:', error);
            this.addMessage('error', `Connection failed: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }
    
    addMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Process content for better display
        if (typeof content === 'string') {
            // Convert newlines to <br> and preserve formatting
            contentDiv.innerHTML = content
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>');
        } else {
            contentDiv.textContent = String(content);
        }
        
        messageDiv.appendChild(contentDiv);
        this.elements.chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    }
    
    clearChat() {
        // Remove all messages except welcome message
        const messages = this.elements.chatMessages.querySelectorAll('.message:not(.welcome-message)');
        messages.forEach(msg => msg.remove());
    }
    
    clearMissionState() {
        // Reset mission state panel to empty state
        this.elements.missionItems.innerHTML = '<div class="empty-mission">No mission items yet</div>';
    }
    
    updateMissionState(missionState) {
        if (!missionState || !missionState.items || missionState.items.length === 0) {
            this.elements.missionItems.innerHTML = '<div class="empty-mission">No mission items yet</div>';
            return;
        }
        
        const itemsHtml = missionState.items.map((item, index) => {
            const commandType = item.command_type || 'unknown';
            const emoji = this.getCommandEmoji(commandType);
            
            let details = [];
            
            // Add altitude info
            if (item.altitude !== null && item.altitude !== undefined) {
                details.push(`Altitude: ${item.altitude} ${item.altitude_units || 'units'}`);
            }
            
            // Add position info
            if (item.latitude !== null && item.longitude !== null) {
                details.push(`Position: ${item.latitude.toFixed(6)}, ${item.longitude.toFixed(6)}`);
            } else if (item.mgrs) {
                details.push(`Position: MGRS ${item.mgrs}`);
            } else if (item.distance && item.heading) {
                details.push(`Position: ${item.distance} ${item.distance_units || 'units'} ${item.heading}`);
            }
            
            // Add radius for loiter/survey
            if (item.radius !== null && item.radius !== undefined) {
                details.push(`Radius: ${item.radius} ${item.radius_units || 'units'}`);
            }
            
            // Add search parameters
            if (item.search_target) {
                details.push(`Target: ${item.search_target}`);
            }
            if (item.detection_behavior) {
                details.push(`Behavior: ${item.detection_behavior}`);
            }
            
            return `
                <div class="mission-item">
                    <div class="mission-item-header">
                        ${emoji} ${index + 1}. ${commandType.toUpperCase()}
                    </div>
                    <div class="mission-item-details">
                        ${details.map(detail => `<div>${detail}</div>`).join('')}
                    </div>
                </div>
            `;
        }).join('');
        
        this.elements.missionItems.innerHTML = itemsHtml;
    }
    
    getCommandEmoji(commandType) {
        const emojis = {
            'takeoff': '🚀',
            'waypoint': '📍',
            'loiter': '🔄',
            'survey': '🗺️',
            'rtl': '🏠'
        };
        return emojis[commandType] || '❓';
    }
    
    showLoading(show) {
        if (show) {
            this.elements.loadingOverlay.classList.add('active');
        } else {
            this.elements.loadingOverlay.classList.remove('active');
        }
    }
}

// Initialize the client when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.px4Client = new PX4AgentClient();
});