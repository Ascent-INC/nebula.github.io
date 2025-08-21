import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from werkzeug.security import generate_password_hash, check_password_hash

###############################################
#  Flask Forum – Single-file app
#  • Crea automáticamente /templates y /static
#  • UI renovada: glassmorphism + gradientes + dark mode
#  • Login/Register, Dashboard, Foro con hilos/respuestas
#  • Seed de datos opcional en el primer arranque
#  • Nueva sección: Máquinas y retos de Hack The Box
###############################################
APP_NAME = "Nebula Vault"
DB_PATH = "db.sqlite3"
TEMPLATES_DIR = "templates"
STATIC_DIR = "static"
app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = os.urandom(32)

# --------------- Helpers ---------------
def ensure_dirs():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db(seed=True):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            thread_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(thread_id) REFERENCES threads(id) ON DELETE CASCADE
        )
        """
    )
    # Tabla para máquinas HTB
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS htb_machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            os TEXT NOT NULL,
            ip TEXT,
            status TEXT DEFAULT 'Activa',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Admin por defecto
    cur.execute("SELECT 1 FROM users WHERE username=?", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users(username, password) VALUES (?,?)",
            ("admin", generate_password_hash("nxn£2K0(£d|%B'Z54u6£$_Nv347$4}lA[MRphjACe+F&6$Mo0i")),
        )
    # Seed suave si la DB está vacía
    cur.execute("SELECT COUNT(*) FROM threads")
    if seed and cur.fetchone()[0] == 0:
        demo_threads = [
            ("Bienvenida a Nebula Vault", "Comparte tips de ciberseguridad, laboratorios y writeups.", "admin"),
            ("Recursos útiles", "Deja tus enlaces favoritos (herramientas, cheat-sheets, labs).", "admin"),
        ]
        cur.executemany(
            "INSERT INTO threads(title, content, author) VALUES (?,?,?)",
            demo_threads,
        )
    # Seed de máquinas HTB
    cur.execute("SELECT COUNT(*) FROM htb_machines")
    if seed and cur.fetchone()[0] == 0:
        demo_machines = [
            ("Legacy", "Fácil", "Windows", "10.10.10.4", "Retirada"),
            ("Active", "Media", "Windows", "10.10.10.100", "Activa"),
            ("Jarvis", "Difícil", "Linux", "10.10.10.143", "Activa"),
            ("Netmon", "Fácil", "Linux", "10.10.10.152", "Retirada"),
            ("Chatterbox", "Media", "Windows", "10.10.10.74", "Activa"),
            ("Bastion", "Difícil", "Windows", "10.10.10.134", "Activa"),
        ]
        cur.executemany(
            "INSERT INTO htb_machines(name, difficulty, os, ip, status) VALUES (?,?,?,?,?)",
            demo_machines,
        )
    db.commit()
    db.close()

# --------------- Template & Asset Writers ---------------
def write_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

def scaffold_assets():
    # --- Base CSS para finos detalles (sobre Tailwind) ---
    style_css = r"""
/* Tailwind via CDN se usa para la mayor parte.
   Aquí afinamos pequeños detalles que no cubren utilidades. */
:root { --ring: 0 0% 100%; }
html.dark { color-scheme: dark; }
body { transition: background-color .4s ease, color .4s ease; }
/***** Glass cards *****/
.glass {
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  background: rgba(255,255,255,.65);
}
.dark .glass { background: rgba(17,24,39,.65); }
/***** Fancy focus ring *****/
.focus-glow:focus { outline: none; box-shadow: 0 0 0 3px rgba(129,140,248,.5); }
/***** Smooth hover lift *****/
.lift { transition: transform .2s ease, box-shadow .2s ease; }
.lift:hover { transform: translateY(-2px); }
/***** Text clamp *****/
.clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
"""
    base_html = r"""
<!doctype html>
<html lang="es" x-data="theme()" :class="{dark: isDark}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title or '""" + APP_NAME + r"""' }}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui'] },
          colors: { brand: { 50:'#eef2ff', 400:'#818cf8', 500:'#6366f1', 600:'#4f46e5', 700:'#4338ca' } }
        }
      }
    }
  </script>
  <style> body{font-family:Inter,ui-sans-serif,system-ui;} </style>
</head>
<body class="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-200 dark:from-gray-900 dark:via-slate-900 dark:to-black text-slate-800 dark:text-slate-100">
  <!-- Navbar -->
  <nav class="sticky top-0 z-50 backdrop-blur bg-white/70 dark:bg-gray-900/70 border-b border-white/20 dark:border-white/10">
    <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
      <a href="{{ url_for('dashboard') if session.get('user') else url_for('login') }}" class="text-xl font-extrabold bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 bg-clip-text text-transparent">
        """ + APP_NAME + r"""
      </a>
      <div class="flex items-center gap-2">
        {% if session.get('user') %}
          <a class="px-3 py-2 rounded-xl lift hover:bg-indigo-50 dark:hover:bg-white/10" href="{{ url_for('threads') }}">Hilos</a>
          <a class="px-3 py-2 rounded-xl lift hover:bg-indigo-50 dark:hover:bg-white/10" href="{{ url_for('htb') }}">HTB</a>
          <a class="px-3 py-2 rounded-xl lift hover:bg-indigo-50 dark:hover:bg-white/10" href="{{ url_for('profile') }}">Perfil</a>
          <a class="px-3 py-2 rounded-xl lift hover:bg-rose-50 dark:hover:bg-white/10" href="{{ url_for('logout') }}">Salir</a>
        {% else %}
          <a class="px-3 py-2 rounded-xl lift hover:bg-indigo-50 dark:hover:bg-white/10" href="{{ url_for('login') }}">Login</a>
          <a class="px-3 py-2 rounded-xl lift hover:bg-indigo-50 dark:hover:bg-white/10" href="{{ url_for('register') }}">Registro</a>
        {% endif %}
        <button @click="toggle()" class="ml-2 p-2 rounded-xl lift hover:bg-indigo-50 dark:hover:bg-white/10" aria-label="Cambiar tema">
          <svg x-show="!isDark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-5 h-5"><path fill="currentColor" d="M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12m0 4a1 1 0 0 1-1-1v-1a1 1 0 1 1 2 0v1a1 1 0 0 1-1 1M5 13H4a1 1 0 1 1 0-2h1a1 1 0 1 1 0 2m15 0h-1a1 1 0 1 1 0-2h1a1 1 0 1 1 0 2M6.3 18.7a1 1 0 0 1-1.4-1.4l.7-.7a1 1 0 0 1 1.4 1.4zM18.4 7.4a1 1 0 0 1-1.4-1.4l.7-.7A1 1 0 1 1 18.4 7.4M6.3 5.3a1 1 0 0 1 0-1.4l.7-.7A1 1 0 1 1 8.4 3.6l-.7.7a1 1 0 0 1-1.4 0M17.7 20.7a1 1 0 1 1-1.4-1.4l.7-.7a1 1 0 1 1 1.4 1.4z"/></svg>
          <svg x-show="isDark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-5 h-5"><path fill="currentColor" d="M21 12.79A9 9 0 1 1 11.21 3A7 7 0 0 0 21 12.79"/></svg>
        </button>
      </div>
    </div>
  </nav>
  <!-- Main -->
  <main class="max-w-6xl mx-auto px-4 py-8">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="space-y-2 mb-6">
          {% for cat, msg in messages %}
            <div class="px-4 py-3 rounded-xl text-sm glass border border-white/20 {{ 'text-emerald-700 bg-emerald-50/60' if cat=='success' else 'text-rose-700 bg-rose-50/60' }} dark:text-white">
              {{ msg }}
            </div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>
  <footer class="py-10 text-center text-xs text-slate-500 dark:text-slate-400">
    <span class="opacity-70">© {{ datetime.utcnow().year }} """ + APP_NAME + r""" · Hecho con Flask</span>
  </footer>
  <script>
    function theme(){
      return {
        isDark: localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches),
        toggle(){ this.isDark = !this.isDark; localStorage.setItem('theme', this.isDark ? 'dark' : 'light'); }
      }
    }
    // Atajos: Ctrl+Enter envía formularios con data-hotkey
    document.addEventListener('keydown', (e)=>{
      if((e.ctrlKey || e.metaKey) && e.key === 'Enter'){
        const form = document.querySelector('form[data-hotkey="submit"]');
        if(form) form.requestSubmit();
      }
    });
  </script>
</body>
</html>
"""
    login_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="min-h-[70vh] grid place-items-center">
  <div class="glass rounded-3xl p-8 shadow-2xl w-full max-w-md border border-white/20 lift">
    <h1 class="text-3xl font-extrabold text-center mb-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 bg-clip-text text-transparent">Entrar</h1>
    <p class="text-center text-sm text-slate-600 dark:text-slate-300 mb-6">Bienvenido de vuelta a <strong>""" + APP_NAME + r"""</strong></p>
    {% if error %}<div class="mb-4 px-3 py-2 rounded-lg bg-rose-100/70 text-rose-700 dark:text-rose-100">{{ error }}</div>{% endif %}
    <form method="post" class="space-y-4" data-hotkey="submit">
      <div>
        <label class="block text-sm mb-1">Usuario</label>
        <input name="username" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" placeholder="tu_usuario" />
      </div>
      <div>
        <label class="block text-sm mb-1">Contraseña</label>
        <input type="password" name="password" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" placeholder="••••••••" />
      </div>
      <button class="w-full px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-600 via-purple-600 to-cyan-500 hover:opacity-95 lift">Entrar</button>
    </form>
    <a href="{{ url_for('register') }}" class="block mt-6 text-center text-indigo-600 dark:text-indigo-400 hover:underline">¿No tienes cuenta? Regístrate</a>
  </div>
</div>
{% endblock %}
"""
    register_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="min-h-[70vh] grid place-items-center">
  <div class="glass rounded-3xl p-8 shadow-2xl w-full max-w-md border border-white/20 lift">
    <h1 class="text-3xl font-extrabold text-center mb-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 bg-clip-text text-transparent">Crear cuenta</h1>
    {% if error %}<div class="mb-4 px-3 py-2 rounded-lg bg-rose-100/70 text-rose-700 dark:text-rose-100">{{ error }}</div>{% endif %}
    <form method="post" class="space-y-4" data-hotkey="submit">
      <div>
        <label class="block text-sm mb-1">Usuario</label>
        <input name="username" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" placeholder="nuevo_usuario" />
      </div>
      <div>
        <label class="block text-sm mb-1">Contraseña</label>
        <input type="password" name="password" required minlength="6" class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" placeholder="mínimo 6 caracteres" />
      </div>
      <button class="w-full px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-500 hover:opacity-95 lift">Crear cuenta</button>
    </form>
    <a href="{{ url_for('login') }}" class="block mt-6 text-center text-indigo-600 dark:text-indigo-400 hover:underline">¿Ya tienes cuenta? Inicia sesión</a>
  </div>
</div>
{% endblock %}
"""
    dashboard_html = r"""
{% extends 'base.html' %}
{% block content %}
<section class="mb-10">
  <div class="glass rounded-3xl p-8 border border-white/20">
    <h2 class="text-2xl md:text-3xl font-extrabold mb-2">Hola, {{ user }}</h2>
    <p class="text-slate-600 dark:text-slate-300">Este es tu panel de control. Accede al foro, gestiona tu cuenta y comparte conocimiento.</p>
  </div>
</section>
<section class="grid grid-cols-1 md:grid-cols-4 gap-6">
  <div class="glass rounded-3xl p-6 border border-white/20 lift">
    <p class="text-sm text-slate-500 mb-2">Usuarios</p>
    <p class="text-5xl font-extrabold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">{{ stats.users }}</p>
  </div>
  <div class="glass rounded-3xl p-6 border border-white/20 lift">
    <p class="text-sm text-slate-500 mb-2">Hilos</p>
    <p class="text-5xl font-extrabold bg-gradient-to-r from-cyan-500 to-indigo-500 bg-clip-text text-transparent">{{ stats.threads }}</p>
  </div>
  <div class="glass rounded-3xl p-6 border border-white/20 lift">
    <p class="text-sm text-slate-500 mb-2">Respuestas</p>
    <p class="text-5xl font-extrabold bg-gradient-to-r from-emerald-500 to-cyan-500 bg-clip-text text-transparent">{{ stats.replies }}</p>
  </div>
  <div class="glass rounded-3xl p-6 border border-white/20 lift">
    <p class="text-sm text-slate-500 mb-2">Máquinas HTB</p>
    <p class="text-5xl font-extrabold bg-gradient-to-r from-rose-500 to-purple-500 bg-clip-text text-transparent">{{ stats.htb_machines }}</p>
  </div>
</section>
{% endblock %}
"""
    threads_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="flex items-center justify-between mb-6">
  <h2 class="text-2xl md:text-3xl font-extrabold">Hilos del Foro</h2>
  <a href="{{ url_for('create_thread') }}" class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-600 to-purple-600 lift">Nuevo hilo</a>
</div>
<div class="grid gap-4">
  {% for thread in threads %}
    <a href="{{ url_for('thread_detail', id=thread['id']) }}" class="glass rounded-2xl p-5 border border-white/20 lift block">
      <h3 class="text-lg md:text-xl font-bold mb-1">{{ thread['title'] }}</h3>
      <p class="text-sm text-slate-600 dark:text-slate-300 clamp-2">{{ thread['content'] }}</p>
      <div class="mt-3 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>Autor: <strong>{{ thread['author'] }}</strong></span>
        <span>Respuestas: {{ thread['reply_count'] }}</span>
      </div>
    </a>
  {% else %}
    <div class="text-slate-600 dark:text-slate-300">Aún no hay hilos. ¡Crea el primero!</div>
  {% endfor %}
</div>
{% endblock %}
"""
    thread_detail_html = r"""
{% extends 'base.html' %}
{% block content %}
<article class="glass rounded-3xl p-8 border border-white/20 mb-8">
  <h1 class="text-2xl md:text-3xl font-extrabold mb-2">{{ thread['title'] }}</h1>
  <p class="text-sm text-slate-500 dark:text-slate-400 mb-6">Por <strong>{{ thread['author'] }}</strong> · {{ thread['created_at'] }}</p>
  <div class="prose dark:prose-invert max-w-none">{{ thread['content'] }}</div>
  {% if session['user'] == thread['author'] %}
    <div class="mt-6 flex gap-2">
      <a href="{{ url_for('edit_thread', id=thread['id']) }}" class="px-4 py-2 rounded-xl bg-amber-500 text-white lift">Editar</a>
      <a href="{{ url_for('delete_thread', id=thread['id']) }}" class="px-4 py-2 rounded-xl bg-rose-600 text-white lift" onclick="return confirm('¿Eliminar este hilo y todas sus respuestas?');">Eliminar</a>
    </div>
  {% endif %}
</article>
<section class="mb-8">
  <h2 class="text-xl font-bold mb-3">Respuestas</h2>
  <div class="space-y-3">
    {% for reply in replies %}
      <div class="glass rounded-xl p-4 border border-white/20 flex items-start justify-between">
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400 mb-1">{{ reply['author'] }} · {{ reply['created_at'] }}</p>
          <p>{{ reply['content'] }}</p>
        </div>
        {% if session['user'] == reply['author'] %}
          <a href="{{ url_for('delete_reply', id=reply['id']) }}" class="text-rose-500 hover:underline" onclick="return confirm('¿Eliminar respuesta?');">Eliminar</a>
        {% endif %}
      </div>
    {% else %}
      <p class="text-slate-600 dark:text-slate-300">No hay respuestas todavía.</p>
    {% endfor %}
  </div>
</section>
<form method="post" class="glass rounded-2xl p-6 border border-white/20 space-y-3" data-hotkey="submit">
  <label class="block text-sm">Nueva respuesta</label>
  <textarea name="content" rows="4" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" placeholder="Escribe tu respuesta..."></textarea>
  <button class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-600 to-purple-600 lift">Responder (Ctrl+Enter)</button>
</form>
{% endblock %}
"""
    create_thread_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="max-w-3xl mx-auto glass rounded-3xl p-8 border border-white/20">
  <h2 class="text-2xl md:text-3xl font-extrabold mb-6">Crear nuevo hilo</h2>
  <form method="post" class="space-y-5" data-hotkey="submit">
    <div>
      <label class="block text-sm mb-1">Título</label>
      <input name="title" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" />
    </div>
    <div>
      <label class="block text-sm mb-1">Contenido</label>
      <textarea name="content" rows="8" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" placeholder="Comparte detalles, enlaces, comandos..."></textarea>
    </div>
    <button class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-500 lift">Publicar</button>
  </form>
</div>
{% endblock %}
"""
    edit_thread_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="max-w-3xl mx-auto glass rounded-3xl p-8 border border-white/20">
  <h2 class="text-2xl md:text-3xl font-extrabold mb-6">Editar hilo</h2>
  {% if error %}<div class="mb-4 px-3 py-2 rounded-lg bg-rose-100/70 text-rose-700 dark:text-rose-100">{{ error }}</div>{% endif %}
  <form method="post" class="space-y-5" data-hotkey="submit">
    <input name="title" value="{{ thread['title'] }}" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" />
    <textarea name="content" rows="8" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow">{{ thread['content'] }}</textarea>
    <button class="px-5 py-3 rounded-xl font-bold text-white bg-amber-500 hover:bg-amber-600 lift">Guardar cambios</button>
  </form>
</div>
{% endblock %}
"""
    profile_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="min-h-[60vh] grid place-items-center">
  <div class="glass rounded-3xl p-8 w-full max-w-lg border border-white/20">
    <h2 class="text-2xl md:text-3xl font-extrabold mb-2">Perfil</h2>
    <p class="mb-6 text-slate-600 dark:text-slate-300">Usuario: <strong>{{ session['user'] }}</strong></p>
    {% if success %}<div class="mb-4 px-3 py-2 rounded-lg bg-emerald-100/70 text-emerald-700 dark:text-emerald-100">{{ success }}</div>{% endif %}
    {% if error %}<div class="mb-4 px-3 py-2 rounded-lg bg-rose-100/70 text-rose-700 dark:text-rose-100">{{ error }}</div>{% endif %}
    <form method="post" class="space-y-4" data-hotkey="submit">
      <div>
        <label class="block text-sm mb-1">Nueva contraseña</label>
        <input type="password" name="new_password" required minlength="6" class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" />
      </div>
      <div>
        <label class="block text-sm mb-1">Confirmar contraseña</label>
        <input type="password" name="confirm_password" required minlength="6" class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" />
      </div>
      <button class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-600 to-purple-600 lift">Cambiar contraseña</button>
    </form>
  </div>
</div>
{% endblock %}
"""
    # Nuevas plantillas para HTB
    htb_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="flex items-center justify-between mb-6">
  <h2 class="text-2xl md:text-3xl font-extrabold">Máquinas HTB</h2>
  <a href="{{ url_for('add_htb') }}" class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-600 to-purple-600 lift">Añadir máquina</a>
</div>

<div class="grid gap-4">
  {% for machine in machines %}
    <div class="glass rounded-2xl p-5 border border-white/20 lift">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex-1">
          <div class="flex items-center gap-3 mb-2">
            <h3 class="text-lg md:text-xl font-bold">{{ machine['name'] }}</h3>
            <span class="px-2 py-1 rounded-full text-xs font-medium 
              {% if machine['difficulty'] == 'Fácil' %}bg-emerald-100 text-emerald-800
              {% elif machine['difficulty'] == 'Media' %}bg-amber-100 text-amber-800
              {% elif machine['difficulty'] == 'Difícil' %}bg-rose-100 text-rose-800
              {% else %}bg-purple-100 text-purple-800{% endif %}">
              {{ machine['difficulty'] }}
            </span>
            <span class="px-2 py-1 rounded-full text-xs font-medium 
              {% if machine['os'] == 'Linux' %}bg-blue-100 text-blue-800
              {% else %}bg-gray-100 text-gray-800{% endif %}">
              {{ machine['os'] }}
            </span>
            <span class="px-2 py-1 rounded-full text-xs font-medium 
              {% if machine['status'] == 'Activa' %}bg-green-100 text-green-800
              {% else %}bg-gray-100 text-gray-800{% endif %}">
              {{ machine['status'] }}
            </span>
          </div>
          {% if machine['ip'] %}
            <p class="text-sm text-slate-600 dark:text-slate-300">IP: <code class="bg-slate-200 dark:bg-slate-800 px-2 py-1 rounded">{{ machine['ip'] }}</code></p>
          {% endif %}
        </div>
        <div class="flex gap-2">
          <a href="{{ url_for('edit_htb', id=machine['id']) }}" class="px-3 py-2 rounded-xl bg-amber-500 text-white text-sm lift">Editar</a>
          <a href="{{ url_for('delete_htb', id=machine['id']) }}" class="px-3 py-2 rounded-xl bg-rose-600 text-white text-sm lift" onclick="return confirm('¿Eliminar esta máquina?');">Eliminar</a>
        </div>
      </div>
    </div>
  {% else %}
    <div class="text-slate-600 dark:text-slate-300">No hay máquinas registradas. ¡Añade la primera!</div>
  {% endfor %}
</div>
{% endblock %}
"""

    add_htb_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="max-w-3xl mx-auto glass rounded-3xl p-8 border border-white/20">
  <h2 class="text-2xl md:text-3xl font-extrabold mb-6">Añadir máquina HTB</h2>
  {% if error %}<div class="mb-4 px-3 py-2 rounded-lg bg-rose-100/70 text-rose-700 dark:text-rose-100">{{ error }}</div>{% endif %}
  <form method="post" class="space-y-5" data-hotkey="submit">
    <div>
      <label class="block text-sm mb-1">Nombre</label>
      <input name="name" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" />
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label class="block text-sm mb-1">Dificultad</label>
        <select name="difficulty" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow">
          <option value="Fácil">Fácil</option>
          <option value="Media">Media</option>
          <option value="Difícil">Difícil</option>
          <option value="Insana">Insana</option>
        </select>
      </div>
      <div>
        <label class="block text-sm mb-1">Sistema Operativo</label>
        <select name="os" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow">
          <option value="Linux">Linux</option>
          <option value="Windows">Windows</option>
        </select>
      </div>
    </div>
    <div>
      <label class="block text-sm mb-1">Dirección IP (opcional)</label>
      <input name="ip" class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" />
    </div>
    <div>
      <label class="block text-sm mb-1">Estado</label>
      <select name="status" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow">
        <option value="Activa">Activa</option>
        <option value="Retirada">Retirada</option>
      </select>
    </div>
    <button class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-500 lift">Guardar máquina</button>
  </form>
</div>
{% endblock %}
"""

    edit_htb_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="max-w-3xl mx-auto glass rounded-3xl p-8 border border-white/20">
  <h2 class="text-2xl md:text-3xl font-extrabold mb-6">Editar máquina HTB</h2>
  {% if error %}<div class="mb-4 px-3 py-2 rounded-lg bg-rose-100/70 text-rose-700 dark:text-rose-100">{{ error }}</div>{% endif %}
  <form method="post" class="space-y-5" data-hotkey="submit">
    <div>
      <label class="block text-sm mb-1">Nombre</label>
      <input name="name" value="{{ machine['name'] }}" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" />
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label class="block text-sm mb-1">Dificultad</label>
        <select name="difficulty" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow">
          <option value="Fácil" {% if machine['difficulty'] == 'Fácil' %}selected{% endif %}>Fácil</option>
          <option value="Media" {% if machine['difficulty'] == 'Media' %}selected{% endif %}>Media</option>
          <option value="Difícil" {% if machine['difficulty'] == 'Difícil' %}selected{% endif %}>Difícil</option>
          <option value="Insana" {% if machine['difficulty'] == 'Insana' %}selected{% endif %}>Insana</option>
        </select>
      </div>
      <div>
        <label class="block text-sm mb-1">Sistema Operativo</label>
        <select name="os" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow">
          <option value="Linux" {% if machine['os'] == 'Linux' %}selected{% endif %}>Linux</option>
          <option value="Windows" {% if machine['os'] == 'Windows' %}selected{% endif %}>Windows</option>
        </select>
      </div>
    </div>
    <div>
      <label class="block text-sm mb-1">Dirección IP (opcional)</label>
      <input name="ip" value="{{ machine['ip'] or '' }}" class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow" />
    </div>
    <div>
      <label class="block text-sm mb-1">Estado</label>
      <select name="status" required class="w-full px-4 py-3 rounded-xl border border-slate-300/70 dark:border-white/10 bg-white/80 dark:bg-white/5 focus-glow">
        <option value="Activa" {% if machine['status'] == 'Activa' %}selected{% endif %}>Activa</option>
        <option value="Retirada" {% if machine['status'] == 'Retirada' %}selected{% endif %}>Retirada</option>
      </select>
    </div>
    <button class="px-5 py-3 rounded-xl font-bold text-white bg-amber-500 hover:bg-amber-600 lift">Guardar cambios</button>
  </form>
</div>
{% endblock %}
"""

    not_found_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="min-h-[60vh] grid place-items-center text-center">
  <div>
    <div class="text-7xl font-black text-rose-500 mb-2">404</div>
    <h2 class="text-2xl md:text-3xl font-extrabold mb-2">Página no encontrada</h2>
    <p class="text-slate-600 dark:text-slate-300 mb-6">La ruta solicitada no existe o fue movida.</p>
    <a href="{{ url_for('dashboard') }}" class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-600 to-purple-600 lift">Volver al panel</a>
  </div>
</div>
{% endblock %}
"""
    error_html = r"""
{% extends 'base.html' %}
{% block content %}
<div class="min-h-[60vh] grid place-items-center text-center">
  <div>
    <div class="text-7xl font-black text-rose-500 mb-2">500</div>
    <h2 class="text-2xl md:text-3xl font-extrabold mb-2">Error interno</h2>
    <p class="text-slate-600 dark:text-slate-300 mb-6">Ups, algo falló. Inténtalo de nuevo más tarde.</p>
    <a href="{{ url_for('dashboard') }}" class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-600 to-purple-600 lift">Volver al panel</a>
  </div>
</div>
{% endblock %}
"""
    ensure_dirs()
    write_file(os.path.join(STATIC_DIR, "style.css"), style_css)
    # Templates
    write_file(os.path.join(TEMPLATES_DIR, "base.html"), base_html)
    write_file(os.path.join(TEMPLATES_DIR, "login.html"), login_html)
    write_file(os.path.join(TEMPLATES_DIR, "register.html"), register_html)
    write_file(os.path.join(TEMPLATES_DIR, "dashboard.html"), dashboard_html)
    write_file(os.path.join(TEMPLATES_DIR, "threads.html"), threads_html)
    write_file(os.path.join(TEMPLATES_DIR, "thread_detail.html"), thread_detail_html)
    write_file(os.path.join(TEMPLATES_DIR, "create_thread.html"), create_thread_html)
    write_file(os.path.join(TEMPLATES_DIR, "edit_thread.html"), edit_thread_html)
    write_file(os.path.join(TEMPLATES_DIR, "profile.html"), profile_html)
    write_file(os.path.join(TEMPLATES_DIR, "htb.html"), htb_html)
    write_file(os.path.join(TEMPLATES_DIR, "add_htb.html"), add_htb_html)
    write_file(os.path.join(TEMPLATES_DIR, "edit_htb.html"), edit_htb_html)
    write_file(os.path.join(TEMPLATES_DIR, "404.html"), not_found_html)
    write_file(os.path.join(TEMPLATES_DIR, "500.html"), error_html)

# --------------- Routes ---------------
@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("user") else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        if user and check_password_hash(user[2], password):
            session["user"] = username
            flash("Has iniciado sesión.", "success")
            return redirect(url_for("dashboard"))
        else:
            error = "Credenciales incorrectas"
    return render_template("login.html", error=error, title="Login")

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        raw_pass = request.form.get("password", "")
        if len(raw_pass) < 6:
            error = "La contraseña debe tener al menos 6 caracteres"
        elif not username:
            error = "El usuario es obligatorio"
        else:
            try:
                db = get_db()
                cur = db.cursor()
                cur.execute(
                    "INSERT INTO users(username, password) VALUES (?,?)",
                    (username, generate_password_hash(raw_pass)),
                )
                db.commit()
                flash("Cuenta creada. Ya puedes iniciar sesión.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "El usuario ya existe"
    return render_template("register.html", error=error, title="Registro")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Sesión cerrada.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect(url_for("login"))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM threads")
    threads = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM replies")
    replies = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM htb_machines")
    htb_machines = cur.fetchone()[0]
    return render_template(
        "dashboard.html", 
        user=session["user"], 
        stats={
            "users": users, 
            "threads": threads, 
            "replies": replies,
            "htb_machines": htb_machines
        }, 
        title="Dashboard"
    )

@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    success = None
    error = None
    
    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if new_password != confirm_password:
            error = "Las contraseñas no coinciden"
        elif len(new_password) < 6:
            error = "La contraseña debe tener al menos 6 caracteres"
        else:
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "UPDATE users SET password=? WHERE username=?",
                (generate_password_hash(new_password), user)
            )
            db.commit()
            success = "Contraseña actualizada correctamente"
    
    return render_template(
        "profile.html",
        user=user,
        success=success,
        error=error,
        title="Perfil"
    )

@app.route("/threads")
def threads():
    if not session.get("user"):
        return redirect(url_for("login"))
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT t.*, COUNT(r.id) AS reply_count
        FROM threads t
        LEFT JOIN replies r ON r.thread_id = t.id
        GROUP BY t.id
        ORDER BY t.id DESC
        """
    )
    rows = cur.fetchall()
    return render_template("threads.html", threads=rows, title="Hilos")

@app.route("/thread/<int:id>", methods=["GET", "POST"])
def thread_detail(id: int):
    if not session.get("user"):
        return redirect(url_for("login"))
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        content = (request.form.get("content") or "").strip()
        if content:
            cur.execute(
                "INSERT INTO replies(content, author, thread_id, created_at) VALUES (?,?,?,?)",
                (content, session["user"], id, datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
            )
            db.commit()
            flash("Respuesta publicada.", "success")
            return redirect(url_for("thread_detail", id=id))
    cur.execute("SELECT * FROM threads WHERE id=?", (id,))
    thread = cur.fetchone()
    if not thread:
        abort(404)
    cur.execute("SELECT * FROM replies WHERE thread_id=? ORDER BY id ASC", (id,))
    replies = cur.fetchall()
    return render_template("thread_detail.html", thread=thread, replies=replies, title=thread[1])

@app.route("/create_thread", methods=["GET", "POST"])
def create_thread():
    if not session.get("user"):
        return redirect(url_for("login"))
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        if title and content:
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "INSERT INTO threads(title, content, author, created_at) VALUES (?,?,?,?)",
                (title, content, session["user"], datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
            )
            db.commit()
            flash("Hilo creado.", "success")
            return redirect(url_for("threads"))
        else:
            flash("El título y el contenido no pueden estar vacíos.", "error")
    return render_template("create_thread.html", title="Nuevo hilo")

@app.route("/edit_thread/<int:id>", methods=["GET", "POST"])
def edit_thread(id: int):
    if not session.get("user"):
        return redirect(url_for("login"))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM threads WHERE id=?", (id,))
    thread = cur.fetchone()
    if not thread or thread[3] != session["user"]:
        abort(404)
    error = None
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        if title and content:
            cur.execute("UPDATE threads SET title=?, content=? WHERE id=?", (title, content, id))
            db.commit()
            flash("Cambios guardados.", "success")
            return redirect(url_for("thread_detail", id=id))
        else:
            error = "El título y el contenido no pueden estar vacíos."
    return render_template("edit_thread.html", thread=thread, error=error, title="Editar hilo")

@app.route("/delete_thread/<int:id>")
def delete_thread(id: int):
    if not session.get("user"):
        return redirect(url_for("login"))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM threads WHERE id=?", (id,))
    thread = cur.fetchone()
    if not thread or thread[3] != session["user"]:
        abort(404)
    cur.execute("DELETE FROM replies WHERE thread_id=?", (id,))
    cur.execute("DELETE FROM threads WHERE id=?", (id,))
    db.commit()
    flash("Hilo eliminado.", "success")
    return redirect(url_for("threads"))

@app.route("/delete_reply/<int:id>")
def delete_reply(id: int):
    if not session.get("user"):
        return redirect(url_for("login"))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM replies WHERE id=?", (id,))
    reply = cur.fetchone()
    if not reply or reply[2] != session["user"]:
        abort(404)
    thread_id = reply[3]
    cur.execute("DELETE FROM replies WHERE id=?", (id,))
    db.commit()
    flash("Respuesta eliminada.", "success")
    return redirect(url_for("thread_detail", id=thread_id))

# Rutas para HTB
@app.route("/htb")
def htb():
    if not session.get("user"):
        return redirect(url_for("login"))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM htb_machines ORDER BY name")
    machines = cur.fetchall()
    return render_template("htb.html", machines=machines, title="Máquinas HTB")

@app.route("/add_htb", methods=["GET", "POST"])
def add_htb():
    if not session.get("user"):
        return redirect(url_for("login"))
    
    # Verificar si el usuario es admin
    if session.get("user") != "admin":
        flash("Solo el administrador puede añadir máquinas.", "error")
        return redirect(url_for("htb"))
    
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        difficulty = request.form.get("difficulty")
        os = request.form.get("os")
        ip = (request.form.get("ip") or "").strip()
        status = request.form.get("status")
        
        if name and difficulty and os and status:
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "INSERT INTO htb_machines(name, difficulty, os, ip, status) VALUES (?,?,?,?,?)",
                (name, difficulty, os, ip if ip else None, status)
            )
            db.commit()
            flash("Máquina añadida correctamente.", "success")
            return redirect(url_for("htb"))
        else:
            flash("Todos los campos obligatorios deben ser completados.", "error")
    
    return render_template("add_htb.html", title="Añadir máquina HTB")

@app.route("/edit_htb/<int:id>", methods=["GET", "POST"])
def edit_htb(id: int):
    if not session.get("user"):
        return redirect(url_for("login"))
    
    # Verificar si el usuario es admin
    if session.get("user") != "admin":
        flash("Solo el administrador puede editar máquinas.", "error")
        return redirect(url_for("htb"))
    
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM htb_machines WHERE id=?", (id,))
    machine = cur.fetchone()
    
    if not machine:
        abort(404)
    
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        difficulty = request.form.get("difficulty")
        os = request.form.get("os")
        ip = (request.form.get("ip") or "").strip()
        status = request.form.get("status")
        
        if name and difficulty and os and status:
            cur.execute(
                "UPDATE htb_machines SET name=?, difficulty=?, os=?, ip=?, status=? WHERE id=?",
                (name, difficulty, os, ip if ip else None, status, id)
            )
            db.commit()
            flash("Máquina actualizada correctamente.", "success")
            return redirect(url_for("htb"))
        else:
            flash("Todos los campos obligatorios deben ser completados.", "error")
    
    return render_template("edit_htb.html", machine=machine, title="Editar máquina HTB")

@app.route("/delete_htb/<int:id>")
def delete_htb(id: int):
    if not session.get("user"):
        return redirect(url_for("login"))
    
    # Verificar si el usuario es admin
    if session.get("user") != "admin":
        flash("Solo el administrador puede eliminar máquinas.", "error")
        return redirect(url_for("htb"))
    
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM htb_machines WHERE id=?", (id,))
    db.commit()
    flash("Máquina eliminada correctamente.", "success")
    return redirect(url_for("htb"))
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))