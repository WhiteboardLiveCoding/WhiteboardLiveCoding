import json
from urllib.request import urlopen

import numpy as np
import sys
from cv2 import cv2, IMREAD_COLOR

from flask import Flask, render_template
from flask import request
from image_segmentation.picture import Picture
from image_segmentation.preprocessor import Preprocessor

from .code_executor.executor import CodeExecutor
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

        code, fixed_code, result, error = CodeExecutor().execute_code_img(pic)
        ar = _get_ar_coordinates(pic, error)

        response = {'unfixed': code, 'fixed': fixed_code, 'result': str(result), 'error': str(error), 'key': key, 'ar': ar}

        return json.dumps(response)
    else:
        return render_template('upload_test.html')


@app.route("/api/resubmit_code", methods=['POST', 'GET'])
def api_resubmit_code():
    if request.method == 'POST':
        code = request.json.get('code')
        result, error = CodeExecutor().execute_code(code)

        key = request.json.get('key')
        image = _url_to_image('https://alpstore.blob.core.windows.net/pictures/{}'.format(key))
        height, width, _ = image.shape
        pic = Picture(image, 0, 0, width, height)
        pic = Preprocessor().process(pic)
        pic.get_segments()
        ar = _get_ar_coordinates(pic, error)

        save_code_to_azure('code', 'pictures', key, code)

        return json.dumps({'result': str(result), 'error': str(error), 'ar': ar, 'key': key})
    else:
        return render_template('resubmit_test.html')


def _get_ar_coordinates(pic, error):

    # calculate mins, maxs
    min_x = min_y = sys.maxsize
    max_x = max_y = 0

    i = 1
    line = pic.get_line_coordinates(i)
    while line:
        if line['x'] < min_x:
            min_x = line['x']

        if line['y'] < min_y:
            min_y = line['y']

        if (line['x'] + line['width']) > max_x:
            max_x = line['x'] + line['width']

        if (line['y'] + line['height']) > max_y:
            max_y = line['y'] + line['height']

        line = pic.get_line_coordinates(i)
        i = i + 1

    return {
        'dimensions': {'width': pic.get_width(), 'height': pic.get_height()},
        'line': pic.get_line_coordinates(error.get_line()),
        'character': pic.get_character_coordinates(error.get_line(), error.get_column()),
        'bbox': {'min_x': min_x, 'min_y': min_y, 'max_x': max_x, 'max_y': max_y}
    }


def _url_to_image(url):
    resp = urlopen(url)
    image = np.asarray(bytearray(resp.read()), dtype="uint8")
    return cv2.imdecode(image, cv2.IMREAD_COLOR)


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=80)
