from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
import os
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# ================================
# Configuração do Flask
# ================================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CHAVE_SECRETA_PADRAO")  # Use SECRET_KEY no Render

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ================================
# DB path
# ================================
DB_PATH = os.path.join(BASE_DIR, 'database.db')

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ================================
# Inicialização do banco de dados (com is_admin, expires_at)
# ================================
def init_db():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            premium INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            expires_at TEXT DEFAULT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("Banco inicializado com sucesso!")

init_db()

# ================================
# Cria admin inicial se não existir (lê variáveis de ambiente)
# ================================
def ensure_admin():
    admin_user = os.getenv("ADMIN_USER")
    admin_pass = os.getenv("ADMIN_PASS")
    if not admin_user or not admin_pass:
        print("Variáveis ADMIN_USER/ADMIN_PASS não definidas — pule criação automática do admin.")
        return
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (admin_user,))
    if cursor.fetchone():
        conn.close()
        print("Admin já existe.")
        return
    hashed = generate_password_hash(admin_pass)
    cursor.execute('INSERT INTO users (username, password, premium, is_admin) VALUES (?, ?, ?, ?)',
                   (admin_user, hashed, 1, 1))
    conn.commit()
    conn.close()
    print("Admin criado a partir de variáveis de ambiente.")

ensure_admin()

# ================================
# Decorators
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
        if session.get('premium') != 1:
            flash('Acesso Premium necessário.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('É necessário estar logado.')
            return redirect(url_for('login'))
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or row['is_admin'] != 1:
            flash('Acesso admin necessário.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ================================
# Rotas de autenticação (hash de senha)
# ================================
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if not username or not password:
            flash('Preencha todos os campos!')
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        try:
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed))
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
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, password, premium, expires_at FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            # checar expiração
            expires_at = user['expires_at']
            if expires_at:
                exp_dt = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                if datetime.now() > exp_dt:
                    flash('Conta expirada.')
                    return redirect(url_for('login'))
            session['user_id'] = user['id']
            session['premium'] = user['premium']
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
# Exemplo: rota /xtream mantida (ajustar para checar DB se quiser)
# ================================
@app.route('/xtream', methods=['GET','POST'])
def xtream():
    # aqui mantemos o comportamento original (monta stream) mas se quiser
    # autenticar contra DB, você pode adaptar como mostrado anteriormente.
    if request.method == 'POST':
        server = request.form.get('server')
        username = request.form.get('username')
        password = request.form.get('password')
        stream_url = f"{server}/live/{username}/{password}/channel.m3u8"
        return redirect(url_for('player', url=stream_url))
    return render_template('login_xtream.html')

# ================================
# ROTAS ADMIN: listar/criar/deletar/editar usuários
# ================================
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, premium, is_admin, expires_at FROM users ORDER BY id DESC')
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

@app.route('/admin/create', methods=['POST'])
@login_required
@admin_required
def admin_create_user():
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()
    premium = 1 if request.form.get('premium') == 'on' else 0
    is_admin = 1 if request.form.get('is_admin') == 'on' else 0
    expires_hours = request.form.get('expires_hours')  # opcional: criar conta teste
    if not username or not password:
        flash('Preencha username e senha.')
        return redirect(url_for('admin_panel'))
    hashed = generate_password_hash(password)
    expires_at = None
    if expires_hours:
        try:
            h = int(expires_hours)
            expires_at = (datetime.now() + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S")
        except:
            expires_at = None
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password, premium, is_admin, expires_at) VALUES (?, ?, ?, ?, ?)',
                       (username, hashed, premium, is_admin, expires_at))
        conn.commit()
        flash('Usuário criado com sucesso.')
    except sqlite3.IntegrityError:
        flash('Já existe um usuário com esse username.')
    finally:
        conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash('Usuário deletado.')
    return redirect(url_for('admin_panel'))

@app.route('/admin/toggle_premium/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_premium(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT premium FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        new = 0 if row['premium'] == 1 else 1
        cursor.execute('UPDATE users SET premium = ? WHERE id = ?', (new, user_id))
        conn.commit()
    conn.close()
    flash('Atualizado.')
    return redirect(url_for('admin_panel'))

@app.route('/admin/set_expiry/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_set_expiry(user_id):
    hours = request.form.get('expires_hours')
    expires_at = None
    if hours:
        try:
            h = int(hours)
            expires_at = (datetime.now() + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S")
        except:
            expires_at = None
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET expires_at = ? WHERE id = ?', (expires_at, user_id))
    conn.commit()
    conn.close()
    flash('Expiração definida.')
    return redirect(url_for('admin_panel'))

# ================================
# Mantenha o restante das rotas (category, player, etc.) como já tinha
# ================================
# ... (seu código existente: index, category, player, local_files, uploads, etc.)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
