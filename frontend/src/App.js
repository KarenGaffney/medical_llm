import { useState } from "react";

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]); 
  

  const sendMessage = async () => {
    const newMessages = [...messages, { role: "user", content: message }];
    const trimmed = newMessages.slice(-12); //trim messages to last 12 to keep memory use manageable

    const res = await fetch("http://localhost:5000/ai/ping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: trimmed })  
    });

    const data = await res.json();

    const assistantText =
      (data.assistant_message || "").replace(/\\n/g, "\n");

    const updated = [
      ...newMessages,
      { role: "assistant", content: assistantText }
    ];

    setMessages(updated);
    setMessage("");
  };

  return (
    <div style={{ padding: "2rem", maxWidth: 800, margin: "0 auto" }}>
      <h2>Doctor Scheduling Assistant (Prototype)</h2>

      <div style={{ marginTop: "1rem" }}>
        {messages.map((m, idx) => (
          <div key={idx} style={{ marginBottom: "0.75rem" }}>
            <strong>{m.role === "user" ? "Doctor" : "Assistant"}:</strong>
            <div style={{ whiteSpace: "pre-wrap", wordWrap: "break-word" }}>
              {m.content}
            </div>
          </div>
        ))}
      </div>

      <textarea
        rows="3"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder='Try: "Schedule Shelly tomorrow at 1pm" then "make it 45 minutes"'
        style={{ width: "100%", marginTop: "1rem" }}
      />

      <button onClick={sendMessage} disabled={!message.trim()}>
        Send
      </button>
    </div>
  );
}

export default App;
