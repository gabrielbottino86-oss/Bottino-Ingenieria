Gestión de Proyectos - Bottino Ingeniería
Servidor Flask para Railway (PostgreSQL)
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json, os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

# ── Base de datos PostgreSQL (Railway) o SQLite (local) ──────────────────
DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_db():
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return conn, 'pg'
    else:
        import sqlite3
        db_path = Path(__file__).parent / 'datos.db'
        conn = sqlite3.connect(str(db_path))
        return conn, 'sqlite'

def init_db():
    conn, tipo = get_db()
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
    print(f"DB OK ({tipo}): {DATABASE_URL[:30] if DATABASE_URL else 'SQLite local'}")

@app.route('/')
def index():
    return send_file('app.html')

@app.route('/logo.png')
def logo():
    logo_path = Path(__file__).parent / 'logo.png'
    if logo_path.exists():
        return send_file(str(logo_path), mimetype='image/png')
    return '', 404

@app.route('/api/load')
def load():
    try:
        conn, tipo = get_db()
        cur = conn.cursor()
        cur.execute('SELECT contenido FROM datos WHERE id=1')
        row = cur.fetchone()
        cur.close(); conn.close()
        if row:
            return row[0], 200, {'Content-Type': 'application/json'}
        return '{}', 200, {'Content-Type': 'application/json'}
    except Exception as e:
        print(f"LOAD ERROR: {e}")
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
        ts = datetime.now().isoformat()
        conn, tipo = get_db()
        cur = conn.cursor()
        if tipo == 'pg':
            cur.execute('''INSERT INTO datos (id, contenido, actualizado)
                          VALUES (1, %s, NOW())
                          ON CONFLICT (id) DO UPDATE SET contenido=%s, actualizado=NOW()''',
                       (data, data))
        else:
            cur.execute('''INSERT OR REPLACE INTO datos (id, contenido, actualizado)
                          VALUES (1, ?, ?)''', (data, ts))
        conn.commit()
        cur.close(); conn.close()
        print(f"SAVE OK: {n_pj} proyectos, {n_mov} movimientos")
        return jsonify({'ok': True})
    except Exception as e:
        print(f"SAVE ERROR: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/abrir')
def abrir():
    # En la nube no se puede abrir archivos locales
    return jsonify({'ok': False, 'error': 'No disponible en modo nube'})

@app.route('/api/elegir-archivo')
def elegir_archivo():
    return jsonify({'ok': False, 'error': 'No disponible en modo nube'})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8765))
    print(f"Iniciando en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
