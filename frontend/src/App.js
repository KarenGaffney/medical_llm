import { useRef, useState } from "react";

function App() {
  const sessionIdRef = useRef(crypto.randomUUID());
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState([]); // {role, content}

  const sendMessage = async () => {
    const userMsg = { role: "user", content: message };
    setChat((prev) => [...prev, userMsg]);

    const res = await fetch("http://localhost:5000/ai/ping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionIdRef.current,
        message,
      }),
    });

    const data = await res.json();
    const assistantMsg = {
      role: "assistant",
      content: (data.assistant_message || JSON.stringify(data, null, 2)).replace(/\\n/g, "\n"),
    };

    setChat((prev) => [...prev, assistantMsg]);
    setMessage("");
  };

  return (
    <div style={{ padding: "2rem", maxWidth: 900, margin: "0 auto" }}>
      <h2>Doctor Scheduling Assistant (Prototype)</h2>

      <div style={{ margin: "1rem 0" }}>
        {chat.map((m, idx) => (
          <div key={idx} style={{ marginBottom: "0.75rem" }}>
            <strong>{m.role === "user" ? "Doctor" : "Assistant"}:</strong>
            <div style={{ whiteSpace: "pre-wrap", wordWrap: "break-word" }}>{m.content}</div>
          </div>
        ))}
      </div>

      <textarea
        rows="3"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder='Try: "Schedule Shelly tomorrow at 1pm" then "make it 45 minutes" then "yes"'
        style={{ width: "100%" }}
      />
      <button onClick={sendMessage} disabled={!message.trim()}>
        Send
      </button>
    </div>
  );
}

export default App;
