function sendMessage() {
  const input = document.getElementById('user-input');
  const chatBox = document.getElementById('chat-box');
  const userText = input.value.trim();
  if (userText) {
    const userMsg = document.createElement('div');
    userMsg.className = 'message user-message';
    userMsg.textContent = userText;
    chatBox.appendChild(userMsg);

    fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText })
    })
    .then(res => res.json())
    .then(data => {
      const botMsg = document.createElement('div');
      botMsg.className = 'message bot-message';
      botMsg.textContent = data.response;
      chatBox.appendChild(botMsg);
      chatBox.scrollTop = chatBox.scrollHeight;
    });

    input.value = '';
  }
}
