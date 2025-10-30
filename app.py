from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CHAVE_SECRETA_SEGURA")  # 🔒 agora usa variável de ambiente (Render-friendly)

# ================================
# Configurações de diretórios
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================================
# Banco de dados
# ================================
def init_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))
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

init_db()

# ================================
# Dados de exemplo (mock)
# ================================
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

# ================================
# Funções de autenticação
# ================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('É necessário estar logado.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def premium_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('premium') != 1:
            flash('Acesso Premium necessário.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ================================
# Rotas públicas
# ================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash('Usuário registrado com sucesso!')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Usuário já existe.')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['premium'] = user[3]
            flash('Login realizado com sucesso!')
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da conta.')
    return redirect(url_for('login'))

# ================================
# Rotas Premium
# ================================
@app.route('/category/<category_name>')
@login_required
@premium_required
def category(category_name):
    items = CATEGORIES.get(category_name, [])
    return render_template('category.html', category_name=category_name, items=items)

@app.route('/player')
@login_required
@premium_required
def player():
    stream_url = request.args.get('url', '')
    return render_template('player.html', stream_url=stream_url)

@app.route('/xtream', methods=['GET', 'POST'])
@login_required
@premium_required
def xtream():
    if request.method == 'POST':
        server = request.form.get('server')
        username = request.form.get('username')
        password = request.form.get('password')
        stream_url = f"{server}/live/{username}/{password}/channel.m3u8"
        return redirect(url_for('player', url=stream_url))
    return render_template('login_xtream.html')

@app.route('/playlist', methods=['GET', 'POST'])
@login_required
@premium_required
def playlist():
    if request.method == 'POST':
        m3u_url = request.form.get('m3u_url')
        return redirect(url_for('player', url=m3u_url))
    return render_template('playlists.html')

@app.route('/local')
@login_required
@premium_required
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
                    "url": url_for('uploaded_file', filename=f"{category}/{f}")
                })
    return render_template('local_files.html', files=all_files)

@app.route('/uploads/<path:filename>')
@login_required
@premium_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ================================
# Execução local (Render ignora)
# ================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
