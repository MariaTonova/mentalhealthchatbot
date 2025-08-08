document.addEventListener("DOMContentLoaded", function () {
    const sendBtn = document.getElementById("sendBtn");
    const userInput = document.getElementById("userInput");
    const chatBox = document.getElementById("chatBox");

    function appendMessage(sender, text, mood = null) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", sender === "user" ? "user" : "bot");

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

        messageDiv.innerHTML = `<strong>${sender === "user" ? "You" : "CareBear"}:</strong> ${text} ${emoji}`;
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        appendMessage("user", message);
        userInput.value = "";

        const typingDiv = document.createElement("div");
        typingDiv.classList.add("message", "bot");
        typingDiv.innerHTML = `<em>CareBear is typing...</em>`;
        chatBox.appendChild(typingDiv);
        chatBox.scrollTop = chatBox.scrollHeight;

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
    }

    sendBtn.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") sendMessage();
    });
});
