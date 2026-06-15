class ChatSidebar {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.ws = null;
        this.sessionId = null;
        this.messageContainer = null;
        this._initDOM();
    }

    _initDOM() {
        if (!this.container) return;
        this.container.innerHTML = `
            <div class="chat-header" style="font-weight: bold; padding: 10px; background: #333; color: white;">Conversational Agent / MCP</div>
            <div id="chat-messages" style="flex-grow: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; background: #fafafa;"></div>
            <div class="chat-input-area" style="padding: 10px; border-top: 1px solid #ccc; background: white; display: flex;">
                <input type="text" id="chat-input" placeholder="Say 'start fluid' or 'search'..." style="flex-grow: 1; padding: 8px;">
                <button id="chat-send" style="padding: 8px 12px; margin-left: 5px; cursor: pointer;">Send</button>
            </div>
        `;
        this.messageContainer = document.getElementById('chat-messages');
        const sendBtn = document.getElementById('chat-send');
        const inputField = document.getElementById('chat-input');
        
        sendBtn.onclick = () => this.sendMessage(inputField.value);
        inputField.onkeypress = (e) => { if (e.key === 'Enter') this.sendMessage(inputField.value); };
        
        this._createSession();
    }

    async _createSession() {
        try {
            const res = await fetch('/api/chat/session', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title: "New Session"})
            });
            const data = await res.json();
            this.sessionId = data.session_id;
            this._connectWS();
        } catch(e) {
            console.error("Failed to create chat session", e);
        }
    }

    _connectWS() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/chat/${this.sessionId}`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this._handleStreamToken(data);
        };
        
        this.ws.onopen = () => {
             this._appendSystemMessage("Chat connected. Ready for tasks.");
        };
    }

    _appendSystemMessage(text) {
        const div = document.createElement('div');
        div.style = "color: gray; font-size: 0.8em; margin-bottom: 5px; text-align: center;";
        div.innerText = text;
        this.messageContainer.appendChild(div);
    }

    sendMessage(text, nodeContext = null) {
        if (!text || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        
        // Rendering User Bubble
        const userDiv = document.createElement('div');
        userDiv.style = "background: #007bff; color: white; padding: 8px 12px; border-radius: 12px; margin-bottom: 10px; align-self: flex-end; max-width: 80%;";
        userDiv.innerText = text;
        this.messageContainer.appendChild(userDiv);
        
        // Prepare Assistant Bubble
        this.currentAssistantDiv = document.createElement('div');
        this.currentAssistantDiv.style = "background: #eee; color: black; padding: 8px 12px; border-radius: 12px; margin-bottom: 15px; align-self: flex-start; max-width: 80%; word-wrap: break-word; white-space: pre-wrap;";
        this.messageContainer.appendChild(this.currentAssistantDiv);

        this.ws.send(JSON.stringify({
            content: text,
            node_context: nodeContext
        }));
        
        document.getElementById('chat-input').value = "";
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }

    _handleStreamToken(payload) {
        if (!this.currentAssistantDiv) return;
        
        if (payload.type === "token") {
            this.currentAssistantDiv.innerText += payload.content;
        } 
        else if (payload.type === "tool_call") {
            const toolTag = document.createElement('div');
            toolTag.style = "background: #fff3cd; color: #856404; font-size: 0.85em; padding: 6px; border-radius: 4px; margin-top: 8px; font-family: monospace;";
            toolTag.innerText = `⚙️ Call: ${payload.tool_name}(${JSON.stringify(payload.tool_input).length > 20 ? '{...}' : JSON.stringify(payload.tool_input)})`;
            this.currentAssistantDiv.appendChild(toolTag);
        }
        else if (payload.type === "tool_result") {
            const resultTag = document.createElement('div');
            resultTag.style = "background: #d4edda; color: #155724; font-size: 0.85em; padding: 6px; border-radius: 4px; margin-top: 4px; border-left: 4px solid #28a745; font-family: monospace;";
            let displayResult = payload.tool_output.status || (payload.tool_output.results ? payload.tool_output.results.length + ' documents found' : 'completed');
            resultTag.innerText = `✅ Result: ${displayResult}`;
            this.currentAssistantDiv.appendChild(resultTag);
        }
        else if (payload.type === "done") {
             // Reached end of LLM generation stream
        }
        
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }
}
window.ChatSidebar = ChatSidebar;
