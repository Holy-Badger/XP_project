from flask import Flask, render_template, request, redirect, url_for, flash, g
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'data' / 'lectory.db'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'public-lectory-dev-key'


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS lecturers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        specialization TEXT NOT NULL,
        topic TEXT NOT NULL,
        bio TEXT
    );

    CREATE TABLE IF NOT EXISTS lectures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        lecture_date TEXT NOT NULL,
        lecture_time TEXT NOT NULL,
        format TEXT NOT NULL,
        place TEXT NOT NULL,
        lecturer_id INTEGER NOT NULL,
        seats INTEGER NOT NULL DEFAULT 50,
        FOREIGN KEY (lecturer_id) REFERENCES lecturers (id)
    );

    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        age_group TEXT NOT NULL,
        email TEXT NOT NULL,
        participation_format TEXT NOT NULL,
        lecture_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (lecture_id) REFERENCES lectures (id)
    );

    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listener_name TEXT NOT NULL,
        lecture_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        submitted_at TEXT NOT NULL,
        FOREIGN KEY (lecture_id) REFERENCES lectures (id)
    );
    ''')

    lecturer_count = cursor.execute('SELECT COUNT(*) FROM lecturers').fetchone()[0]
    if lecturer_count == 0:
        cursor.executemany(
            'INSERT INTO lecturers (full_name, specialization, topic, bio) VALUES (?, ?, ?, ?)',
            [
                ('Лукин Глеб Олегович', 'История науки', 'Научные мифы: почему мы верим в ложные факты', 'Руководитель проекта и лектор по истории науки и просвещения.'),
                ('Савинов Артур Эльмирович', 'Информационные технологии', 'Будущее уже здесь: ИИ в повседневной жизни', 'Backend-разработчик проекта, интересуется цифровыми сервисами и ИИ.'),
                ('Слобцев Иван Игоревич', 'Экология и цифровые медиа', 'Экология города: как технологии помогают окружающей среде', 'Frontend-разработчик и популяризатор цифровых решений.'),
                ('Боталов Иван Сергеевич', 'Психология восприятия', 'Как критически мыслить в эпоху соцсетей', 'Тестировщик проекта, занимается анализом пользовательского опыта.'),
            ]
        )

    lecture_count = cursor.execute('SELECT COUNT(*) FROM lectures').fetchone()[0]
    if lecture_count == 0:
        cursor.executemany(
            '''INSERT INTO lectures
            (title, description, lecture_date, lecture_time, format, place, lecturer_id, seats)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            [
                ('Научные мифы и заблуждения', 'Открытая лекция о самых распространённых псевдонаучных убеждениях и способах их распознавания.', '2026-05-07', '18:30', 'Очно + онлайн', 'г. Пермь, Молодёжный центр', 1, 80),
                ('Будущее уже здесь: искусственный интеллект', 'Разговор о том, как ИИ меняет образование, работу и повседневную жизнь.', '2026-05-14', '18:30', 'Очно + онлайн', 'г. Пермь, Городская библиотека', 2, 70),
                ('Экология и городская среда', 'Лекция о современных экологических вызовах и роли технологий в их решении.', '2026-05-21', '18:30', 'Очно + онлайн', 'г. Пермь, Коворкинг-центр', 3, 60),
                ('Критическое мышление в цифровую эпоху', 'Практические инструменты проверки информации и защиты от манипуляций.', '2026-05-28', '18:30', 'Очно + онлайн', 'г. Пермь, Молодёжный центр', 4, 90),
            ]
        )

    db.commit()
    db.close()


@app.route('/')
def index():
    db = get_db()
    stats = {
        'lectures': db.execute('SELECT COUNT(*) AS cnt FROM lectures').fetchone()['cnt'],
        'lecturers': db.execute('SELECT COUNT(*) AS cnt FROM lecturers').fetchone()['cnt'],
        'registrations': db.execute('SELECT COUNT(*) AS cnt FROM registrations').fetchone()['cnt'],
        'feedback_count': db.execute('SELECT COUNT(*) AS cnt FROM feedback').fetchone()['cnt'],
    }
    upcoming = db.execute(
        '''SELECT lectures.*, lecturers.full_name
           FROM lectures
           JOIN lecturers ON lecturers.id = lectures.lecturer_id
           ORDER BY lecture_date, lecture_time
           LIMIT 3'''
    ).fetchall()
    return render_template('index.html', stats=stats, upcoming=upcoming)


@app.route('/lectures')
def lectures():
    db = get_db()
    lecture_list = db.execute(
        '''SELECT lectures.*, lecturers.full_name
           FROM lectures
           JOIN lecturers ON lecturers.id = lectures.lecturer_id
           ORDER BY lecture_date, lecture_time'''
    ).fetchall()
    return render_template('lectures.html', lectures=lecture_list)


@app.route('/lecturers')
def lecturers():
    db = get_db()
    lecturer_list = db.execute('SELECT * FROM lecturers ORDER BY full_name').fetchall()
    return render_template('lecturers.html', lecturers=lecturer_list)


@app.route('/register', methods=['GET', 'POST'])
def register():
    db = get_db()
    lectures = db.execute('SELECT id, title, lecture_date, lecture_time FROM lectures ORDER BY lecture_date').fetchall()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        age_group = request.form.get('age_group', '').strip()
        email = request.form.get('email', '').strip()
        participation_format = request.form.get('participation_format', '').strip()
        lecture_id = request.form.get('lecture_id', '').strip()

        if not all([full_name, age_group, email, participation_format, lecture_id]):
            flash('Пожалуйста, заполните все поля формы.', 'error')
            return render_template('register.html', lectures=lectures)

        db.execute(
            '''INSERT INTO registrations (full_name, age_group, email, participation_format, lecture_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (full_name, age_group, email, participation_format, lecture_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        db.commit()
        flash('Регистрация успешно отправлена.', 'success')
        return redirect(url_for('register'))

    return render_template('register.html', lectures=lectures)


@app.route('/feedback', methods=['GET', 'POST'])
def submit_feedback():
    db = get_db()
    lectures = db.execute('SELECT id, title FROM lectures ORDER BY lecture_date').fetchall()

    if request.method == 'POST':
        listener_name = request.form.get('listener_name', '').strip()
        lecture_id = request.form.get('lecture_id', '').strip()
        rating = request.form.get('rating', '').strip()
        comment = request.form.get('comment', '').strip()

        if not all([listener_name, lecture_id, rating]):
            flash('Для отправки отзыва заполните обязательные поля.', 'error')
            return render_template('feedback.html', lectures=lectures)

        db.execute(
            '''INSERT INTO feedback (listener_name, lecture_id, rating, comment, submitted_at)
               VALUES (?, ?, ?, ?, ?)''',
            (listener_name, lecture_id, int(rating), comment, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        db.commit()
        flash('Спасибо! Ваш отзыв сохранён.', 'success')
        return redirect(url_for('submit_feedback'))

    return render_template('feedback.html', lectures=lectures)


@app.route('/dashboard')
def dashboard():
    db = get_db()
    registrations = db.execute(
        '''SELECT registrations.*, lectures.title
           FROM registrations
           JOIN lectures ON lectures.id = registrations.lecture_id
           ORDER BY registrations.created_at DESC'''
    ).fetchall()
    feedback_rows = db.execute(
        '''SELECT feedback.*, lectures.title
           FROM feedback
           JOIN lectures ON lectures.id = feedback.lecture_id
           ORDER BY feedback.submitted_at DESC'''
    ).fetchall()
    return render_template('dashboard.html', registrations=registrations, feedback_rows=feedback_rows)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
