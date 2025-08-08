document.getElementById("send-button").addEventListener("click", sendMessage);
document.getElementById("user-input").addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
});

function appendMessage(content, sender) {
    const msgContainer = document.createElement("div");
    msgContainer.classList.add("message", sender === "user" ? "user-message" : "bot-message");
    msgContainer.textContent = content;
    document.getElementById("chatbot-messages").appendChild(msgContainer);
    document.getElementById("chatbot-messages").scrollTop = document.getElementById("chatbot-messages").scrollHeight;
}

async function sendMessage() {
    const inputField = document.getElementById("user-input");
    const userText = inputField.value.trim();
    if (!userText) return;

    appendMessage(userText, "user");
    inputField.value = "";

    // Show typing placeholder
    const typingMsg = document.createElement("div");
    typingMsg.classList.add("message", "bot-message");
    typingMsg.textContent = "CareBear is thinking...";
    document.getElementById("chatbot-messages").appendChild(typingMsg);

    // GPT-3.5 API call (replace YOUR_API_KEY)
    try {
        const res = await fetch("https://api.openai.com/v1/chat/completions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer YOUR_API_KEY`
            },
            body: JSON.stringify({
                model: "gpt-3.5-turbo",
                messages: [{ role: "system", content: "You are a supportive mental health assistant." }, { role: "user", content: userText }]
            })
        });

        const data = await res.json();
        typingMsg.remove();
        appendMessage(data.choices[0].message.content.trim(), "bot");

    } catch (err) {
        typingMsg.remove();
        appendMessage("Sorry, I’m having trouble connecting right now.", "bot");
        console.error(err);
    }
}
