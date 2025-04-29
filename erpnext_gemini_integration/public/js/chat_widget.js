
frappe.provide("erpnext_gemini_integration.chat_widget");

erpnext_gemini_integration.chat_widget = class ChatWidget {
    constructor(opts) {
        this.opts = opts || {};
        this.container = opts.container || document.body;
        this.position = opts.position || "bottom-right";
        this.title = opts.title || "Gemini Assistant";
        this.placeholder = opts.placeholder || "Ask me anything...";
        this.welcomeMessage = opts.welcomeMessage || "Hello! I'm your Gemini Assistant. How can I help you today?";
        this.apiEndpoint = opts.apiEndpoint || "/api/method/erpnext_gemini_integration.api.chat_api.process_message";
        
        // State variables
        this.isOpen = false;
        this.isLoading = false;
        this.conversationId = null;
        this.messageHistory = [];
        this.contextInfo = {};
        this.fileAttachments = [];
        
        // Initialize the widget
        this.init();
    }
    
    init() {
        this.createWidgetElements();
        this.attachEventListeners();
        this.detectActiveContext();
        this.addWelcomeMessage();
    }
    
    createWidgetElements() {
        // Create main container
        this.widgetContainer = document.createElement("div");
        this.widgetContainer.className = "gemini-chat-widget";
        this.widgetContainer.dataset.position = this.position;
        
        // Create toggle button
        this.toggleButton = document.createElement("button");
        this.toggleButton.className = "gemini-chat-toggle";
        this.toggleButton.innerHTML = `
            <i class="fa fa-robot"></i>
            <span class="gemini-notification-badge hidden"></span>
        `;
        
        // Create chat window
        this.chatWindow = document.createElement("div");
        this.chatWindow.className = "gemini-chat-window hidden";
        
        // Create chat header
        this.chatHeader = document.createElement("div");
        this.chatHeader.className = "gemini-chat-header";
        this.chatHeader.innerHTML = `
            <div class="gemini-chat-title">
                <i class="fa fa-robot"></i>
                <span>${this.title}</span>
            </div>
            <div class="gemini-chat-actions">
                <button class="gemini-chat-minimize" title="Minimize">
                    <i class="fa fa-minus"></i>
                </button>
            </div>
        `;
        
        // Create chat body
        this.chatBody = document.createElement("div");
        this.chatBody.className = "gemini-chat-body";
        
        // Create messages container
        this.messagesContainer = document.createElement("div");
        this.messagesContainer.className = "gemini-chat-messages";
        
        // Create input area
        this.inputArea = document.createElement("div");
        this.inputArea.className = "gemini-chat-input-area";
        
        // Create input container
        this.inputContainer = document.createElement("div");
        this.inputContainer.className = "gemini-chat-input-container";
        
        // Create text input
        this.textInput = document.createElement("textarea");
        this.textInput.className = "gemini-chat-input";
        this.textInput.placeholder = this.placeholder;
        this.textInput.rows = 1;
        
        // Create send button
        this.sendButton = document.createElement("button");
        this.sendButton.className = "gemini-chat-send";
        this.sendButton.innerHTML = `<i class="fa fa-paper-plane"></i>`;
        this.sendButton.disabled = true;
        
        // Create attachment button
        this.attachButton = document.createElement("button");
        this.attachButton.className = "gemini-chat-attach";
        this.attachButton.innerHTML = `<i class="fa fa-paperclip"></i>`;
        
        // Create file input (hidden)
        this.fileInput = document.createElement("input");
        this.fileInput.type = "file";
        this.fileInput.className = "gemini-chat-file-input";
        this.fileInput.multiple = true;
        this.fileInput.accept = ".pdf,.csv,.txt,.jpg,.jpeg,.png";
        this.fileInput.style.display = "none";
        
        // Create attachments container
        this.attachmentsContainer = document.createElement("div");
        this.attachmentsContainer.className = "gemini-chat-attachments hidden";
        
        // Assemble the widget
        this.inputContainer.appendChild(this.textInput);
        this.inputContainer.appendChild(this.sendButton);
        this.inputContainer.appendChild(this.attachButton);
        this.inputContainer.appendChild(this.fileInput);
        
        this.inputArea.appendChild(this.inputContainer);
        this.inputArea.appendChild(this.attachmentsContainer);
        
        this.chatBody.appendChild(this.messagesContainer);
        
        this.chatWindow.appendChild(this.chatHeader);
        this.chatWindow.appendChild(this.chatBody);
        this.chatWindow.appendChild(this.inputArea);
        
        this.widgetContainer.appendChild(this.toggleButton);
        this.widgetContainer.appendChild(this.chatWindow);
        
        // Add to container
        this.container.appendChild(this.widgetContainer);
        
        // Add styles
        this.addStyles();
    }
    
    addStyles() {
        // Check if styles already exist
        if (document.getElementById("gemini-chat-styles")) {
            return;
        }
        
        // Create style element
        const style = document.createElement("style");
        style.id = "gemini-chat-styles";
        style.textContent = `
            .gemini-chat-widget {
                position: fixed;
                z-index: 1000;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
            }
            
            .gemini-chat-widget[data-position="bottom-right"] {
                right: 20px;
                bottom: 20px;
            }
            
            .gemini-chat-widget[data-position="bottom-left"] {
                left: 20px;
                bottom: 20px;
            }
            
            .gemini-chat-toggle {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background-color: #4285f4;
                color: white;
                border: none;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
                cursor: pointer;
                position: relative;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .gemini-chat-toggle:hover {
                background-color: #3367d6;
                transform: scale(1.05);
            }
            
            .gemini-chat-toggle i {
                font-size: 24px;
            }
            
            .gemini-notification-badge {
                position: absolute;
                top: 0;
                right: 0;
                background-color: #ea4335;
                color: white;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                font-size: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .gemini-notification-badge.hidden {
                display: none;
            }
            
            .gemini-chat-window {
                position: absolute;
                bottom: 80px;
                right: 0;
                width: 350px;
                height: 500px;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
                display: flex;
                flex-direction: column;
                overflow: hidden;
                transition: all 0.3s ease;
            }
            
            .gemini-chat-widget[data-position="bottom-left"] .gemini-chat-window {
                left: 0;
                right: auto;
            }
            
            .gemini-chat-window.hidden {
                opacity: 0;
                visibility: hidden;
                transform: translateY(20px);
            }
            
            .gemini-chat-header {
                background-color: #4285f4;
                color: white;
                padding: 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .gemini-chat-title {
                display: flex;
                align-items: center;
                font-weight: bold;
            }
            
            .gemini-chat-title i {
                margin-right: 10px;
            }
            
            .gemini-chat-actions button {
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                padding: 5px;
                margin-left: 5px;
            }
            
            .gemini-chat-body {
                flex: 1;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }
            
            .gemini-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 15px;
                display: flex;
                flex-direction: column;
                gap: 15px;
            }
            
            .gemini-chat-message {
                max-width: 80%;
                padding: 10px 15px;
                border-radius: 18px;
                position: relative;
                line-height: 1.5;
                font-size: 14px;
            }
            
            .gemini-chat-message.user {
                align-self: flex-end;
                background-color: #4285f4;
                color: white;
                border-bottom-right-radius: 5px;
            }
            
            .gemini-chat-message.assistant {
                align-self: flex-start;
                background-color: #f1f3f4;
                color: #202124;
                border-bottom-left-radius: 5px;
            }
            
            .gemini-chat-message-content {
                word-wrap: break-word;
            }
            
            .gemini-chat-message-content pre {
                background-color: rgba(0, 0, 0, 0.1);
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                font-family: monospace;
            }
            
            .gemini-chat-message-content code {
                font-family: monospace;
                background-color: rgba(0, 0, 0, 0.1);
                padding: 2px 4px;
                border-radius: 3px;
            }
            
            .gemini-chat-message-content a {
                color: inherit;
                text-decoration: underline;
            }
            
            .gemini-chat-message-content ul, 
            .gemini-chat-message-content ol {
                padding-left: 20px;
                margin: 10px 0;
            }
            
            .gemini-chat-message-timestamp {
                font-size: 10px;
                opacity: 0.7;
                margin-top: 5px;
                text-align: right;
            }
            
            .gemini-chat-message-actions {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                margin-top: 5px;
            }
            
            .gemini-chat-message-action {
                background: none;
                border: none;
                color: inherit;
                opacity: 0.7;
                cursor: pointer;
                padding: 2px 5px;
                font-size: 12px;
                border-radius: 3px;
            }
            
            .gemini-chat-message-action:hover {
                opacity: 1;
                background-color: rgba(0, 0, 0, 0.1);
            }
            
            .gemini-chat-input-area {
                padding: 15px;
                border-top: 1px solid #e0e0e0;
            }
            
            .gemini-chat-input-container {
                display: flex;
                align-items: flex-end;
                gap: 10px;
                background-color: #f1f3f4;
                border-radius: 20px;
                padding: 10px 15px;
            }
            
            .gemini-chat-input {
                flex: 1;
                border: none;
                background: none;
                resize: none;
                outline: none;
                font-family: inherit;
                font-size: 14px;
                max-height: 100px;
                overflow-y: auto;
            }
            
            .gemini-chat-send, 
            .gemini-chat-attach {
                background: none;
                border: none;
                color: #4285f4;
                cursor: pointer;
                padding: 5px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .gemini-chat-send:disabled {
                color: #9aa0a6;
                cursor: not-allowed;
            }
            
            .gemini-chat-attachments {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 10px;
            }
            
            .gemini-chat-attachments.hidden {
                display: none;
            }
            
            .gemini-chat-attachment {
                display: flex;
                align-items: center;
                background-color: #f1f3f4;
                border-radius: 15px;
                padding: 5px 10px;
                font-size: 12px;
                position: relative;
            }
            
            .gemini-chat-attachment i {
                margin-right: 5px;
            }
            
            .gemini-chat-attachment-remove {
                background: none;
                border: none;
                color: #ea4335;
                cursor: pointer;
                padding: 2px;
                margin-left: 5px;
            }
            
            .gemini-chat-typing {
                display: flex;
                align-items: center;
                gap: 5px;
                padding: 10px;
                font-size: 12px;
                color: #5f6368;
            }
            
            .gemini-chat-typing-dot {
                width: 8px;
                height: 8px;
                background-color: #5f6368;
                border-radius: 50%;
                animation: typing-dot 1.4s infinite ease-in-out both;
            }
            
            .gemini-chat-typing-dot:nth-child(1) {
                animation-delay: -0.32s;
            }
            
            .gemini-chat-typing-dot:nth-child(2) {
                animation-delay: -0.16s;
            }
            
            @keyframes typing-dot {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }
            
            .gemini-chat-error {
                color: #ea4335;
                font-size: 12px;
                margin-top: 5px;
                text-align: center;
            }
            
            .gemini-chat-confidence {
                display: inline-block;
                padding: 2px 5px;
                border-radius: 10px;
                font-size: 10px;
                margin-left: 5px;
            }
            
            .gemini-chat-confidence.high {
                background-color: #34a853;
                color: white;
            }
            
            .gemini-chat-confidence.medium {
                background-color: #fbbc05;
                color: black;
            }
            
            .gemini-chat-confidence.low {
                background-color: #ea4335;
                color: white;
            }
            
            /* Responsive styles */
            @media (max-width: 480px) {
                .gemini-chat-window {
                    width: calc(100vw - 40px);
                    height: 60vh;
                    bottom: 80px;
                }
                
                .gemini-chat-widget[data-position="bottom-right"] .gemini-chat-window,
                .gemini-chat-widget[data-position="bottom-left"] .gemini-chat-window {
                    right: 0;
                    left: 0;
                    margin: 0 auto;
                }
            }
        `;
        
        // Add to document head
        document.head.appendChild(style);
    }
    
    attachEventListeners() {
        // Toggle chat window
        this.toggleButton.addEventListener("click", () => {
            this.toggleChatWindow();
        });
        
        // Minimize chat window
        this.chatHeader.querySelector(".gemini-chat-minimize").addEventListener("click", () => {
            this.toggleChatWindow(false);
        });
        
        // Send message on button click
        this.sendButton.addEventListener("click", () => {
            this.sendMessage();
        });
        
        // Send message on Enter key (but allow Shift+Enter for new line)
        this.textInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Enable/disable send button based on input
        this.textInput.addEventListener("input", () => {
            this.adjustTextareaHeight();
            this.sendButton.disabled = !this.textInput.value.trim();
        });
        
        // File attachment
        this.attachButton.addEventListener("click", () => {
            this.fileInput.click();
        });
        
        // Handle file selection
        this.fileInput.addEventListener("change", () => {
            this.handleFileSelection();
        });
    }
    
    toggleChatWindow(open = null) {
        // If open is null, toggle the current state
        this.isOpen = open !== null ? open : !this.isOpen;
        
        if (this.isOpen) {
            this.chatWindow.classList.remove("hidden");
            this.textInput.focus();
            
            // Hide notification badge
            this.toggleButton.querySelector(".gemini-notification-badge").classList.add("hidden");
        } else {
            this.chatWindow.classList.add("hidden");
        }
    }
    
    adjustTextareaHeight() {
        // Reset height to auto to get the correct scrollHeight
        this.textInput.style.height = "auto";
        
        // Set the height based on scrollHeight (with a max height)
        const newHeight = Math.min(this.textInput.scrollHeight, 100);
        this.textInput.style.height = `${newHeight}px`;
    }
    
    addWelcomeMessage() {
        if (this.welcomeMessage) {
            this.addMessage({
                role: "assistant",
                content: this.welcomeMessage,
                timestamp: new Date()
            });
        }
    }
    
    addMessage(message) {
        // Create message element
        const messageEl = document.createElement("div");
        messageEl.className = `gemini-chat-message ${message.role}`;
        
        // Create message content
        const contentEl = document.createElement("div");
        contentEl.className = "gemini-chat-message-content";
        
        // Format message content with Markdown-like syntax
        contentEl.innerHTML = this.formatMessageContent(message.content);
        
        // Create timestamp
        const timestampEl = document.createElement("div");
        timestampEl.className = "gemini-chat-message-timestamp";
        timestampEl.textContent = this.formatTimestamp(message.timestamp);
        
        // Add confidence indicator for assistant messages
        if (message.role === "assistant" && message.confidence) {
            const confidenceEl = document.createElement("span");
            confidenceEl.className = `gemini-chat-confidence ${message.confidence}`;
            confidenceEl.textContent = message.confidence;
            contentEl.appendChild(confidenceEl);
        }
        
        // Add actions for assistant messages
        if (message.role === "assistant") {
            const actionsEl = document.createElement("div");
            actionsEl.className = "gemini-chat-message-actions";
            
            // Add feedback buttons
            const thumbsUpBtn = document.createElement("button");
            thumbsUpBtn.className = "gemini-chat-message-action";
            thumbsUpBtn.innerHTML = `<i class="fa fa-thumbs-up"></i>`;
            thumbsUpBtn.addEventListener("click", () => {
                this.provideFeedback(message.id, "positive");
            });
            
            const thumbsDownBtn = document.createElement("button");
            thumbsDownBtn.className = "gemini-chat-message-action";
            thumbsDownBtn.innerHTML = `<i class="fa fa-thumbs-down"></i>`;
            thumbsDownBtn.addEventListener("click", () => {
                this.provideFeedback(message.id, "negative");
            });
            
            actionsEl.appendChild(thumbsUpBtn);
            actionsEl.appendChild(thumbsDownBtn);
            
            messageEl.appendChild(actionsEl);
        }
        
        // Assemble message
        messageEl.appendChild(contentEl);
        messageEl.appendChild(timestampEl);
        
        // Add to messages container
        this.messagesContainer.appendChild(messageEl);
        
        // Scroll to bottom
        this.scrollToBottom();
        
        // Add to message history
        this.messageHistory.push(message);
    }


    formatMessageContent(content) {
        if (!content) return "";
        
        // Replace newlines with <br>
        let formatted = content.replace(/\n/g, "<br>");
        
        // Format code blocks
        formatted = formatted.replace(/```([a-z]*)\n([\s\S]*?)\n```/g, (match, language, code) => {
            return `<pre><code class="language-${language}">${this.escapeHtml(code)}</code></pre>`;
        });
        
        // Format inline code
        formatted = formatted.replace(/`([^`]+)`/g, (match, code) => {
            return `<code>${this.escapeHtml(code)}</code>`;
        });
        
        // Format bold text
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        
        // Format italic text
        formatted = formatted.replace(/\*([^*]+)\*/g, "<em>$1</em>");
        
        // Format links
        formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, "<a href='$2' target='_blank'>$1</a>");
        
        // Format lists
        formatted = formatted.replace(/^\s*-\s+(.+)$/gm, "<li>$1</li>");
        formatted = formatted.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");
        
        // Format numbered lists
        formatted = formatted.replace(/^\s*(\d+)\.\s+(.+)$/gm, "<li>$2</li>");
        formatted = formatted.replace(/(<li>.*<\/li>)/s, "<ol>$1</ol>");
        
        return formatted;
    }
    
    escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    sendMessage() {
        const message = this.textInput.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        this.addMessage({
            role: "user",
            content: message,
            timestamp: new Date()
        });
        
        // Clear input
        this.textInput.value = "";
        this.adjustTextareaHeight();
        this.sendButton.disabled = true;
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Prepare files if any
        const files = this.prepareFileAttachments();
        
        // Send message to server
        this.sendMessageToServer(message, files);
        
        // Clear attachments
        this.clearAttachments();
    }
    
    showTypingIndicator() {
        // Create typing indicator
        const typingIndicator = document.createElement("div");
        typingIndicator.className = "gemini-chat-typing";
        typingIndicator.innerHTML = `
            <div class="gemini-chat-typing-dot"></div>
            <div class="gemini-chat-typing-dot"></div>
            <div class="gemini-chat-typing-dot"></div>
        `;
        
        // Add to messages container
        this.messagesContainer.appendChild(typingIndicator);
        
        // Scroll to bottom
        this.scrollToBottom();
        
        // Store reference to remove later
        this.typingIndicator = typingIndicator;
        
        // Set loading state
        this.isLoading = true;
    }
    
    hideTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.remove();
            this.typingIndicator = null;
        }
        
        // Reset loading state
        this.isLoading = false;
    }
    
    handleFileSelection() {
        const files = this.fileInput.files;
        
        if (!files || files.length === 0) return;
        
        // Clear previous attachments
        this.clearAttachments();
        
        // Process each file
        Array.from(files).forEach(file => {
            this.addFileAttachment(file);
        });
        
        // Show attachments container
        this.attachmentsContainer.classList.remove("hidden");
        
        // Reset file input
        this.fileInput.value = "";
    }
    
    addFileAttachment(file) {
        // Create attachment element
        const attachmentEl = document.createElement("div");
        attachmentEl.className = "gemini-chat-attachment";
        
        // Determine icon based on file type
        let icon = "fa-file";
        if (file.type.includes("image")) {
            icon = "fa-image";
        } else if (file.type.includes("pdf")) {
            icon = "fa-file-pdf";
        } else if (file.type.includes("csv") || file.type.includes("excel")) {
            icon = "fa-file-excel";
        } else if (file.type.includes("text")) {
            icon = "fa-file-alt";
        }
        
        // Create attachment content
        attachmentEl.innerHTML = `
            <i class="fa ${icon}"></i>
            <span>${file.name}</span>
            <button class="gemini-chat-attachment-remove" title="Remove">
                <i class="fa fa-times"></i>
            </button>
        `;
        
        // Add remove event listener
        attachmentEl.querySelector(".gemini-chat-attachment-remove").addEventListener("click", () => {
            this.removeFileAttachment(file, attachmentEl);
        });
        
        // Add to attachments container
        this.attachmentsContainer.appendChild(attachmentEl);
        
        // Add to file attachments array
        this.fileAttachments.push({
            file: file,
            element: attachmentEl
        });
    }
    
    removeFileAttachment(file, element) {
        // Remove from DOM
        element.remove();
        
        // Remove from array
        this.fileAttachments = this.fileAttachments.filter(attachment => {
            return attachment.file !== file;
        });
        
        // Hide container if no attachments
        if (this.fileAttachments.length === 0) {
            this.attachmentsContainer.classList.add("hidden");
        }
    }
    
    clearAttachments() {
        // Clear DOM
        this.attachmentsContainer.innerHTML = "";
        
        // Clear array
        this.fileAttachments = [];
        
        // Hide container
        this.attachmentsContainer.classList.add("hidden");
    }
    
    prepareFileAttachments() {
        if (this.fileAttachments.length === 0) return null;
        
        // For each file, we need to upload it to the server first
        const uploadPromises = this.fileAttachments.map(attachment => {
            return this.uploadFile(attachment.file);
        });
        
        // Return Promise that resolves with all file URLs
        return Promise.all(uploadPromises);
    }
    
    uploadFile(file) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("doctype", "Gemini Message");
            formData.append("fieldname", "attachment");
            formData.append("is_private", 0);
            
            fetch("/api/method/upload_file", {
                method: "POST",
                body: formData,
                headers: {
                    "X-Frappe-CSRF-Token": frappe.csrf_token
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    resolve({
                        file_url: data.message.file_url,
                        file_name: data.message.file_name
                    });
                } else {
                    reject(new Error("File upload failed"));
                }
            })
            .catch(error => {
                console.error("Error uploading file:", error);
                reject(error);
            });
        });
    }
    
    sendMessageToServer(message, files) {
        // Prepare request data
        const data = {
            message: message,
            conversation_id: this.conversationId,
            context: JSON.stringify(this.contextInfo)
        };
        
        // Add files if available
        if (files && files.length > 0) {
            data.files = JSON.stringify(files);
        }
        
        // Send request
        frappe.call({
            method: this.apiEndpoint,
            args: data,
            callback: (response) => {
                // Hide typing indicator
                this.hideTypingIndicator();
                
                if (response.message) {
                    // Handle successful response
                    this.handleServerResponse(response.message);
                } else {
                    // Handle error
                    this.handleServerError("No response from server");
                }
            },
            error: (error) => {
                // Hide typing indicator
                this.hideTypingIndicator();
                
                // Handle error
                this.handleServerError(error.message || "Error communicating with server");
            }
        });
    }
    
    handleServerResponse(response) {
        // Check for error
        if (response.error) {
            this.handleServerError(response.message || "Unknown error");
            return;
        }
        
        // Store conversation ID
        if (response.conversation_id) {
            this.conversationId = response.conversation_id;
        }
        
        // Add assistant message
        this.addMessage({
            id: response.message_id,
            role: "assistant",
            content: response.text,
            timestamp: new Date(),
            confidence: this.getConfidenceLevel(response)
        });
        
        // Handle function calls if any
        if (response.function_call) {
            this.handleFunctionCall(response.function_call, response.function_result);
        }
        
        // Handle citations if any
        if (response.citations && response.citations.length > 0) {
            this.handleCitations(response.citations);
        }
    }
    
    handleServerError(errorMessage) {
        // Create error message
        const errorEl = document.createElement("div");
        errorEl.className = "gemini-chat-error";
        errorEl.textContent = `Error: ${errorMessage}`;
        
        // Add to messages container
        this.messagesContainer.appendChild(errorEl);
        
        // Scroll to bottom
        this.scrollToBottom();
        
        // Log error
        console.error("Gemini chat error:", errorMessage);
    }
    
    getConfidenceLevel(response) {
        // This is a placeholder. In a real implementation, the confidence
        // would come from the response or be calculated based on various factors.
        if (response.confidence) {
            const confidence = parseFloat(response.confidence);
            if (confidence >= 0.8) return "high";
            if (confidence >= 0.5) return "medium";
            return "low";
        }
        
        return null;
    }
    
    handleFunctionCall(functionCall, functionResult) {
        // Add a message indicating the function call
        this.addMessage({
            role: "assistant",
            content: `I executed the function "${functionCall.name}" with the following parameters: ${JSON.stringify(functionCall.args)}`,
            timestamp: new Date()
        });
        
        // If there's a result, add it
        if (functionResult) {
            this.addMessage({
                role: "assistant",
                content: `Result: ${JSON.stringify(functionResult, null, 2)}`,
                timestamp: new Date()
            });
        }
    }
    
    handleCitations(citations) {
        // Add a message with citations
        let citationsText = "Sources:\n";
        
        citations.forEach((citation, index) => {
            citationsText += `${index + 1}. [${citation.title}](${citation.url})\n`;
        });
        
        this.addMessage({
            role: "assistant",
            content: citationsText,
            timestamp: new Date()
        });
    }
    
    provideFeedback(messageId, feedback) {
        if (!messageId) return;
        
        // Send feedback to server
        frappe.call({
            method: "/api/method/erpnext_gemini_integration.api.chat_api.record_feedback",
            args: {
                message_id: messageId,
                feedback: feedback
            },
            callback: (response) => {
                if (response.message && !response.message.error) {
                    // Show feedback confirmation
                    frappe.show_alert({
                        message: `Thank you for your feedback!`,
                        indicator: "green"
                    }, 3);
                } else {
                    // Show error
                    frappe.show_alert({
                        message: `Error recording feedback: ${response.message.message || "Unknown error"}`,
                        indicator: "red"
                    }, 3);
                }
            }
        });
    }
    
    detectActiveContext() {
        // Get current page info
        const currentPage = this.getCurrentPageInfo();
        
        if (!currentPage) return;
        
        // Store context info
        this.contextInfo = {
            page: currentPage
        };
        
        // If we're on a form page, add form context
        if (currentPage.doctype && currentPage.docname) {
            this.addFormContext(currentPage.doctype, currentPage.docname);
        }
    }
    
    getCurrentPageInfo() {
        // Check if we're in a form
        if (frappe.get_route_str().startsWith("Form/")) {
            const route = frappe.get_route();
            return {
                type: "form",
                doctype: route[1],
                docname: route[2]
            };
        }
        
        // Check if we're in a list
        if (frappe.get_route_str().startsWith("List/")) {
            const route = frappe.get_route();
            return {
                type: "list",
                doctype: route[1]
            };
        }
        
        // Check if we're in a report
        if (frappe.get_route_str().startsWith("Report/")) {
            const route = frappe.get_route();
            return {
                type: "report",
                report_name: route[1]
            };
        }
        
        // Default to current route
        return {
            type: "page",
            route: frappe.get_route_str()
        };
    }
    
    addFormContext(doctype, docname) {
        // Get form data
        frappe.model.with_doc(doctype, docname, () => {
            const doc = frappe.get_doc(doctype, docname);
            
            if (!doc) return;
            
            // Add doc data to context
            this.contextInfo.doc = {
                doctype: doctype,
                docname: docname,
                data: this.sanitizeDocData(doc)
            };
            
            // Update welcome message if needed
            if (this.messageHistory.length === 1 && this.messageHistory[0].role === "assistant") {
                const newWelcome = `Hello! I'm your Gemini Assistant. I see you're viewing the ${doctype} "${docname}". How can I help you with this?`;
                
                // Update the message in DOM
                const welcomeMsg = this.messagesContainer.querySelector(".gemini-chat-message.assistant .gemini-chat-message-content");
                if (welcomeMsg) {
                    welcomeMsg.innerHTML = newWelcome;
                }
                
                // Update in history
                this.messageHistory[0].content = newWelcome;
            }
        });
    }
    
    sanitizeDocData(doc) {
        // Create a sanitized copy with only safe fields
        const sanitized = {};
        
        // Skip standard private fields
        const privateFields = [
            "password",
            "pwd",
            "api_key",
            "api_secret",
            "secret",
            "token",
            "access_token",
            "refresh_token"
        ];
        
        // Copy fields
        for (const key in doc) {
            // Skip functions and private fields
            if (typeof doc[key] === "function" || key.startsWith("_") || privateFields.includes(key.toLowerCase())) {
                continue;
            }
            
            // Include the field
            sanitized[key] = doc[key];
        }
        
        return sanitized;
    }
    
    showNotification(count = 1) {
        const badge = this.toggleButton.querySelector(".gemini-notification-badge");
        badge.textContent = count;
        badge.classList.remove("hidden");
    }
};

// Initialize the chat widget when the page is ready
frappe.ready(function() {
    // Check if the widget should be initialized
    if (frappe.boot && frappe.boot.gemini_assistant_enabled) {
        // Initialize the widget
        window.geminiChatWidget = new erpnext_gemini_integration.chat_widget({
            container: document.body,
            position: "bottom-right",
            title: "Gemini Assistant",
            placeholder: "Ask me anything about ERPNext...",
            welcomeMessage: "Hello! I'm your Gemini Assistant. How can I help you today?"
        });
    }
});

