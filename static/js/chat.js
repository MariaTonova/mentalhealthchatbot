body {
    font-family: Arial, sans-serif;
    background: linear-gradient(to bottom right, rgba(255, 182, 193, 0.8), rgba(173, 216, 230, 0.8));
    height: 100vh;
    margin: 0;
    display: flex;
    justify-content: center;
    align-items: center;
}

.chat-container {
    width: 400px;
    background: white;
    border-radius: 20px;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.2);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.chat-header {
    display: flex;
    align-items: center;
    padding: 10px;
    background: rgba(255, 192, 203, 0.9);
    border-bottom: 2px solid #f0f0f0;
}

.bear-icon {
    width: 50px;
    height: 50px;
    margin-right: 10px;
}

.chat-messages {
    flex: 1;
    padding: 10px;
    overflow-y: auto;
    background: rgba(255, 255, 255, 0.7);
}

.message {
    padding: 8px 12px;
    border-radius: 15px;
    margin-bottom: 8px;
    max-width: 80%;
}

.user-message {
    background: rgba(173, 216, 230, 0.6);
    align-self: flex-end;
}

.bot-message {
    background: rgba(255, 182, 193, 0.6);
    align-self: flex-start;
}

.chat-input {
    display: flex;
    padding: 10px;
    border-top: 2px solid #f0f0f0;
}

#user-input {
    flex: 1;
    padding: 8px;
    border: 1px solid #ccc;
    border-radius: 15px;
    outline: none;
}

.paw-btn {
    background: transparent;
    border: none;
    margin-left: 8px;
    cursor: pointer;
}

.paw-icon {
    width: 32px;
    height: 32px;
}
