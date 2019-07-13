#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
from future.standard_library import install_aliases
from flask import Flask, request, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from data import DATA_PATH
from model import emotion_model as emotion_model
import model
import json
import os
import time
import shutil
from scipy import misc
import random
import requests
import string
import numpy as np
from PIL import Image

from push_notification import PushNotification

IMAGE_PREDICT = "image_predict"

install_aliases()
app = Flask(__name__)
cors = CORS(app)

pusher = None
current_milli_time = lambda: int(round(time.time() * 1000))

happy_messages = ["Hôm nay trông cụ vui thế ạ, cụ muốn nghe nhạc không ạ",
                  "Hôm nay trông yêu đời thế ạ, cụ muốn nghe nhạc không ạ",
                  "Cụ hôm nay thần thái tốt vậy, cụ muốn nghe một bài hát không ạ"]

sad_messages = ["Cụ hôm nay có gì không vui ạ. Cháu gọi con trai cụ nhé",
                  "Hôm nay cụ buồn vậy. Cháu gọi cho con trai cụ nha",
                  "Cháu gọi cho cháu trai cụ nhé"]

happy_responses = [{"url":0, "content" : "vâng ạ"},
                  {"url":1, "content" : "Dạ"},
                  {"url":2, "content" : "Dạ chúc cụ một ngày vui vẻ"}]

sad_responses = [{"url":0, "content" : "Vâng cháu gọi luôn ạ"},
                  {"url":1, "content" : "Dạ, cháu gọi đây ạ"},
                  {"url":2, "content" : "Vâng cháu gọi đây"}]

current_session = ""
last_time = 0

@app.route('/api/detect', methods=['POST'])
def detect():
    global current_session, last_time
    duration = time.time() - last_time
    if current_session != '' and duration < 15:
        response = generate_response(1002, 'Processing', '')
        return response

    current_session = random_string(10)
    last_time = time.time()

    file_predict = request.files[IMAGE_PREDICT]
    mime_type = file_predict.content_type
    if mime_type not in ['image/png', 'image/jpg', 'image/jpeg']:
        response = generate_response(1001, 'Image have to png or jpg format')
        return response

    file_name = generate_name(secure_filename(file_predict.filename))
    file_predict_path = os.path.join(DATA_PATH, file_name)
    file_predict.save(file_predict_path)
    #image = misc.imread(image = Image.open(image_stream))/255.
    #Image.open(image_stream)image = Image.open(image_stream)
    image = np.array(Image.open(file_predict_path)).astype(float)/255.
    image = 0.2126 * image[:,:,0] + 0.7152 * image[:,:,1] + 0.0722 * image[:,:,2]
    image =image.astype('float')
    start_time = time.time()
    # global detector
    results = emotion_model.predict_([image])
    if results[0] == 'happy':
        mesage = random.choice(happy_messages)
    elif results[0] == 'sad' or results[0] == 'angry':
        mesage = random.choice(sad_messages)
    else:
        mesage = 'Cháu thấy lạ ghê ạ'

    mesage = {"emotion": results[0], "message":mesage}
    send_sync_push("Thread-1", mesage)
    response = generate_response(0, '', results)
    os.remove(file_predict_path)
    return response


@app.route('/api/answer', methods=['POST'])
def answer():
    req = request.get_json(silent=True, force=True)
    emotion = req['emotion']
    message = req['message']
    data = send_request_nlp(message)
    if data['code'] == 0 and emotion == 'happy':
        result = random.choice(happy_responses)
        code = 0
        message = ''
    elif data['code'] == 0 and (emotion == 'sad' or emotion == 'angry'):
        result = random.choice(sad_responses)
        code = 0
        message = ''
    else:
        code = -1
        result = {"url":-1, "content" : "Error"}
        message = 'Bà ơi cháu mới học chưa biết nhiều đâu'

    response = generate_response(code, message, result)
    global current_session
    current_session = ""
    return response

def generate_response(code=0, message='', data=None):
    response = {'code': code, 'message': message, 'data': data}
    res = json.dumps(response)
    response = make_response(res)
    response.headers['Content-Type'] = 'application/json'
    return response


def generate_name(suffix):
    timestamp = current_milli_time()
    return "{}_{}".format(timestamp, suffix)


def remove_file(file_path):
    print("Deleting " + file_path + " Removed!")
    os.remove(file_path)
    print(file_path + " Removed!")


def move_file(source_folder, destination_folder):
    files = os.listdir(source_folder)
    for _file in files:
        file_path = "{}/{}".format(source_folder, _file)
        shutil.move(file_path, destination_folder)


def send_sync_push(threadName, message):
    global pusher
    pusher.push_to_client(message)

def random_string(stringLength=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

def send_request_nlp(message):
    URL = "https://10bot.vn/api/ask"
    DATA = {'question':message, "chat_session_id" : ""}
    HEADERS = {'Content-Type': 'application/json', 'ZBOT-AUTHORIZATION-KEY': 'bkNVUzV0azlYTDB4cWxkRE0zTnViR0VvRnpWY2U0STY='}
    response = requests.post(URL, data = json.dumps(DATA), headers = HEADERS)
    data = response.json()
    print(data)
    return data

if __name__ == '__main__':
    global pusher
    pusher = PushNotification()
    print("Starting app on port 3689")
    app.run(threaded=True, debug=False, port=3689,host = '0.0.0.0')
