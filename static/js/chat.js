document.addEventListener("DOMContentLoaded", function () {
    const sendBtn = document.getElementById("sendBtn");
    const userInput = document.getElementById("userInput");
    const chatBox = document.getElementById("chatBox");

    function appendMessage(sender, text, mood = null) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", sender === "user" ? "user" : "bot", "fade-in");

        let emoji = "";
        if (mood) {
            const moodEmojis = {
                happy: "😊",
                sad: "😔",
                angry: "😠",
                neutral: "😐",
                anxious: "😰"
            };
            emoji = moodEmojis[mood] || "";
        }

        messageDiv.innerHTML = `<span class="sender">${sender === "user" ? "You" : "CareBear"}:</span> ${text} ${emoji}`;
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function showTyping() {
        const typingDiv = document.createElement("div");
        typingDiv.classList.add("message", "bot", "typing");
        typingDiv.innerHTML = `<span class="dots"></span>`;
        chatBox.appendChild(typingDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
        return typingDiv;
    }

    sendBtn.addEventListener("click", function () {
        const message = userInput.value.trim();
        if (!message) return;

        appendMessage("user", message);
        userInput.value = "";

        const typingDiv = showTyping();

        fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            chatBox.removeChild(typingDiv);
            appendMessage("bot", data.response, data.mood);
        });
    });
});
