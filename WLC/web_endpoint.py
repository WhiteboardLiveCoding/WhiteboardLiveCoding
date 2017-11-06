import json

import numpy as np
from cv2 import cv2, IMREAD_COLOR

from flask import Flask, render_template
from flask import request

from .code_executor.executor import CodeExecutor
from .image_processing.picture import Picture
from .utils.azure import save_image_to_azure, save_code_to_azure

app = Flask(__name__)


@app.route("/")
def index():
    return "Nothing to see here, this is just the API."


@app.route("/api/upload_image", methods=['POST', 'GET'])
def api_upload_image():
    if request.method == 'POST':
        file = request.files['file']
        img_array = np.asarray(bytearray(file.read()), dtype=np.uint8)
        img = cv2.imdecode(img_array, IMREAD_COLOR)

        height, width, _ = img.shape
        pic = Picture(img, 0, 0, width, height, None)
        saved, key = save_image_to_azure('pictures', pic.get_image())

        if not saved:
            key = None

        code, fixed_code, result, error = CodeExecutor().execute_code_img(pic)

        return json.dumps(['unfixed', code, 'fixed', fixed_code, 'result', str(result), 'error', str(error), 'key', key])
    else:
        return render_template('upload_test.html')


@app.route("/api/resubmit_code", methods=['POST', 'GET'])
def api_resubmit_code():
    if request.method == 'POST':
        code = request.form['code']
        result, error = CodeExecutor().execute_code(code)

        if request.json.get('key'):
            save_code_to_azure('code', 'pictures', request.json.get('key'), code)

        return json.dumps(['result', str(result), 'error', str(error)])
    else:
        return render_template('resubmit_test.html')


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=80)
