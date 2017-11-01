from flask import Flask, render_template
from flask import request
app = Flask(__name__)


@app.route("/api/upload_image", methods=['POST', 'GET'])
def api_upload_image():
    if request.method == 'POST':
        f = request.files['file']
        return str(f.read())
    else:
        return render_template('upload_test.html')

