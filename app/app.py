from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 관리를 위한 비밀 키 설정

def init_db():
    """데이터베이스 초기화 및 관리자 테이블 생성"""
    conn = sqlite3.connect('../filter_words.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            is_owner BOOLEAN DEFAULT 0
        )
    ''')
    # 최고 관리자 계정이 없으면 생성
    c.execute('''
        INSERT OR IGNORE INTO admins (username, password, is_owner) VALUES ('owner', 'owner_password', 1)
    ''')
    conn.commit()
    conn.close()

def login_required(f):
    """사용자가 로그인했는지 확인하는 데코레이터."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('페이지에 접근하려면 로그인하세요.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def owner_required(f):
    """최고 관리자만 접근할 수 있는 데코레이터."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'is_owner' not in session or not session['is_owner']:
            flash('이 페이지에 접근할 권한이 없습니다.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('../filter_words.db')
        c = conn.cursor()
        c.execute('SELECT id, is_owner FROM admins WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            session['is_owner'] = user[1]
            session['is_admin'] = True  # Assuming all users in the admins table are admins
            return redirect(url_for('index'))
        else:
            flash('잘못된 자격 증명입니다. 다시 시도하세요.')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('is_owner', None)
    session.pop('is_admin', None)
    flash('로그아웃되었습니다.')
    return redirect(url_for('login'))

@app.route('/')
def index():
    """bad_words 테이블을 초기화하고 cnt 칼럼을 추가"""
    column_data = []
    conn = sqlite3.connect('../filter_words.db')
    c = conn.cursor()
    
    # bad_words 테이블이 존재하는지 확인하고 없으면 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS bad_words (
            word TEXT UNIQUE,
            cnt INTEGER DEFAULT 1
        )
    ''')

    # 정렬 방식 결정
    sort_order = request.args.get("sort", "desc")
    if sort_order == "asc":
        c.execute('SELECT cnt, word FROM bad_words ORDER BY cnt ASC')
    else:
        c.execute('SELECT cnt, word FROM bad_words ORDER BY cnt DESC')
    
    result = c.fetchall()
    column_data = [row for row in result]

    # 데이터베이스 연결 종료
    conn.close()

    # 리스트를 템플릿으로 넘겨주어 웹 페이지에 출력
    return render_template('index.html', words=column_data, is_admin=session.get('is_admin', False), is_owner=session.get('is_owner', False))

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        # 폼에서 입력한 단어를 가져옴
        new_word = request.form.get("word")

        # 데이터베이스에 새 단어를 추가
        conn = sqlite3.connect('../filter_words.db')
        c = conn.cursor()

        # 이미 존재하는 단어인지 확인한 후 없으면 추가
        c.execute('''
            INSERT OR IGNORE INTO bad_words (word) VALUES (?)
        ''', (new_word,))
        
        conn.commit()
        conn.close()

        # 추가 후 홈 화면으로 리디렉션
        return redirect(url_for('index'))
    
    # GET 요청일 때는 폼이 있는 페이지를 렌더링
    return render_template('add.html')

@app.route('/search', methods=['GET'])
def search():
    keyword = request.args.get('word', '')
    query = 'SELECT cnt, word FROM bad_words WHERE word LIKE ?'
    conn = sqlite3.connect('../filter_words.db')
    c = conn.cursor()
    c.execute(query, ('%' + keyword + '%',))
    result = c.fetchall()
    conn.close()
    return render_template('index.html', words=result, is_admin=session.get('is_admin', False), is_owner=session.get('is_owner', False))

@app.route("/remove", methods=["POST"])
@login_required
def remove():
    words = request.form.getlist("words")
    if words:
        conn = sqlite3.connect('../filter_words.db')
        c = conn.cursor()
        c.executemany('DELETE FROM bad_words WHERE word = ?', [(word,) for word in words])
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route("/get", methods=["POST"])
def get():
    word_list = request.get_json()
    conn = sqlite3.connect('../filter_words.db')
    c = conn.cursor()
    answer = {}
    i = 0
    for word in word_list['words']:
        c.execute('SELECT cnt, word FROM bad_words WHERE word = ?', (word,))
        result = c.fetchone()
        if result:
            answer[word] = '욕'
        else:
            answer[word] = '욕아님'
        i += 1
    conn.close()
    return jsonify(answer)

@app.route('/config', methods=['GET', 'POST'])
@owner_required
def config():
    """관리자 계정을 추가하거나 삭제할 수 있는 페이지"""
    conn = sqlite3.connect('../filter_words.db')
    c = conn.cursor()
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        if action == 'add':
            password = request.form.get('password')
            c.execute('INSERT INTO admins (username, password) VALUES (?, ?)', (username, password))
        elif action == 'delete':
            c.execute('DELETE FROM admins WHERE username = ?', (username,))
        conn.commit()
    c.execute('SELECT username, is_owner FROM admins')
    admins = c.fetchall()
    conn.close()
    return render_template('config.html', admins=admins)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
