from flask import Flask
from threading import Thread


app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Web Server!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run_server)
    thread.start()
    print("Web server is running in the background...")