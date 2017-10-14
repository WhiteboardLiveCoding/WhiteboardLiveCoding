import numpy as np
import pickle

from os import environ
from os.path import dirname, join
from keras.models import model_from_yaml
from WLC.utils.singleton import Singleton

# Mute tensorflow debugging information on console
environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


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
        x = np.invert(char);
        x = x.reshape(1, 28, 28, 1)

        x = x.astype('float32')

        # Normalize to prevent issues with model
        x /= 255

        out = self.model.predict(x)

        response = chr(self.mapping[(int(np.argmax(out, axis=1)[0]))])

        return response