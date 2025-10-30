from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'SEU_SECRET_KEY'

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        premium INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

# Inicializa banco ao iniciar o app
init_db()


# Dados de exemplo online
CATEGORIES = {
    "Ao Vivo": [
        {"name": "Canal 1", "url": "https://teste.com/live1.m3u8"},
        {"name": "Canal 2", "url": "https://teste.com/live2.m3u8"}
    ],
    "Filmes": [
        {"name": "Filme 1", "url": "https://teste.com/movie1.mp4"},
        {"name": "Filme 2", "url": "https://teste.com/movie2.mp4"}
    ],
    "Séries": [
        {"name": "Série 1 - Ep1", "url": "https://teste.com/serie1e1.mp4"},
        {"name": "Série 2 - Ep1", "url": "https://teste.com/serie2e1.mp4"}
    ]
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/category/<category_name>')
def category(category_name):
    items = CATEGORIES.get(category_name, [])
    return render_template('category.html', category_name=category_name, items=items)

@app.route('/player')
def player():
    stream_url = request.args.get('url', '')
    return render_template('player.html', stream_url=stream_url)

@app.route('/xtream', methods=['GET', 'POST'])
def xtream():
    if request.method == 'POST':
        server = request.form.get('server')
        username = request.form.get('username')
        password = request.form.get('password')
        stream_url = f"{server}/live/{username}/{password}/channel.m3u8"
        return redirect(url_for('player', url=stream_url))
    return render_template('login_xtream.html')

@app.route('/playlist', methods=['GET', 'POST'])
def playlist():
    if request.method == 'POST':
        m3u_url = request.form.get('m3u_url')
        return redirect(url_for('player', url=m3u_url))
    return render_template('playlists.html')

# Página de arquivos locais
@app.route('/local')
def local_files():
    all_files = []
    for category in os.listdir(app.config['UPLOAD_FOLDER']):
        cat_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
        if os.path.isdir(cat_path):
            files = os.listdir(cat_path)
            for f in files:
                all_files.append({
                    "category": category,
                    "name": f,
                    "url": f"/uploads/{category}/{f}"
                })
    return render_template('local_files.html', files=all_files)

# Servir arquivos locais
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
