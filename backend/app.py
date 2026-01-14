from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import os
from openai import AzureOpenAI

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

@app.route("/ai/ping", methods=["POST"])
def ai_ping():
    user_input = request.json.get("message", "")

    response = call_azure_openai(user_input)
    return jsonify(response)

def call_azure_openai(prompt):

    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    client = AzureOpenAI(
    api_version=os.getenv("API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "only respond to questions about cheese, do not answer any other questions. If the question is not about cheese, respond with 'I am sorry, I can only answer questions about cheese.'",
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=deployment
    )

    print(response.choices[0].message.content)


    return response.choices[0].message.content

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
