document.getElementById("send-button").addEventListener("click", sendMessage);
document.getElementById("user-input").addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
});

function appendMessage(content, sender) {
    const msgContainer = document.createElement("div");
    msgContainer.classList.add("message", sender === "user" ? "user-message" : "bot-message");
    msgContainer.textContent = content;
    document.getElementById("chatbot-messages").appendChild(msgContainer);
    document.getElementById("chatbot-messages").scrollTop =
        document.getElementById("chatbot-messages").scrollHeight;
}

async function sendMessage() {
    const inputField = document.getElementById("user-input");
    const userText = inputField.value.trim();
    if (!userText) return;

    // Add user message
    appendMessage(userText, "user");
    inputField.value = "";

    // Show typing placeholder
    const typingMsg = document.createElement("div");
    typingMsg.classList.add("message", "bot-message");
    typingMsg.textContent = "CareBear is thinking...";
    document.getElementById("chatbot-messages").appendChild(typingMsg);

    try {
        // Call your Flask backend instead of OpenAI directly
        const res = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userText })
        });

        const data = await res.json();
        typingMsg.remove();

        // Show bot response + mood emoji if available
        let botText = data.response;
        if (data.mood) {
            const moodEmojis = {
                happy: "😊",
                sad: "😔",
                angry: "😠",
                neutral: "😐",
                anxious: "😰"
            };
            botText += ` ${moodEmojis[data.mood] || ""}`;
        }
        appendMessage(botText, "bot");

    } catch (err) {
        typingMsg.remove();
        appendMessage("Sorry, I’m having trouble connecting right now.", "bot");
        console.error(err);
    }
}

