from flask import Flask, render_template, redirect, request, session, url_for, g
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['DATABASE'] = os.path.join(app.instance_path, 'task_manager.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']
        
        if password != confirm:
            return render_template('register.html', error='Passwords do not match')
        
        db = get_db()
        try:
            hashed = generate_password_hash(password)
            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, hashed)
            )
            db.commit()
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Username already taken')
        
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    tasks = db.execute(
        'SELECT * FROM tasks WHERE user_id = ? ORDER BY due_date ASC',
        (session['user_id'],)
    ).fetchall()
    return render_template('dashboard.html', tasks=tasks)

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form['title']
    description = request.form['description']
    due_date = request.form['due_date']
    db = get_db()
    db.execute(
        'INSERT INTO tasks (user_id, title, description, due_date) VALUES (?, ?, ?, ?)',
        (session['user_id'], title, description, due_date)
    )
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/complete_task/<int:task_id>')
@login_required
def complete_task(task_id):
    db = get_db()
    db.execute(
        "UPDATE tasks SET status = 'completed' WHERE id = ?",
        (task_id,)
    )
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    db = get_db()
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    os.makedirs(app.instance_path, exist_ok=True)
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    app.run(debug=True)
