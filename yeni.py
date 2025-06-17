# -*- coding: utf-8 -*-
"""
Multi‐page Flask + Supabase dashboard nümunəsi.
Hər səhifə (route) üçün ayrıca kartlar və diaqramlar,
və hər birində tarix aralığı seçimi mövcuddur.
"""

import os
from datetime import datetime, date
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, flash, redirect, url_for
from supabase import create_client, Client
from postgrest import APIError
from flask import Flask, request, jsonify, render_template_string, session, flash, redirect, url_for


app = Flask(__name__)

# ---------------------------------------------
# 0) CONSTANTS — hamısını burda saxla
# ---------------------------------------------
app.secret_key      = "516c2d519f41c3d864340d506dafabea0cc60337196631cf061799a6f8f766db"  # sessiya üçün
SUPABASE_URL        = "https://toetwtgzozlvvmsnodqn.supabase.co"
SUPABASE_ANON_KEY   = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRvZXR3dGd6b3psdnZtc25vZHFuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTAyNTM1NCwiZXhwIjoyMDY0NjAxMzU0fQ.yQmYTk2t0GcuWJpEukQkvEz7SUpRTHMW86Le4CjCsVc"

# Supabase client with anon key (auth üçün lazım)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --- REGISTER ---
def login_required(f):
    @wraps(f)
    def deco(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return deco

# ---------------------------------------------
# 2) /register
# ---------------------------------------------
@app.route("/register", methods=["GET","POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home"))

    html = r"""
<!DOCTYPE html><html lang="az"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Qeydiyyat</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-100 p-8">
  <div class="max-w-md mx-auto bg-white p-6 rounded shadow">
    <h1 class="text-2xl mb-4">Qeydiyyat</h1>
    {% with msgs = get_flashed_messages(with_categories=true) %}
      {% for cat,msg in msgs %}<div class="mb-2 text-{{'green' if cat=='success' else 'red'}}">{{msg}}</div>{% endfor %}
    {% endwith %}
    <form method="post" class="space-y-4">
      <input name="full_name" type="text" placeholder="Tam Ad"    class="w-full p-2 border rounded" required/>
      <input name="username"  type="text" placeholder="İstifadəçi adı" class="w-full p-2 border rounded" required/>
      <input name="password"  type="password" placeholder="Şifrə"   class="w-full p-2 border rounded" required/>
      <button type="submit" class="w-full bg-indigo-600 text-white p-2 rounded">Qeydiyyat</button>
    </form>
    <p class="mt-4 text-center">Hesabın var? <a href="{{ url_for('login') }}" class="text-indigo-600">Daxil ol</a></p>
  </div>
</body></html>
"""
    if request.method=="POST":
        fn = request.form["full_name"]
        un = request.form["username"]
        pw = request.form["password"]
        # İstifadəçi mövcuddurmu yoxla
        existing = supabase.table("users").select("id").eq("username", un).execute().data
        if existing:
            flash("Bu istifadəçi adı artıq var.", "danger")
        else:
            supabase.table("users").insert({
                "full_name": fn,
                "username": un,
                "password": pw
            }).execute()
            flash("Qeydiyyat uğurlu oldu.", "success")
            return redirect(url_for("login"))
    return render_template_string(html)

# --- Login ---
@app.route("/login", methods=["GET","POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    html = r"""
<!DOCTYPE html><html lang="az"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Daxil ol</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-100 p-8">
  <div class="max-w-md mx-auto bg-white p-6 rounded shadow">
    <h1 class="text-2xl mb-4">Daxil ol</h1>
    {% with msgs = get_flashed_messages(with_categories=true) %}
      {% for cat,msg in msgs %}<div class="mb-2 text-{{'green' if cat=='success' else 'red'}}">{{msg}}</div>{% endfor %}
    {% endwith %}
    <form method="post" class="space-y-4">
      <input name="username" type="text" placeholder="İstifadəçi adı" class="w-full p-2 border rounded" required/>
      <input name="password" type="password" placeholder="Şifrə" class="w-full p-2 border rounded" required/>
      <button type="submit" class="w-full bg-green-600 text-white p-2 rounded">Daxil ol</button>
    </form>
    <p class="mt-4 text-center">Hesabın yoxdur? <a href="{{ url_for('register') }}" class="text-indigo-600">Qeydiyyat</a></p>
  </div>
</body></html>
"""
    if request.method=="POST":
        un = request.form["username"]
        pw = request.form["password"]
        user = supabase.table("users") \
            .select("id, full_name, password") \
            .eq("username", un).single().execute().data
        if user and user.get("password")==pw:
            session["user_id"]   = user["id"]
            session["full_name"] = user["full_name"]
            return redirect(url_for("home"))
        flash("İstifadəçi adı və ya şifrə səhvdir.", "danger")
    return render_template_string(html)

# --- Logout ---
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
  
  
  



# ---------------------------------------------
# 2) Köməkçi funksiya: start_date & end_date
# ---------------------------------------------
def _get_date_range():
    """
    ?start_date=YYYY-MM-DD & ?end_date=YYYY-MM-DD query parametrini oxuyur.
    Default: bu ayın 1-i → bu gün.
    """
    today = date.today()
    default_start = today.replace(day=1).isoformat()
    default_end = today.isoformat()
    requested_start = request.args.get("start_date", None)
    requested_end = request.args.get("end_date", None)
    if requested_start:
        default_start = requested_start
    if requested_end:
        default_end = requested_end
    return default_start, default_end
  
@app.route("/")
@login_required
def home():
    html = r"""
<!DOCTYPE html>
<html lang="az" class="transition-colors duration-300">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Manager Dashboard Ana Səhifə</title>

  <!-- favicon əlavə olundu -->
  <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='favicon.ico') }}">

  <!-- Tailwind + dark mode konfiqurasiyası -->
  <script src="https://cdn.tailwindcss.com?plugins=forms,typography"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: { extend: {} }
    }
  </script>
  <script src="https://unpkg.com/feather-icons"></script>
</head>
<body class="bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100">
  <nav class="bg-white dark:bg-gray-800 shadow-md">
    <div class="container mx-auto px-4 py-4 flex justify-between items-center">
      <h1 class="text-2xl font-semibold">🚀 Manager Dashboard</h1>
      <button id="theme-toggle" class="p-2 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-transform transform hover:scale-110">
        <i data-feather="moon"></i>
      </button>
    </div>
  </nav>

  <main class="container mx-auto px-4 py-8">
    <h2 class="text-xl font-medium mb-6 text-center">🏠 Ana Səhifə</h2>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-8">
      {% set cards = [
        ('Technician Status Dashboard','status','bar-chart-2','Hər texnik üçün status paylanması','🔧'),
        ('Average Duration Dashboard','duration','clock','Texniklərin orta xidmət vaxtları','⏱️'),
        ('Equipment Stats Dashboard','equipment','tool','Avadanlıq istifadəsi və xərcləri','🛠️'),
        ('Profit Report Dashboard','profit','dollar-sign','Texniklərin gəlir‑xərc','💰'),
      ] %}
      {% for title, endpoint, icon, desc, emoji in cards %}
      <a href="{{ url_for(endpoint + '_dashboard') }}"
         class="group block bg-white dark:bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-transform transform hover:scale-105 p-8">
        <div class="flex items-center space-x-4">
          <div class="p-4 bg-indigo-100 dark:bg-indigo-200 rounded-lg transition-transform transform group-hover:scale-110">
            <span class="text-4xl">{{ emoji }}</span>
          </div>
          <div>
            <h3 class="text-lg font-semibold group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">{{ title }}</h3>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ desc }}</p>
          </div>
        </div>
      </a>
      {% endfor %}
    </div>
  </main>

  <script>
    document.addEventListener('DOMContentLoaded', () => {
      feather.replace();
      if (localStorage.getItem('theme') === 'dark') {
        document.documentElement.classList.add('dark');
      }
      const btn = document.getElementById('theme-toggle');
      btn.addEventListener('click', () => {
        document.documentElement.classList.toggle('dark');
        localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
      });
    });
  </script>
</body>
</html>
    """
    return render_template_string(html)

# ---------------------------------------------
# 4) Technician Status Dashboard
# ---------------------------------------------
@app.route("/status")
@login_required
def status_dashboard():
    html = r"""
<!DOCTYPE html>
<html lang="az" class="transition-colors">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Technician Status Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/feather-icons"></script>
</head>
<body class="bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100">
  <nav class="bg-white dark:bg-gray-800 shadow-md">
    <div class="container mx-auto px-6 py-4 flex justify-between items-center">
      <h1 class="text-2xl font-semibold">Technician Status</h1>
      <div class="flex items-center space-x-4">
        <button id="theme-toggle" class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition">
          <i data-feather="moon"></i>
        </button>
      </div>
    </div>
  </nav>

  <main class="container mx-auto px-6 py-8 space-y-8">
    <!-- Filter -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div>
        <label for="startDate" class="block text-sm font-medium mb-1">Başlanğıc Tarix</label>
        <input type="date" id="startDate" class="w-full px-3 py-2 border rounded-lg focus:ring-indigo-500 focus:border-indigo-500 transition" />
      </div>
      <div>
        <label for="endDate" class="block text-sm font-medium mb-1">Son Tarix</label>
        <input type="date" id="endDate" class="w-full px-3 py-2 border rounded-lg focus:ring-indigo-500 focus:border-indigo-500 transition" />
      </div>
      <div class="flex items-end">
        <button id="btnRefresh" class="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition">
          Yenilə
        </button>
      </div>
    </div>

    <!-- Metrics -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow hover:shadow-lg transition">
        <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Ümumi Technician</h3>
        <p id="totalTech" class="mt-2 text-3xl font-bold">--</p>
      </div>
      <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow hover:shadow-lg transition">
        <h3 class="text-sm font-medium text-green-600">Uğurla tamamlandı</h3>
        <p id="sumSuccess" class="mt-2 text-3xl font-bold">--</p>
      </div>
      <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow hover:shadow-lg transition">
        <h3 class="text-sm font-medium text-red-600">Uğursuz oldu</h3>
        <p id="sumFailed" class="mt-2 text-3xl font-bold">--</p>
      </div>
    </div>

    <!-- Chart -->
    <!-- Chart (Centered & Smaller) -->
    <section class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow max-w-md mx-auto">
      <h2 class="text-lg font-semibold mb-4 text-center">Status Paylanması</h2>
      <div class="flex justify-center">
        <canvas id="statusChart" class="w-full h-48"></canvas>
      </div>
    </section>

    <!-- Table -->
    <section class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow">
      <h2 class="text-lg font-semibold mb-4">Detallı Technician Status</h2>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">#</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Adı</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-green-600 uppercase">Uğurla</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-red-600 uppercase">Uğursuz</th>
            </tr>
          </thead>
          <tbody id="statusTable" class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <!-- JS will inject rows here -->
          </tbody>
        </table>
      </div>
    </section>
  </main>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    feather.replace();
    const toggle = document.getElementById('theme-toggle');
    toggle.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
    });

    function buildUrl(endpoint) {
      const base = window.location.origin;
      const start = document.getElementById("startDate").value;
      const end = document.getElementById("endDate").value;
      let q = start ? `start_date=${start}` : "";
      q += end ? `${q ? '&' : ''}end_date=${end}` : "";
      return `${base}/api/${endpoint}${q ? '?' + q : ''}`;
    }

    async function loadStatusMetrics() {
      const res = await fetch(buildUrl("technician-status"));
      const data = await res.json();
      document.getElementById("totalTech").innerText = data.length;
      let s=0,f=0,p=0;
      data.forEach(r=>{ s+=r.success_count; f+=r.failed_count; p+=r.stopped_count; });
      document.getElementById("sumSuccess").innerText = s;
      document.getElementById("sumFailed").innerText = f;
      document.getElementById("sumStopped").innerText = p;
    }

    async function loadStatusChart() {
      const res = await fetch(buildUrl("technician-status"));
      const data = await res.json();
      let s=0,f=0,p=0; data.forEach(r=>{ s+=r.success_count; f+=r.failed_count; p+=r.stopped_count; });
      new Chart(document.getElementById("statusChart"), {
        type: 'pie',
        data: {
          labels: ['Uğurla tamamlandı','Uğursuz oldu'],
          datasets:[{ data:[s,f,p] }]
        },
        options:{ responsive:true, plugins:{ legend:{ position:'bottom' } } }
      });
    }

    async function loadStatusTable() {
      const res = await fetch(buildUrl("technician-status"));
      const data = await res.json();
      const tbody = document.getElementById("statusTable");
      tbody.innerHTML = "";
      data.forEach((r,i)=> {
        tbody.innerHTML += `
          <tr class="hover:bg-gray-100 dark:hover:bg-gray-700">
            <td class="px-4 py-2">${i+1}</td>
            <td class="px-4 py-2">${r.full_name}</td>
            <td class="px-4 py-2">${r.success_count}</td>
            <td class="px-4 py-2">${r.failed_count}</td>
            <td class="px-4 py-2">${r.stopped_count}</td>
          </tr>`;
      });
    }

    document.addEventListener("DOMContentLoaded", () => {
      const today = new Date().toISOString().split("T")[0];
      document.getElementById("startDate").value = today.replace(/-.+$/, "-01");
      document.getElementById("endDate").value = today;
      loadStatusMetrics();
      loadStatusChart();
      loadStatusTable();
    });
    document.getElementById("btnRefresh").addEventListener("click", () => {
      loadStatusMetrics();
      loadStatusChart();
      loadStatusTable();
    });
  </script>
</body>
</html>
    """
    return render_template_string(html)

# ---------------------------------------------
# 5) Average Duration Dashboard
# ---------------------------------------------
@app.route("/duration")
@login_required
def duration_dashboard():
    html = r"""
<!DOCTYPE html>
<html lang="az">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Average Duration Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { background-color: #f0f2f5; padding-top: 2rem; }
    .card { border-radius: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .card-header { background-color: #0d6efd; color: white; font-weight: 600; border-top-left-radius: 1rem; border-top-right-radius: 1rem; }
    .metric { font-size: 2rem; font-weight: bold; }
    .chart-container { position: relative; height: 200px; }
  </style>
</head>
<body>
  <div class="container">
    <h1 class="mb-4 text-center">Average Duration Dashboard</h1>

    <!-- Tarix aralığı filtri -->
    <div class="row g-3 mb-4 justify-content-center">
      <div class="col-md-3">
        <label for="startDate" class="form-label">Başlanğıc Tarix:</label>
        <input type="date" id="startDate" class="form-control" />
      </div>
      <div class="col-md-3">
        <label for="endDate" class="form-label">Son Tarix:</label>
        <input type="date" id="endDate" class="form-control" />
      </div>
      <div class="col-md-2 align-self-end">
        <button id="btnRefresh" class="btn btn-primary w-100">Yenilə</button>
      </div>
    </div>

    <!-- Kartlar: Ortalama Vaxt -->
    <div class="row g-4 mb-4">
      <div class="col-md-4">
        <div class="card text-center p-3">
          <div class="card-header">Ən Az Ortalama Vaxt</div>
          <div class="card-body">
            <div id="minAvgTech" class="metric">--</div>
            <div>Texnik və Dəq</div>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card text-center p-3">
          <div class="card-header">Ən Yüksək Ortalama Vaxt</div>
          <div class="card-body">
            <div id="maxAvgTech" class="metric">--</div>
            <div>Texnik və Dəq</div>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card text-center p-3">
          <div class="card-header">Ortalama Dəqiqə (Bütün Texniklər)</div>
          <div class="card-body">
            <div id="avgOfAvgs" class="metric">--</div>
            <div>Dəq</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Centered, compact chart card -->
    <div class="row justify-content-center mb-4">
      <div class="col-md-6">
        <div class="card">
          <div class="card-header text-center">Top 5 Ortalama Vaxt (Bar Diaqram)</div>
          <div class="card-body">
            <div class="chart-container">
              <canvas id="durationChart"></canvas>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Detallı Cədvəl -->
    <div class="card mb-4">
      <div class="card-header">Detallı Average Duration Cədvəli</div>
      <div class="card-body">
        <div class="table-responsive">
          <table class="table table-hover align-middle" id="durationTable">
            <thead class="table-light">
              <tr>
                <th>#</th>
                <th>Adı</th>
                <th>Orta Vaxt (dəq)</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>

  </div>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    function buildUrl(endpoint) {
      const base = window.location.origin;
      const start = document.getElementById("startDate").value;
      const end = document.getElementById("endDate").value;
      let q = "";
      if (start) q += `start_date=${start}`;
      if (end) {
        if (q.length) q += "&";
        q += `end_date=${end}`;
      }
      return q.length ? `${base}/api/${endpoint}?${q}` : `${base}/api/${endpoint}`;
    }

    async function loadDurationMetrics() {
      const res = await fetch(buildUrl("avg-duration"));
      const data = await res.json();
      if (!data.length) return;
      data.sort((a, b) => a.avg_duration_min - b.avg_duration_min);
      const min = data[0];
      const max = data[data.length - 1];
      document.getElementById("minAvgTech").innerText = `${min.full_name}: ${min.avg_duration_min}`;
      document.getElementById("maxAvgTech").innerText = `${max.full_name}: ${max.avg_duration_min}`;
      const avgAll = (data.reduce((sum, r) => sum + r.avg_duration_min, 0) / data.length).toFixed(2);
      document.getElementById("avgOfAvgs").innerText = avgAll;
    }

    async function loadDurationChart() {
      const res = await fetch(buildUrl("avg-duration"));
      const data = await res.json();
      data.sort((a, b) => b.avg_duration_min - a.avg_duration_min);
      const top5 = data.slice(0, 5);
      const labels = top5.map(r => r.full_name);
      const values = top5.map(r => r.avg_duration_min);
      const ctx = document.getElementById("durationChart").getContext("2d");
      new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Orta Vaxt (dəq)', data: values, backgroundColor: '#0d6efd' }] },
        options: { indexAxis: 'y', responsive: true, scales: { x: { beginAtZero: true } }, plugins: { legend: { display: false } } }
      });
    }

    async function loadDurationTable() {
      const res = await fetch(buildUrl("avg-duration"));
      const data = await res.json();
      const tbody = document.querySelector("#durationTable tbody");
      tbody.innerHTML = "";
      data.forEach((row, idx) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${idx + 1}</td>
          <td>${row.full_name}</td>
          <td>${row.avg_duration_min}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    document.addEventListener("DOMContentLoaded", () => {
      const today = new Date().toISOString().split("T")[0];
      document.getElementById("startDate").value = today.replace(/-.+$/, "-01");
      document.getElementById("endDate").value = today;
      loadDurationMetrics();
      loadDurationChart();
      loadDurationTable();
    });

    document.getElementById("btnRefresh").addEventListener("click", () => {
      loadDurationMetrics();
      loadDurationChart();
      loadDurationTable();
    });
  </script>
</body>
</html>
    """
    return render_template_string(html)


# ---------------------------------------------
# 6) Equipment Stats Dashboard
# ---------------------------------------------
@app.route("/equipment")
@login_required
def equipment_dashboard():
    html = r"""
<!DOCTYPE html>
<html lang="az">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Equipment Stats Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { background-color: #f0f2f5; padding-top: 2rem; }
    .card { border-radius: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }
    .card-header { background-color: #0d6efd; color: white; font-weight: 600; border-top-left-radius: 1rem; border-top-right-radius: 1rem; }
    .metric { font-size: 2rem; font-weight: bold; }
    .chart-container { position: relative; height: 200px; }
  </style>
</head>
<body>
  <div class="container">
    <h1 class="mb-4 text-center">Equipment Stats Dashboard</h1>


    <!-- Tarix aralığı filtri -->
    <div class="row g-3 mb-4 justify-content-center">
      <div class="col-md-3">
        <label for="startDate" class="form-label">Başlanğıc Tarix:</label>
        <input type="date" id="startDate" class="form-control" />
      </div>
      <div class="col-md-3">
        <label for="endDate" class="form-label">Son Tarix:</label>
        <input type="date" id="endDate" class="form-control" />
      </div>
      <div class="col-md-2 align-self-end">
        <button id="btnRefresh" class="btn btn-primary w-100">Yenilə</button>
      </div>
    </div>

    <!-- Top 3 equipment cards -->
    <div class="row g-4 mb-4">
      {% for i in range(1,4) %}
      <div class="col-md-4">
        <div class="card text-center p-3">
          <div class="card-header">Ən Yüksək Xərc ({{ i }})</div>
          <div class="card-body">
            <div id="top{{ i }}" class="metric">--</div>
            <div>Manat</div>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>

    <!-- Centered compact chart -->
    <div class="row justify-content-center mb-4">
      <div class="col-md-6">
        <div class="card">
          <div class="card-header text-center">Top 5 Equipment İstifadəsi (Bar Diaqram)</div>
          <div class="card-body">
            <div class="chart-container">
              <canvas id="equipmentChart"></canvas>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Detallı Table -->
    <div class="card mb-4">
      <div class="card-header">Detallı Equipment Stats Cədvəli</div>
      <div class="card-body">
        <div class="table-responsive">
          <table class="table table-hover align-middle" id="equipmentTable">
            <thead class="table-light">
              <tr>
                <th>#</th>
                <th>Adı</th>
                <th>Ümumi Miqdar</th>
                <th>Ümumi Xərc</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>

  </div>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    function buildUrl(endpoint) {
      const base = window.location.origin;
      const start = document.getElementById("startDate").value;
      const end = document.getElementById("endDate").value;
      let q = "";
      if (start) q += `start_date=${start}`;
      if (end) { q += q? '&' : ''; q += `end_date=${end}`; }
      return q? `${base}/api/${endpoint}?${q}` : `${base}/api/${endpoint}`;
    }

    async function loadEquipmentMetrics() {
      const res = await fetch(buildUrl("equipment-stats"));
      const data = await res.json();
      data.sort((a,b)=>b.total_cost-a.total_cost);
      const top=data.slice(0,3);
      top.forEach((r,i)=>document.getElementById(`top${i+1}`).innerText = `${r.equipment_name}: ${r.total_cost}`);
    }

    async function loadEquipmentChart() {
      const res = await fetch(buildUrl("equipment-stats"));
      const data = await res.json();
      data.sort((a,b)=>b.total_quantity-a.total_quantity);
      const top5=data.slice(0,5);
      const labels=top5.map(r=>r.equipment_name);
      const values=top5.map(r=>r.total_quantity);
      new Chart(document.getElementById("equipmentChart").getContext("2d"),{
        type:'bar',data:{labels,datasets:[{data:values}]},
        options:{indexAxis:'y',responsive:true,scales:{x:{beginAtZero:true}},plugins:{legend:{display:false}}}
      });
    }

    async function loadEquipmentTable() {
      const res = await fetch(buildUrl("equipment-stats"));
      const data = await res.json();
      const tbody=document.querySelector('#equipmentTable tbody');tbody.innerHTML='';
      data.forEach((r,i)=>{
        const tr=document.createElement('tr');
        tr.innerHTML=`<td>${i+1}</td><td>${r.equipment_name}</td><td>${r.total_quantity}</td><td>${r.total_cost}</td>`;
        tbody.appendChild(tr);
      });
    }

    document.addEventListener('DOMContentLoaded',()=>{
      const today=new Date().toISOString().split('T')[0];
      document.getElementById('startDate').value=today.replace(/-.+$/, '-01');
      document.getElementById('endDate').value=today;
      loadEquipmentMetrics();loadEquipmentChart();loadEquipmentTable();
    });
    document.getElementById('btnRefresh').addEventListener('click',()=>{loadEquipmentMetrics();loadEquipmentChart();loadEquipmentTable();});
  </script>
</body>
</html>
    """
    return render_template_string(html)


# ---------------------------------------------
# 7) Profit Report Dashboard
# ---------------------------------------------
@app.route("/profit")
@login_required
def profit_dashboard():
    html = r"""
<!DOCTYPE html>
<html lang="az">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Profit Report Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <style>
    body { background-color: #f0f2f5; padding-top: 2rem; }
    .card { border-radius: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }
    .card-header { background-color: #0d6efd; color: white; font-weight: 600; border-top-left-radius: 1rem; border-top-right-radius: 1rem; }
    .metric { font-size: 2rem; font-weight: bold; }
  </style>
</head>
<body>
  <div class="container">
    <h1 class="mb-4 text-center">Profit Report Dashboard</h1>

    <!-- Tarix aralığı filtri -->
    <div class="row g-3 mb-4">
      <div class="col-md-3">
        <label for="startDate" class="form-label">Başlanğıc Tarix:</label>
        <input type="date" id="startDate" class="form-control" />
      </div>
      <div class="col-md-3">
        <label for="endDate" class="form-label">Son Tarix:</label>
        <input type="date" id="endDate" class="form-control" />
      </div>
      <div class="col-md-3 align-self-end">
        <button id="btnRefresh" class="btn btn-primary w-100">Yenilə</button>
      </div>
    </div>

    <!-- Detallı Cədvəl -->
    <div class="card mb-4">
      <div class="card-header">Detallı Profit Report Cədvəli</div>
      <div class="card-body">
        <div class="table-responsive">
          <table class="table table-hover align-middle" id="profitTable">
            <thead class="table-light">
              <tr>
                <th>#</th>
                <th>Adı</th>
                <th>Ümumi Xərc</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>

  </div>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    function buildUrl(endpoint) {
      const base = window.location.origin;
      const start = document.getElementById("startDate").value;
      const end = document.getElementById("endDate").value;
      let q = "";
      if (start) q += `start_date=${start}`;
      if (end) {
        if (q.length) q += "&";
        q += `end_date=${end}`;
      }
      return q.length ? `${base}/api/${endpoint}?${q}` : `${base}/api/${endpoint}`;
    }

    async function loadProfitTable() {
      const res = await fetch(buildUrl("technician-profit"));
      const data = await res.json();
      const tbody = document.querySelector("#profitTable tbody");
      tbody.innerHTML = "";
      data.forEach((row, idx) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${idx + 1}</td>
          <td>${row.full_name}</td>
          <td>${row.total_cost}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    document.addEventListener("DOMContentLoaded", () => {
      const today = new Date().toISOString().split("T")[0];
      const firstOfMonth = today.replace(/-.+$/, "-01");
      document.getElementById("startDate").value = firstOfMonth;
      document.getElementById("endDate").value = today;

      loadProfitTable();
    });

    document.getElementById("btnRefresh").addEventListener("click", () => {
      loadProfitTable();
    });
  </script>
</body>
</html>
    """
    return render_template_string(html)



# ---------------------------------------------
# 9) API Endpoints (mövcud kodlar)
# ---------------------------------------------

@app.route("/api/technician-status", methods=["GET"])
@login_required
def api_technician_status():
    start_date, end_date = _get_date_range()
    try:
        resp = (
            supabase.table("technician_activity")
            .select("technician_id, status, activity_date, technicians(full_name)")
            .gte("activity_date", start_date)
            .lte("activity_date", end_date)
            .execute()
        )
    except APIError as e:
        return jsonify({"error": str(e)}), 400

    rows = resp.data
    stats = {}
    for r in rows:
        tid = r["technician_id"]
        name = r.get("technicians", {}).get("full_name", "Unknown")
        status = (r.get("status") or "").strip()
        if tid not in stats:
            stats[tid] = {"technician_id": tid, "full_name": name, "success_count": 0, "failed_count": 0, "stopped_count": 0}
        if status in ["Uğurla tamamlandı", "Completed"]:
            stats[tid]["success_count"] += 1
        elif status in ["Uğursuz oldu", "Failed"]:
            stats[tid]["failed_count"] += 1

    result = sorted(stats.values(), key=lambda x: (x["success_count"] + x["failed_count"] + x["stopped_count"]), reverse=True)
    return jsonify(result), 200

@app.route("/api/avg-duration", methods=["GET"])
@login_required
def api_avg_duration():
    start_date, end_date = _get_date_range()
    try:
        resp = (
            supabase.table("technician_activity")
            .select("technician_id, activity_date, start_time, end_time, technicians(full_name)")
            .gte("activity_date", start_date)
            .lte("activity_date", end_date)
            .execute()
        )
    except APIError as e:
        return jsonify({"error": str(e)}), 400

    rows = resp.data
    durations = {}
    for r in rows:
        tid = r["technician_id"]
        name = r.get("technicians", {}).get("full_name", "Unknown")
        ad = r.get("activity_date")
        st = r.get("start_time")
        et = r.get("end_time")
        if not (ad and st and et):
            continue
        try:
            dt_start = datetime.fromisoformat(f"{ad}T{st}")
            dt_end = datetime.fromisoformat(f"{ad}T{et}")
        except ValueError:
            continue
        diff_min = (dt_end - dt_start).total_seconds() / 60.0
        if diff_min < 0:
            continue
        if tid not in durations:
            durations[tid] = {"sum_minutes": 0.0, "count": 0, "full_name": name}
        durations[tid]["sum_minutes"] += diff_min
        durations[tid]["count"] += 1

    result = []
    for tid, info in durations.items():
        if info["count"] == 0:
            continue
        avg_m = round(info["sum_minutes"] / info["count"], 2)
        result.append({"technician_id": tid, "full_name": info["full_name"], "avg_duration_min": avg_m})
    result.sort(key=lambda x: x["avg_duration_min"])
    return jsonify(result), 200

@app.route("/api/equipment-stats", methods=["GET"])
def api_equipment_stats():
    start_date, end_date = _get_date_range()
    try:
        resp_all_eq = supabase.table("equipment").select("equipment_id, name, unit_cost").execute()
    except APIError as e:
        return jsonify({"error": str(e)}), 400

    stats = {}
    for eq in resp_all_eq.data:
        eq_id = eq["equipment_id"]
        eq_name = eq.get("name", "Unknown")
        unit_cost = float(eq.get("unit_cost", 0.0) or 0.0)
        stats[eq_id] = {"equipment_name": eq_name, "unit_cost": unit_cost, "total_quantity": 0, "total_cost": 0.0}

    try:
        resp_usage = supabase.table("technician_activity_equipment") \
            .select("activity_id, equipment_id, quantity, technician_activity(activity_date)") \
            .execute()
    except APIError as e:
        return jsonify({"error": str(e)}), 400

    for r in resp_usage.data:
        act = r.get("technician_activity")
        if not act:
            continue
        ad = act.get("activity_date")
        if not ad or not (start_date <= ad <= end_date):
            continue
        eq_id = r.get("equipment_id")
        qty = float(r.get("quantity", 0) or 0.0)

        if eq_id in stats:
            stats[eq_id]["total_quantity"] += qty
            stats[eq_id]["total_cost"] += qty * stats[eq_id]["unit_cost"]

    result = []
    for eq_id, info in stats.items():
        result.append({"equipment_id": eq_id, "equipment_name": info["equipment_name"], "total_quantity": info["total_quantity"], "total_cost": round(info["total_cost"], 2)})
    result.sort(key=lambda x: x["total_quantity"], reverse=True)
    return jsonify(result), 200

@app.route("/api/current-active", methods=["GET"])
def api_current_active():
    start_date, end_date = _get_date_range()
    try:
        resp = (
            supabase.table("technician_activity")
            .select("technician_id, technicians(full_name), activity_date, start_time, paused_at, status")
            .gte("activity_date", start_date)
            .lte("activity_date", end_date)
            .order("start_time")
            .execute()
        )
    except APIError as e:
        return jsonify({"error": str(e)}), 400

    result = []
    for r in resp.data:
        result.append({
            "full_name": r.get("technicians", {}).get("full_name", "Unknown"),
            "activity_date": r["activity_date"],
            "start_time": r["start_time"],
            "paused_at": r.get("paused_at")
        })
    return jsonify(result), 200

@app.route("/api/technician-profit", methods=["GET"])
def api_technician_profit():
    start_date, end_date = _get_date_range()
    try:
        resp_act = (supabase.table("technician_activity")
                    .select("activity_id, technician_id, activity_date, start_time, end_time, technicians(base_hourly_rate, full_name)")
                    .gte("activity_date", start_date)
                    .lte("activity_date", end_date)
                    .execute())
    except APIError as e:
        return jsonify({"error": str(e)}), 400
    acts = resp_act.data

    try:
        resp_eq = supabase.table("technician_activity_equipment") \
            .select("activity_id, quantity, equipment(unit_cost)") \
            .execute()
    except APIError as e:
        return jsonify({"error": str(e)}), 400
    eq_links = resp_eq.data

    material_cost_map = {}
    for link in eq_links:
        aid = link["activity_id"]
        eq = link.get("equipment")
        if not eq:
            continue
        unit_cost = eq.get("unit_cost", 0.0) or 0.0
        qty = link.get("quantity", 0) or 0
        material_cost_map[aid] = material_cost_map.get(aid, 0.0) + qty * unit_cost

    profit_data = {}
    for a in acts:
        tid = a["technician_id"]
        tech = a.get("technicians", {})
        base_rate = tech.get("base_hourly_rate", 0.0) or 0.0
        name = tech.get("full_name", "Unknown")
        ad = a.get("activity_date")
        st = a.get("start_time")
        et = a.get("end_time")
        revenue = 0.0

        if ad and st and et:
            try:
                dt_start = datetime.fromisoformat(f"{ad}T{st}")
                dt_end = datetime.fromisoformat(f"{ad}T{et}")
            except ValueError:
                continue
            hours = max((dt_end - dt_start).total_seconds() / 3600.0, 0.0)
            labor_cost = round(hours * base_rate, 2)
        else:
            labor_cost = 0.0

        mat_cost = round(material_cost_map.get(a["activity_id"], 0.0), 2)
        total_cost = round(labor_cost + mat_cost, 2)
        net = round(revenue - total_cost, 2)

        try:
            dt_ad = datetime.fromisoformat(ad)
            month_start = dt_ad.replace(day=1).date().isoformat()
        except Exception:
            continue

        key = (tid, month_start)
        if key not in profit_data:
            profit_data[key] = {
                "technician_id": tid,
                "full_name": name,
                "month_start": month_start,
                "total_cost": 0.0,
                "total_revenue": 0.0,
                "net_profit": 0.0
            }
        profit_data[key]["total_cost"] += total_cost
        profit_data[key]["total_revenue"] += revenue
        profit_data[key]["net_profit"] += net

    result = []
    for val in profit_data.values():
        result.append({
            "technician_id": val["technician_id"],
            "full_name": val["full_name"],
            "month_start": val["month_start"],
            "total_cost": round(val["total_cost"], 2),
            "total_revenue": round(val["total_revenue"], 2),
            "net_profit": round(val["net_profit"], 2)
        })
    result.sort(key=lambda x: (x["month_start"], -x["net_profit"]))
    return jsonify(result), 200

# ---------------------------------------------
# 10) Flask app‐ı işə sal
# ---------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
