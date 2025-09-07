document.getElementById("send-btn").addEventListener("click", sendMessage);
document.getElementById("user-input").addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
});

const inputField = document.getElementById("user-input");
const chatBox = document.getElementById("chat-messages");

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
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showTypingAnimation() {
    const typingDiv = document.createElement("div");
    typingDiv.classList.add("message", "bot-message", "fade-in");
    typingDiv.setAttribute("id", "typing");

    typingDiv.innerHTML = `<span class="dots">
        <span>.</span><span>.</span><span>.</span>
    </span>`;

    chatBox.appendChild(typingDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeTypingAnimation() {
    const typingDiv = document.getElementById("typing");
    if (typingDiv) typingDiv.remove();
}

function sendMessage() {
    const message = inputField.value.trim();
    if (!message) return;

    appendMessage(message, "user");
    inputField.value = "";
    inputField.disabled = true;
    document.getElementById("send-btn").disabled = true;

    showTypingAnimation();

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
    })
    .then(async (res) => {
        if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
        }
        return res.json();
    })
    .then(data => {
        const baseDelay = 800;
        const extraDelay = Math.min(data.response.length * 20, 2200);
        const totalDelay = baseDelay + extraDelay;

        setTimeout(() => {
            removeTypingAnimation();
            appendMessage(data.response, "bot", data.mood);
            inputField.disabled = false;
            document.getElementById("send-btn").disabled = false;
            inputField.focus();
        }, totalDelay);
    })
    .catch(err => {
        console.error("Chat fetch error:", err);
        removeTypingAnimation();
        appendMessage("⚠️ Sorry, I couldn’t process that. Let’s try again 💛", "bot");
        inputField.disabled = false;
        document.getElementById("send-btn").disabled = false;
    });
}

// ---------------- Summary Button ----------------
document.getElementById("summary-btn").addEventListener("click", () => {
    showTypingAnimation();

    fetch("/session-summary")
        .then(res => res.json())
        .then(data => {
            removeTypingAnimation();
            appendMessage(data.response, "bot", data.mood);
        })
        .catch(() => {
            removeTypingAnimation();
            appendMessage("⚠️ Sorry, I couldn’t fetch the summary right now.", "bot");
        });
});
