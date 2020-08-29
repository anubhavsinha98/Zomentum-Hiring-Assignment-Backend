from flask import Flask

app = Flask(__name__)

@app.route('/abc')
def hello_world():
    return 'Hello World'
