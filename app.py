from flask import Flask, request, render_template, send_from_directory
from flask_socketio import SocketIO
import os
import yt_dlp
import tempfile
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = ''
socketio = SocketIO(app, cors_allowed_origins="*")

def progress_hook(response, socketio, sid):
    if response['status'] == 'downloading':
        percent = response['_percent_str']
        socketio.emit('download_progress', {'percent': percent}, namespace='/test', room=sid)
    elif response['status'] == 'finished':
        socketio.emit('download_progress', {'percent': '100%'}, namespace='/test', room=sid)
        socketio.emit('conversion_start', namespace='/test', room=sid)

def download_ytvid_as_mp3(url, sid):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(tempfile.gettempdir(), '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'progress_hooks': [lambda x: progress_hook(x, socketio, sid)],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        info = ydl.extract_info(url, download=False)
        file_name = ydl.prepare_filename(info)
        mp3_file_name = os.path.split(os.path.splitext(file_name)[0] + '.mp3')[1]
        socketio.emit('finished', {'file': mp3_file_name}, namespace='/test', room=sid)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/downloads/<path:filename>')
def download_file(filename):
    return send_from_directory(tempfile.gettempdir(), filename, as_attachment=True)

@socketio.on('start_download', namespace='/test')
def handle_message(message):
    threading.Thread(target=download_ytvid_as_mp3, args=(message['url'], request.sid)).start()

if __name__ == '__main__':
    socketio.run(app, debug=True)
