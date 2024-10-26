from flask import Flask, request, Response, render_template, jsonify
from flask_cors import CORS
import tensorflow as tf
import numpy as np
from tensorflow import keras
import pickle
from embedding import to_index_array, padding, decompose_string

app = Flask(__name__)
CORS(app)

MAX_LEN = 681

graph = None
sess = None
with open('jamo.pydict', 'rb') as f:
    jamodict = pickle.load(f)


def load_model():
    global graph
    global sess
    # TensorFlow 1.x에서는 session과 graph를 명시적으로 관리해야 함
    sess = tf.Session()
    graph = tf.get_default_graph()
    with sess.as_default():
        with graph.as_default():
            model = tf.keras.models.load_model('models/latest-yok-detect-model.h5')
    return model

model = load_model()

import re

# HTML 태그와 링크 제거 함수 추가
def clean_text(text):
    # HTML 태그 제거
    clean_html = re.compile('<.*?>')
    text = re.sub(clean_html, '', text)
    
    # 링크 형식 텍스트 제거 (http:// 또는 https:// 로 시작하는 텍스트 제거)
    text = re.sub(r'http\S+|www.\S+', '', text)
    
    return text

def encode_review(text):
    # HTML 태그와 링크 제거
    text = clean_text(text)
    text = decompose_string(text)
    text = to_index_array(text, jamodict)
    text = padding(text, MAX_LEN)
    return text
def predict(text):
    global model
    global graph
    global sess
    with graph.as_default():
        with sess.as_default():
            indices = encode_review(text)
            print(text)
            indices = np.array([indices])
            predictions = model.predict(indices)
            print(predictions)
            # 가장 높은 확률을 가진 클래스를 선택
            predicted_class = model.predict_classes(indices)
            print(predicted_class)
            if predicted_class == 0:
                return '욕아님'
            else:
                return '욕'

@app.route('/chk', methods=['POST'])
def upload_train():
    data = request.get_json()
    s = data['text'].split()
    answer = []
    for element in s:
        poornag = predict(element)
        if poornag == '욕':
            answer.append(element)
            print(element)
        else:
            answer.append("욕아님")
    print(answer)
    response = Response()
    response.headers[
        'Access-Control-Allow-Headers'] = 'Access-Control-Allow-Headers, Origin, X-Requested-With, Content-Type, Accept, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD'
    return answer

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0', debug=True, threaded=True)