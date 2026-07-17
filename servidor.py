# Build: 2026-07-17T22:21:42.480588
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json, os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL', '')

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
        cur.close()
        conn.close()
        print(f"[OK] Tabla 'datos' lista ({tipo})")
        return True
    except Exception as e:
        print(f"[ERROR] init_db: {e}")
        return False

init_db()

@app.route('/')
def index():
    from flask import make_response
    resp = make_response(send_file('index.html'))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/logo.png')
def logo():
    logo_path = Path(__file__).parent / 'logo.png'
    if logo_path.exists():
        return send_file(str(logo_path), mimetype='image/png')
    return '', 404

@app.route('/api/setup')
def setup():
    """Endpoint para crear la tabla manualmente si no existe"""
    ok = init_db()
    try:
        conn, tipo = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM datos')
        count = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({'ok': ok, 'tipo': tipo, 'registros': count, 'db': DATABASE_URL[:30] if DATABASE_URL else 'SQLite'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

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

@app.route('/health')
def health():
    try:
        conn, tipo = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM datos')
        count = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({'status': 'ok', 'tipo': tipo, 'registros': count})
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
    print(f"DATABASE_URL: {'configurada' if DATABASE_URL else 'NO - usando SQLite'}")
    app.run(host='0.0.0.0', port=port, debug=False)

