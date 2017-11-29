import json
import os
from urllib.request import urlopen

import numpy as np
import sys
from cv2 import cv2, IMREAD_COLOR

from flask import Flask, render_template
from flask import request
from image_segmentation.picture import Picture
from image_segmentation.preprocessor import Preprocessor

from .code_executor.code_executor import CodeExecutor
from .utils.azure import WLCAzure

app = Flask(__name__)


@app.route("/")
def index():
    build_id = os.environ['BUILD_NUM'] if 'BUILD_NUM' in os.environ else 'local'
    return "Nothing to see here, this is just the API. Circle build id: {}.".format(build_id)


@app.route("/api/upload_image", methods=['POST', 'GET'])
def api_upload_image():
    if request.method == 'POST':
        file = request.files['file']
        img_array = np.asarray(bytearray(file.read()), dtype=np.uint8)
        img = cv2.imdecode(img_array, IMREAD_COLOR)

        height, width, _ = img.shape
        pic = Picture(img, 0, 0, width, height, None)

        azure = WLCAzure()
        saved, key = azure.save_image_to_azure('pictures', pic.get_image())

        executor = get_executor(request)
        code, fixed_code, result, errors = executor.execute_code_img(pic)

        if 'test_key' in request.args:
            test_results = executor.execute_tests(code, request.args.get('test_key'))
        else:
            test_results = []

        ar = _get_ar_coordinates(pic, errors)

        response = {'unfixed': code, 'fixed': fixed_code, 'result': str(result), 'errors': errors, 'key': key,
                    'ar': ar, 'test_results': test_results}

        return json.dumps(response)
    else:
        return render_template('upload_test.html')


@app.route("/api/resubmit_code", methods=['POST', 'GET'])
def api_resubmit_code():
    if request.method == 'POST':
        code = request.json.get('code')
        executor = get_executor(request)
        result, errors = executor.execute_code(code)

        if 'test_key' in request.args:
            test_results = executor.execute_tests(code, request.args.get('test_key'))
        else:
            test_results = []

        key = request.json.get('key')
        image = _url_to_image('https://alpstore.blob.core.windows.net/pictures/{}'.format(key))
        height, width, _ = image.shape
        pic = Picture(image, 0, 0, width, height)
        pic = Preprocessor().process(pic)
        pic.get_segments()
        ar = _get_ar_coordinates(pic, errors)

        azure = WLCAzure()
        azure.save_code_to_azure('code', 'pictures', key, code)

        return json.dumps({'result': str(result), 'errors': errors, 'ar': ar, 'key': key,
                           'test_results': test_results})
    else:
        return render_template('resubmit_test.html')


@app.route("/api/template", methods=['POST'])
def api_resubmit_code():
    if request.method == 'POST':
        template_file = request.files.get('templateFile')
        test_file = request.files.get('templateFile')

        if not template_file or not test_file:
            return json.dumps({'id': '', 'error': 'Files Missing', 'success': False})

        azure = WLCAzure()
        key, err = azure.save_template_and_test('template', template_file, test_file)

        if err == 1:
            return json.dumps({'id': '', 'error': 'Template already exists', 'success': False})
        elif err == 2:
            return json.dumps({'id': '', 'error': 'File Upload Failed', 'success': False})

        return json.dumps({'id': str(key), 'error': '', 'success': True})


def _get_ar_coordinates(pic, errors):
    # calculate mins, maxs
    min_x = min_y = sys.maxsize
    max_x = max_y = 0

    i = 1
    line = pic.get_line_coordinates(i)
    while line:
        min_x = min(min_x, line['x']);
        min_y = min(min_y, line['y']);
        max_x = max(max_x, line['x'] + line['width']);
        max_y = max(max_y, line['y'] + line['height']);

        line = pic.get_line_coordinates(i)
        i = i + 1  
      
    ar_coords = {
        'dimensions': {'width': pic.get_width(), 'height': pic.get_height()},
        'bbox': {'min_x': min_x, 'min_y': min_y, 'max_x': max_x, 'max_y': max_y},
        'errors': [],
    }

    for error in errors:
        ar_coords['errors'].append(
            {
                'line': pic.get_line_coordinates(error['line']),
                'character': pic.get_character_coordinates(error['line'], error['column']-1)
            })

    return ar_coords


def _url_to_image(url):
    resp = urlopen(url)
    image = np.asarray(bytearray(resp.read()), dtype="uint8")
    return cv2.imdecode(image, cv2.IMREAD_COLOR)


def get_executor(request):
    if 'language' in request.args:
        return CodeExecutor(request.args.get('language'))
    else:
        return CodeExecutor()


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=80)
