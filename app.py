from flask import Flask, render_template, send_file
import os

app = Flask(__name__)

# Página inicial (HTML bonito com lista)
@app.route('/')
def index():
    return render_template('index.html')

# Rota para baixar a playlist M3U
@app.route('/playlist')
def playlist():
    playlist_path = os.path.join('playlist', 'jet-tv-legal.m3u')
    return send_file(playlist_path, mimetype='audio/x-mpegurl', as_attachment=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
