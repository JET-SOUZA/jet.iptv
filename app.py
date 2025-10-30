from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Tela inicial
@app.route('/')
def index():
    return render_template('index.html')

# Player HLS/MP4
@app.route('/player')
def player():
    stream_url = request.args.get('url', '')
    return render_template('player.html', stream_url=stream_url)

# Login Xtream
@app.route('/xtream', methods=['GET', 'POST'])
def xtream():
    if request.method == 'POST':
        server = request.form.get('server')
        username = request.form.get('username')
        password = request.form.get('password')
        # Aqui você pode adicionar validação real de Xtream
        # Para teste, redireciona para player
        stream_url = f"{server}/live/{username}/{password}/channel.m3u8"
        return redirect(url_for('player', url=stream_url))
    return render_template('login_xtream.html')

# Playlist M3U
@app.route('/playlist', methods=['GET', 'POST'])
def playlist():
    if request.method == 'POST':
        m3u_url = request.form.get('m3u_url')
        return redirect(url_for('player', url=m3u_url))
    return render_template('playlists.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
