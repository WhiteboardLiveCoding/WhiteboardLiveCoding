import pickle
from os import environ
from os.path import dirname, join

import numpy as np
from keras.models import model_from_yaml

from ..utils.singleton import Singleton

# Mute tensorflow debugging information on console
environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

MINIMUM_PROBABILITY = 0.01


class OCR(metaclass=Singleton):

    def __init__(self):
        self._load_model()
        self._load_mapping()

    def _load_model(self):
        yaml_path = join(dirname(__file__), 'model/model.yaml')
        h5_path = join(dirname(__file__), 'model/model.h5')

        yaml_file = open(yaml_path, 'r')
        loaded_model_yaml = yaml_file.read()
        yaml_file.close()

        model = model_from_yaml(loaded_model_yaml)
        model.load_weights(h5_path)

        self.model = model

    def _load_mapping(self):
        mapping_path = join(dirname(__file__), 'model/mapping.p')
        self.mapping = pickle.load(open(mapping_path, 'rb'))

    def predict(self, char):
        char = char.reshape(1, 28, 28, 1)

        char = char.astype('float32')

        char /= 255

        prediction = self.model.predict(char)
        sorted_preds = np.argsort(prediction, axis=1)[0]

        res = [(chr(self.mapping[(int(elem))]), prediction[0][elem]) for elem in sorted_preds][::-1]
        return res[0][0], self.reduce_line(res)

    def reduce_line(self, possibilities):
        lowered = map(lambda p: (p[0].lower(), p[1]), possibilities)
        filtered = list(map(lambda c: c[0], filter(lambda c: c[1] > MINIMUM_PROBABILITY, lowered)))
        return self.remove_duplicate_predictions(filtered)

    def remove_duplicate_predictions(self, seq):
        seen = set()
        seen_add = seen.add
        return [x for x in seq if not (x in seen or seen_add(x))]
