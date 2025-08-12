document.getElementById("send-btn").addEventListener("click", sendMessage);
document.getElementById("user-input").addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
});

function appendMessage(text, sender, mood = null) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message", "fade-in");

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

    // Smooth scroll to bottom
    document.getElementById("chat-messages").scrollTop = document.getElementById("chat-messages").scrollHeight;
}

function sendMessage() {
    const inputField = document.getElementById("user-input");
    const message = inputField.value.trim();
    if (!message) return;

    appendMessage(message, "user");
    inputField.value = "";

    // Typing simulation
    const typingDiv = document.createElement("div");
    typingDiv.classList.add("message", "bot-message", "fade-in");
    typingDiv.setAttribute("id", "typing");
    typingDiv.innerHTML = "CareBear is typing...";
    document.getElementById("chat-messages").appendChild(typingDiv);
    document.getElementById("chat-messages").scrollTop = document.getElementById("chat-messages").scrollHeight;

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
    })
    .then(res => res.json())
    .then(data => {
        // Adjust delay based on response length (min 0.8s, max 3s)
        const baseDelay = 800;
        const extraDelay = Math.min(data.response.length * 20, 2200); 
        const totalDelay = baseDelay + extraDelay;

        setTimeout(() => {
            document.getElementById("typing").remove();
            appendMessage(data.response, "bot", data.mood);
        }, totalDelay);
    })
    .catch(() => {
        document.getElementById("typing").remove();
        appendMessage("Sorry, something went wrong.", "bot");
    });
}
