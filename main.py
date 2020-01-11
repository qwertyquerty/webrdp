from flask import Response, stream_with_context, Flask, render_template
from io import BytesIO

from flask_socketio import SocketIO, send, emit

import mss

from PIL import Image

from threading import Thread

import base64

import eventlet

import mouse
import keyboard

from screeninfo import get_monitors

SCREENSIZE = (get_monitors()[0].width, get_monitors()[0].height)

SETTINGS = {
	"quality": 9
}

eventlet.monkey_patch()

app = Flask(__name__)

app.config['SECRET_KEY'] = 'thisisasupersecretkey'

socketio = SocketIO(app, async_mode='eventlet')

def stream_thread():

	def video_gen():
		while True:
			sct = mss.mss()
			screenshot = sct.grab(sct.monitors[1])

			pimg = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

			quo = 11 - SETTINGS["quality"]

			pimg.thumbnail((SCREENSIZE[0]/quo,SCREENSIZE[1]/quo))

			bytes = BytesIO()
			pimg.save(bytes, format="PNG")

			img_str = base64.b64encode(bytes.getvalue()).decode("utf-8") 

			yield img_str

	for img in video_gen():
		socketio.emit('video_frame', img,)
		socketio.sleep(0.1)

@app.route('/')
def index_page():
	return render_template('screen.html')

@socketio.on('connect')
def client_connected():
	print("Client connection")
	
@socketio.on('mousedown')
def client_mousedown(event):
	mouse.move(SCREENSIZE[0]*event["x"], SCREENSIZE[1]*event["y"])
	mouse.press()

@socketio.on('mouseup')
def client_mouseup():
	mouse.release()

@socketio.on('mousemove')
def client_mousemove(event):
	mouse.move(SCREENSIZE[0]*event["x"], SCREENSIZE[1]*event["y"])

key_translation = {
	"Meta": "left windows",
	"ArrowLeft": "left",
	"ArrowRight": "right",
	"ArrowUp": "up",
	"ArrowDown": "down"
}

@socketio.on('keydown')
def client_keydown(event):
	if event in key_translation: event = key_translation[event]
	print("keydown",event)
	keyboard.press(event)
	eventlet.sleep(0.1)
	keyboard.release(event)

"""
@socketio.on('keyup')
def client_keyup(event):
	if event in key_translation: event = key_translation[event]
	print("keyup",event)
	keyboard.release(event)
"""

@socketio.on('setting_quality')
def client_setting_quality(data):
	SETTINGS["quality"] = min(max(int(data), 1), 10)

if __name__ == "__main__":
	socketio.start_background_task(target=stream_thread)
	socketio.run(app, host='0.0.0.0', debug=True)