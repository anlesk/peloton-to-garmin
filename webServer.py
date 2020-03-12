import os
import importlib  

from flask import Flask
from flask import request

ptg = importlib.import_module("peloton-to-garmin")

app = Flask(__name__)

@app.route('/')
def hello_world():
    target = os.environ.get('TARGET', 'World')
    return 'Hello {}!\n'.format(target)

@app.route('/peloton', methods = ['POST'])
def runExport():
    email = request.form.get('email')
    password = request.form.get('password')
    ptg.getWorkouts(email, password);
    return 'success';

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8080)))