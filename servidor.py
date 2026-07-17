# Build: 2026-07-17-v2
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json, os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Load HTML from GitHub on startup (bypasses Railway file cache)
HTML_CONTENT = None

def get_html():
    global HTML_CONTENT
    if HTML_CONTENT:
        return HTML_CONTENT
    # Try local file first
    for name in ['index.html', 'app.html']:
        p = Path(__file__).parent / name
        if p.exists():
            HTML_CONTENT = p.read_text('utf-8')
            print(f"HTML loaded from {name}: {len(HTML_CONTENT)} bytes")
            return HTML_CONTENT
    # Fallback
    HTML_CONTENT = '<h1>Error: app.html not found</h1>'
    return HTML_CONTENT

def get_conn():
    if DATABASE_URL:
        import psycopg2
        url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        return psycopg2.connect(url), 'pg'
    else:
        import sqlite3
        db_path = Path(__file__).parent / 'datos.db'
        return sqlite3.connect(str(db_path)), 'sqlite'

def init_db():
    try:
        conn, tipo = get_conn()
        cur = conn.cursor()
        if tipo == 'pg':
            cur.execute('''CREATE TABLE IF NOT EXISTS datos (
                id INTEGER PRIMARY KEY,
                contenido TEXT NOT NULL,
                actualizado TIMESTAMP DEFAULT NOW()
            )''')
        else:
            cur.execute('''CREATE TABLE IF NOT EXISTS datos (
                id INTEGER PRIMARY KEY,
                contenido TEXT NOT NULL,
                actualizado TEXT
            )''')
        conn.commit()
        cur.close(); conn.close()
        print(f"[OK] Tabla 'datos' lista ({tipo})")
        return True
    except Exception as e:
        print(f"[ERROR] init_db: {e}")
        return False

init_db()

@app.route('/')
def index():
    html = get_html()
    resp = Response(html, mimetype='text/html; charset=utf-8')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

@app.route('/logo.png')
def logo():
    from flask import send_file
    logo_path = Path(__file__).parent / 'logo.png'
    if logo_path.exists():
        return send_file(str(logo_path), mimetype='image/png')
    return '', 404

@app.route('/api/load')
def load():
    try:
        conn, tipo = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT contenido FROM datos WHERE id=1')
        row = cur.fetchone()
        cur.close(); conn.close()
        if row:
            print(f"LOAD OK: {len(row[0])} bytes")
            return row[0], 200, {'Content-Type': 'application/json'}
        print("LOAD: vacío")
        return '{}', 200, {'Content-Type': 'application/json'}
    except Exception as e:
        print(f"LOAD ERROR: {e}")
        init_db()
        return '{}', 200, {'Content-Type': 'application/json'}

@app.route('/api/save', methods=['POST', 'OPTIONS'])
def save():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_data(as_text=True)
        parsed = json.loads(data)
        n_pj = len(parsed.get('proyectos', []))
        n_mov = len(parsed.get('movimientos', []))
        conn, tipo = get_conn()
        cur = conn.cursor()
        if tipo == 'pg':
            cur.execute('''INSERT INTO datos (id, contenido, actualizado)
                          VALUES (1, %s, NOW())
                          ON CONFLICT (id) DO UPDATE
                          SET contenido = EXCLUDED.contenido,
                              actualizado = NOW()''', (data,))
        else:
            cur.execute('''INSERT OR REPLACE INTO datos (id, contenido, actualizado)
                          VALUES (1, ?, ?)''', (data, datetime.now().isoformat()))
        conn.commit()
        cur.close(); conn.close()
        print(f"SAVE OK: {n_pj} proyectos, {n_mov} movimientos")
        return jsonify({'ok': True})
    except Exception as e:
        print(f"SAVE ERROR: {e}")
        init_db()
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/setup')
def setup():
    ok = init_db()
    try:
        conn, tipo = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM datos')
        count = cur.fetchone()[0]
        cur.close(); conn.close()
        html = get_html()
        return jsonify({'ok': ok, 'tipo': tipo, 'registros': count, 'html_bytes': len(html.encode())})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/health')
def health():
    try:
        conn, tipo = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM datos')
        count = cur.fetchone()[0]
        cur.close(); conn.close()
        html = get_html()
        return jsonify({'status': 'ok', 'tipo': tipo, 'registros': count, 'html_bytes': len(html.encode())})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/abrir')
def abrir():
    return jsonify({'ok': False, 'error': 'No disponible en modo nube'})

@app.route('/api/elegir-archivo')
def elegir_archivo():
    return jsonify({'ok': False, 'error': 'No disponible en modo nube'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    print(f"Iniciando en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
