import os
import sys
from flask import Flask, jsonify

# ---- REQUIRED ENV VARIABLES ----
REQUIRED_VARS = ["APP_NAME", "ENVIRONMENT", "SECRET_KEY"]

missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
if missing:
    print(f"Missing required environment variables: {missing}", file=sys.stderr)
    sys.exit(1)

APP_NAME = os.getenv("APP_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")

app = Flask(__name__)

@app.route("/")
def home():
    return f"{APP_NAME} running in {ENVIRONMENT}\n"

@app.route("/health")
def health():
    return jsonify(status="ok")

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False
    )
