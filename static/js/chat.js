document.getElementById("send-btn").addEventListener("click", sendMessage);
document.getElementById("user-input").addEventListener("keypress", function(e) {
    if (e.key === "Enter") sendMessage();
});

function appendMessage(text, sender, mood = null) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message");

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

    msgDiv.innerHTML = `${text} ${emoji}`;
    document.getElementById("chat-messages").appendChild(msgDiv);
    document.getElementById("chat-messages").scrollTop = document.getElementById("chat-messages").scrollHeight;
}

function sendMessage() {
    const inputField = document.getElementById("user-input");
    const message = inputField.value.trim();
    if (!message) return;

    appendMessage(message, "user");
    inputField.value = "";

    const typingDiv = document.createElement("div");
    typingDiv.classList.add("message", "bot-message");
    typingDiv.innerHTML = `<em>CareBear is typing...</em>`;
    document.getElementById("chat-messages").appendChild(typingDiv);

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("chat-messages").removeChild(typingDiv);
        appendMessage(data.response, "bot", data.mood);
    })
    .catch(() => {
        document.getElementById("chat-messages").removeChild(typingDiv);
        appendMessage("Sorry, something went wrong.", "bot");
    });
}

