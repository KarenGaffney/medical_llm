import { useState } from "react";


function App() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState("");

  const sendMessage = async () => {
    const res = await fetch("http://localhost:5000/ai/ping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    const data = await res.json();
    const content =
    data.choices?.[0]?.message?.content || JSON.stringify(data);

    setResponse(content.replace(/\\n/g, "\n"));

    // setResponse(
    //   data.choices?.[0]?.message?.content || JSON.stringify(data)
    // );
  };

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Doctor Scheduling Assistant (Prototype)</h2>

      <textarea
        rows="4"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Schedule an appointment for Shelly next Friday at 1pm"
        style={{ width: "100%" }}
      />

      <button onClick={sendMessage}>Send</button>

      <pre
        style={{
          whiteSpace: "pre-wrap",
          wordWrap: "break-word",
          background: "#f5f5f5",
          padding: "1rem",
          borderRadius: "6px",
          marginTop: "1rem",
        }}
      >
        {response}
      </pre>

    </div>
  );
}

export default App;
