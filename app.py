#!/usr/bin/env python
from importlib import import_module
import os
import cv2 as cv
from flask import Flask, render_template, Response
import context

from camera import Camera
from detector import Detector
import threading
import time
import numpy as np

app = Flask(__name__)
#Camera = Camera.Camera
detector = Detector()
camera = Camera()


last_frame = None
ret = None
rvecs = None
tvecs = None
diagnostic_img = None
proper_green = (26, 178, 79)
axis_for_cube = np.float32([[0,0,0], [0,3,0], [3,3,0], [3,0,0],
                   [0,0,-3],[0,3,-3],[3,3,-3],[3,0,-3] ])

def draw_cube(img):
    imgpts, _ = cv.projectPoints(axis_for_cube, context.rvecs, context.tvecs, context.mtx, context.dist)
    imgpts = np.int32(imgpts).reshape(-1,2)

    # draw ground floor in green
    cv.drawContours(img, [imgpts[:4]],-1,(0,255,0),-3)

    # draw pillars in blue color
    for i,j in zip(range(4),range(4,8)):
        cv.line(img, tuple(imgpts[i]), tuple(imgpts[j]),proper_green,3)

    # draw top layer in red color
    cv.drawContours(img, [imgpts[4:]], -1, (0,255,0),-3)

    return img

def draw_target(img):
    height, width, _ = img.shape
    size = 50
    cv.line(img, (width/2 - size, height/2),(width/2 + size, height/2), proper_green,3)
    cv.line(img, (width/2, height/2 - size),(width/2, height/2  + size), proper_green,3)
    return img

def draw_color_values(frame):
    height, width, _ = frame.shape
    color = frame[height/2, width/2]
    hsv_color = cv.cvtColor(np.array([[color]]), cv.COLOR_BGR2HSV)[0][0]
    cv.putText(frame, 'o HSV: %d, %d, %d' %(hsv_color[0], hsv_color[1], hsv_color[2]) , (width/2, height/2), cv.FONT_HERSHEY_SIMPLEX, 0.7, proper_green, 2)

def detector_thread():
  global ret, rvecs, tvecs, diagnostic_img
  while context.keep_running:
    # get the job from the front of the queue
    frame = camera.get_frame()
    ret, rvecs, tvecs, diagnostic_img = detector.solve(frame)
    time.sleep(0.1)

thread = threading.Thread(target = detector_thread)
context.threads.append(thread)
# this ensures the thread will die when the main thread dies
# can set t.daemon to False if you want it to keep running
thread.daemon = False
thread.start()

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

@app.route('/diagnostic')
def diagnostic():
    """Video streaming home page."""
    return render_template('diagnostic.html')

@app.route('/color')
def color():
    """Video streaming home page."""
    return render_template('color.html')

@app.route('/both')
def both():
    """Video streaming home page."""
    return render_template('both.html')

def gen(camera):
    """Video streaming generator function."""
    while context.keep_running:
        frame = camera.get_frame().copy()
        draw_target(frame)

        if time.time() - 1 < context.last_detection:
            # img = draw_cube(frame)
            cv.putText(frame, 'X: %s' % round(context.tvecs[0][0], 3), (50, 50), cv.FONT_HERSHEY_SIMPLEX, 1, proper_green, 2)
            cv.putText(frame, 'Y: %s' % round(context.tvecs[1][0], 3), (50, 100), cv.FONT_HERSHEY_SIMPLEX, 1, proper_green, 2)
            cv.putText(frame, 'Z: %s' % round(context.tvecs[2][0], 3), (50, 150), cv.FONT_HERSHEY_SIMPLEX, 1, proper_green, 2)
        yield encode_and_embed(frame)

def encode_and_embed(frame):
    encoded_frame = cv.imencode('.jpg', frame)[1].tobytes()
    return (b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n' + encoded_frame + b'\r\n')

def gen_overlay(camera):
    """Video streaming generator function."""
    while context.keep_running:
        frame = camera.get_frame()
        global tvecs
        if len(tvecs) == 3:
            cv.putText(frame, 'X: %s' % round(tvecs[0][0], 3), (50, 50), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv.putText(frame, 'Y: %s' % round(tvecs[1][0], 3), (50, 100), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv.putText(frame, 'Z: %s' % round(tvecs[2][0], 3), (50, 150), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        yield encode_and_embed(frame)

def diagnostic_gen(camera):
    """Video streaming generator function."""
    global diagnostic_img

    while context.keep_running:
        yield encode_and_embed(diagnostic_img)


def color_gen(camera):
    """Video streaming generator function."""
    while context.keep_running:
        frame = camera.get_frame()
        draw_color_values(frame)
        yield encode_and_embed(frame)

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/diagnostic_feed')
def diagnostic_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(diagnostic_gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/color_feed')
def color_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(color_gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)

context.keep_running = False

for thread in context.threads:
    thread.join()
