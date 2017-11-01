import json

import numpy as np
from cv2 import cv2, IMREAD_COLOR

from flask import Flask, render_template
from flask import request

from WLC.code_executor.executor import CodeExecutor
from WLC.image_processing.picture import Picture

app = Flask(__name__)


@app.route("/api/upload_image", methods=['POST', 'GET'])
def api_upload_image():
    if request.method == 'POST':
        file = request.files['file']
        img_array = np.asarray(bytearray(file.read()), dtype=np.uint8)
        img = cv2.imdecode(img_array, IMREAD_COLOR)

        height, width, _ = img.shape
        pic = Picture(img, 0, 0, width, height, None)

        code, fixed_code, result, error = CodeExecutor().execute_code(pic)

        return json.dumps(['unfixed', code, 'fixed', fixed_code, 'result', str(result), 'error', str(error)])
    else:
        return render_template('upload_test.html')
