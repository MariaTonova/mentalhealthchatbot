document.getElementById("send-button").addEventListener("click", sendMessage);
document.getElementById("user-input").addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
});

function appendMessage(text, sender, mood = null) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message");

    // Mood emoji mapping
    const moodEmojis = {
        happy: "😊",
        sad: "😔",
        angry: "😠",
        neutral: "😐",
        anxious: "😰"
    };
    const emoji = mood && moodEmojis[mood] ? ` ${moodEmojis[mood]}` : "";

    msgDiv.innerHTML = `${text}${emoji}`;
    document.getElementById("chatbot-messages").appendChild(msgDiv);
    document.getElementById("chatbot-messages").scrollTop = document.getElementById("chatbot-messages").scrollHeight;
}

async function sendMessage() {
    const inputField = document.getElementById("user-input");
    const message = inputField.value.trim();
    if (!message) return;

    appendMessage(message, "user");
    inputField.value = "";

    // Typing placeholder
    const typingDiv = document.createElement("div");
    typingDiv.classList.add("message", "bot-message");
    typingDiv.textContent = "CareBear is thinking...";
    document.getElementById("chatbot-messages").appendChild(typingDiv);

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });

        const data = await res.json();

        // Remove typing indicator
        typingDiv.remove();

        appendMessage(data.response, "bot", data.mood);
    } catch (error) {
        typingDiv.remove();
        appendMessage("Sorry, something went wrong.", "bot");
        console.error(error);
    }
}
