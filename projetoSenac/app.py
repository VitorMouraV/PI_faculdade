from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import Error
from datetime import datetime, date, time, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "mude-esta-chave-secreta"

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "agenda_online"

AVAILABLE_TIME_SLOTS = [
    "08:00", "09:00", "10:00", "11:00",
    "14:00", "15:00", "16:00", "17:00"
]


def get_db_connection():
    """Abre uma nova conexão com o banco MySQL."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        return conn
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None


def login_required(f):
    """Decorator simples para proteger rotas administrativas."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Faça login para acessar esta página.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


def normalize_date(value):
    """Garante que o valor seja um objeto date (não datetime nem timedelta)."""
    if isinstance(value, datetime):
        return value.date()
    return value


def normalize_time(value):
    """
    Garante que o valor seja um objeto time.
    Trata casos em que venha como datetime, timedelta ou string.
    """
    if isinstance(value, time):
        return value

    if isinstance(value, datetime):
        return value.time()

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return time(hour=hours % 24, minute=minutes, second=seconds)

    if isinstance(value, str):
        # tenta "HH:MM:SS"
        try:
            return datetime.strptime(value, "%H:%M:%S").time()
        except ValueError:
            pass
        # tenta "HH:MM"
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            pass

    # Se não for nenhum dos tipos acima, retorna como veio
    return value


@app.context_processor
def inject_now():
    """Disponibiliza o ano atual em todos os templates."""
    return {"current_year": datetime.now().year}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/agendar", methods=["GET", "POST"])
def agendar():
    conn = get_db_connection()
    if conn is None:
        flash("Erro ao conectar ao banco de dados.", "danger")
        return redirect(url_for("index"))

    # Carrega profissionais ativos para o formulário
    professionals = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, name
            FROM professionals
            WHERE active = 1
            ORDER BY name
            """
        )
        professionals = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        date_str = request.form.get("date", "").strip()
        time_str = request.form.get("time", "").strip()
        professional_id = request.form.get("professional_id", "").strip()
        service_id = request.form.get("service_id", "").strip()

        if not (name and date_str and time_str and professional_id and service_id):
            flash("Preencha nome, data, horário, profissional e módulo.", "danger")
            return redirect(url_for("agendar"))

        try:
            appointment_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            flash("Data inválida. Use o formato dd/mm/aaaa.", "danger")
            return redirect(url_for("agendar"))

        if time_str not in AVAILABLE_TIME_SLOTS:
            flash("Horário inválido.", "danger")
            return redirect(url_for("agendar"))

        try:
            professional_id = int(professional_id)
            service_id = int(service_id)
        except ValueError:
            flash("Profissional ou módulo inválido.", "danger")
            return redirect(url_for("agendar"))

        conn = get_db_connection()
        if conn is None:
            flash("Erro ao conectar ao banco de dados.", "danger")
            return redirect(url_for("agendar"))

        try:
            cursor = conn.cursor(dictionary=True)

            # Verifica se o serviço realmente pertence ao profissional
            cursor.execute(
                """
                SELECT 1
                FROM professional_services
                WHERE professional_id = %s AND service_id = %s
                """,
                (professional_id, service_id),
            )
            if cursor.fetchone() is None:
                flash("Este profissional não atende o módulo selecionado.", "danger")
                return redirect(url_for("agendar"))

            # Verifica se já existe cliente com esse e-mail
            client_id = None
            if email:
                cursor.execute(
                    "SELECT id FROM clients WHERE email = %s",
                    (email,),
                )
                row = cursor.fetchone()
                if row:
                    client_id = row["id"]

            # Se não existir, cria o cliente
            if client_id is None:
                cursor.execute(
                    "INSERT INTO clients (name, email, phone) VALUES (%s, %s, %s)",
                    (name, email, phone),
                )
                conn.commit()
                client_id = cursor.lastrowid

            # Verifica se o horário já está ocupado para aquele profissional
            cursor.execute(
                """
                SELECT id FROM appointments
                WHERE appointment_date = %s
                  AND appointment_time = %s
                  AND professional_id = %s
                  AND status = 'scheduled'
                """,
                (appointment_date, time_str, professional_id),
            )
            existing = cursor.fetchone()
            if existing:
                flash("Este horário já está agendado para este profissional. Escolha outro horário.", "warning")
                return redirect(url_for("agendar"))

            # Cria o agendamento
            cursor.execute(
                """
                INSERT INTO appointments
                    (client_id, professional_id, service_id,
                     appointment_date, appointment_time, status)
                VALUES (%s, %s, %s, %s, %s, 'scheduled')
                """,
                (client_id, professional_id, service_id, appointment_date, time_str),
            )
            conn.commit()
            appointment_id = cursor.lastrowid
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("agendar_sucesso", appointment_id=appointment_id))

    # GET
    today = date.today().strftime("%d/%m/%Y")
    return render_template("booking.html", today=today, professionals=professionals)


@app.route("/agendar/sucesso/<int:appointment_id>")
def agendar_sucesso(appointment_id: int):
    conn = get_db_connection()
    if conn is None:
        flash("Erro ao conectar ao banco de dados.", "danger")
        return redirect(url_for("index"))

    appointment = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT a.id,
                   a.appointment_date,
                   a.appointment_time,
                   a.status,
                   c.name,
                   c.email,
                   c.phone,
                   p.name AS professional_name,
                   s.name AS service_name
            FROM appointments a
            JOIN clients c ON a.client_id = c.id
            JOIN professionals p ON a.professional_id = p.id
            JOIN services s ON a.service_id = s.id
            WHERE a.id = %s
            """,
            (appointment_id,),
        )
        appointment = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not appointment:
        flash("Agendamento não encontrado.", "warning")
        return redirect(url_for("index"))

    # Normaliza tipos antes de mandar para o template
    appointment["appointment_date"] = normalize_date(appointment["appointment_date"])
    appointment["appointment_time"] = normalize_time(appointment["appointment_time"])

    return render_template("booking_success.html", appointment=appointment)


@app.route("/api/horarios")
def api_horarios():
    """Retorna uma lista de horários livres para a data e profissional informados."""
    date_str = request.args.get("date")
    professional_id = request.args.get("professional_id", type=int)

    if not (date_str and professional_id):
        return jsonify({"slots": []})

    try:
        appointment_date = datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        return jsonify({"slots": []})

    conn = get_db_connection()
    if conn is None:
        return jsonify({"slots": []})

    used_times = set()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT appointment_time
            FROM appointments
            WHERE appointment_date = %s
              AND professional_id = %s
              AND status = 'scheduled'
            """,
            (appointment_date, professional_id),
        )
        for (time_value,) in cursor.fetchall():
            t = normalize_time(time_value)
            if hasattr(t, "strftime"):
                used_times.add(t.strftime("%H:%M"))
    finally:
        cursor.close()
        conn.close()

    free_slots = [t for t in AVAILABLE_TIME_SLOTS if t not in used_times]
    return jsonify({"slots": free_slots})


@app.route("/api/servicos")
def api_servicos():
    """Retorna módulos/serviços atendidos por um profissional."""
    professional_id = request.args.get("professional_id", type=int)
    if not professional_id:
        return jsonify({"services": []})

    conn = get_db_connection()
    if conn is None:
        return jsonify({"services": []})

    services = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT s.id, s.name
            FROM services s
            JOIN professional_services ps
              ON ps.service_id = s.id
             AND ps.professional_id = %s
            WHERE s.active = 1
            ORDER BY s.name
            """,
            (professional_id,),
        )
        services = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return jsonify({"services": services})


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        if conn is None:
            flash("Erro ao conectar ao banco de dados.", "danger")
            return redirect(url_for("admin_login"))

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, name, email, role
                FROM users
                WHERE email = %s AND password = %s
                """,
                (email, password),
            )
            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if not user:
            flash("Usuário ou senha inválidos.", "danger")
            return redirect(url_for("admin_login"))

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]

        flash("Login realizado com sucesso.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Logout realizado com sucesso.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    today = date.today()

    conn = get_db_connection()
    if conn is None:
        flash("Erro ao conectar ao banco de dados.", "danger")
        return redirect(url_for("admin_login"))

    total_today = 0
    upcoming = []
    try:
        cursor = conn.cursor(dictionary=True)

        # total de agendamentos do dia
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM appointments
            WHERE appointment_date = %s
              AND status = 'scheduled'
            """,
            (today,),
        )
        row = cursor.fetchone()
        if row:
            total_today = row["total"]

        # próximos agendamentos
        cursor.execute(
            """
            SELECT a.id,
                   a.appointment_date,
                   a.appointment_time,
                   a.status,
                   c.name AS client_name,
                   p.name AS professional_name,
                   s.name AS service_name
            FROM appointments a
            JOIN clients c ON a.client_id = c.id
            JOIN professionals p ON a.professional_id = p.id
            JOIN services s ON a.service_id = s.id
            WHERE a.appointment_date >= %s
              AND a.status = 'scheduled'
            ORDER BY a.appointment_date, a.appointment_time
            LIMIT 10
            """,
            (today,),
        )
        upcoming = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    # Normaliza dados para o template
    for u in upcoming:
        u["appointment_date"] = normalize_date(u["appointment_date"])
        u["appointment_time"] = normalize_time(u["appointment_time"])

    return render_template(
        "admin_dashboard.html",
        total_today=total_today,
        upcoming=upcoming,
        today=today,
    )


@app.route("/admin/agendamentos")
@login_required
def admin_agendamentos():
    date_str = request.args.get("date")

    conn = get_db_connection()
    if conn is None:
        flash("Erro ao conectar ao banco de dados.", "danger")
        return redirect(url_for("admin_dashboard"))

    appointments = []
    filter_date = None
    try:
        cursor = conn.cursor(dictionary=True)

        if date_str:
            try:
                filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                filter_date = None

        if filter_date:
            cursor.execute(
                """
                SELECT a.id,
                       a.appointment_date,
                       a.appointment_time,
                       a.status,
                       c.name AS client_name,
                       c.phone,
                       p.name AS professional_name,
                       s.name AS service_name
                FROM appointments a
                JOIN clients c ON a.client_id = c.id
                JOIN professionals p ON a.professional_id = p.id
                JOIN services s ON a.service_id = s.id
                WHERE a.appointment_date = %s
                ORDER BY a.appointment_time
                """,
                (filter_date,),
            )
        else:
            cursor.execute(
                """
                SELECT a.id,
                       a.appointment_date,
                       a.appointment_time,
                       a.status,
                       c.name AS client_name,
                       c.phone,
                       p.name AS professional_name,
                       s.name AS service_name
                FROM appointments a
                JOIN clients c ON a.client_id = c.id
                JOIN professionals p ON a.professional_id = p.id
                JOIN services s ON a.service_id = s.id
                ORDER BY a.appointment_date DESC, a.appointment_time DESC
                LIMIT 50
                """
            )

        appointments = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    # Normaliza dados para o template
    for a in appointments:
        a["appointment_date"] = normalize_date(a["appointment_date"])
        a["appointment_time"] = normalize_time(a["appointment_time"])

    return render_template(
        "admin_appointments.html",
        appointments=appointments,
        filter_date=filter_date,
    )


@app.route("/admin/agendamentos/<int:appointment_id>/cancelar", methods=["POST"])
@login_required
def admin_cancelar_agendamento(appointment_id: int):
    conn = get_db_connection()
    if conn is None:
        flash("Erro ao conectar ao banco de dados.", "danger")
        return redirect(url_for("admin_agendamentos"))

    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE appointments SET status = 'cancelled' WHERE id = %s",
            (appointment_id,),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    flash("Agendamento cancelado com sucesso.", "success")
    return redirect(url_for("admin_agendamentos"))


@app.route("/admin/relatorios")
@login_required
def admin_relatorios():
    conn = get_db_connection()
    if conn is None:
        flash("Erro ao conectar ao banco de dados.", "danger")
        return redirect(url_for("admin_dashboard"))

    stats = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT appointment_date,
                   COUNT(*) AS total
            FROM appointments
            WHERE status = 'scheduled'
            GROUP BY appointment_date
            ORDER BY appointment_date DESC
            LIMIT 30
            """
        )
        stats = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    # Normaliza datas
    for row in stats:
        row["appointment_date"] = normalize_date(row["appointment_date"])

    max_total = max((row["total"] for row in stats), default=0)

    return render_template("admin_reports.html", stats=stats, max_total=max_total)


@app.route("/admin/profissionais", methods=["GET", "POST"])
@login_required
def admin_profissionais():
    conn = get_db_connection()
    if conn is None:
        flash("Erro ao conectar ao banco de dados.", "danger")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name:
            flash("Informe o nome do profissional.", "danger")
            return redirect(url_for("admin_profissionais"))

        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO professionals (name, email, phone) VALUES (%s, %s, %s)",
                (name, email, phone),
            )
            conn.commit()
            flash("Profissional cadastrado com sucesso.", "success")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("admin_profissionais"))

    professionals = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, name, email, phone, active, created_at
            FROM professionals
            ORDER BY name
            """
        )
        professionals = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template("admin_professionals.html", professionals=professionals)


@app.route("/admin/servicos", methods=["GET", "POST"])
@login_required
def admin_servicos():
    conn = get_db_connection()
    if conn is None:
        flash("Erro ao conectar ao banco de dados.", "danger")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        form_type = request.form.get("form_type")

        try:
            cursor = conn.cursor()
            if form_type == "new_service":
                name = request.form.get("name", "").strip()
                description = request.form.get("description", "").strip()

                if not name:
                    flash("Informe o nome do módulo/serviço.", "danger")
                    return redirect(url_for("admin_servicos"))

                cursor.execute(
                    "INSERT INTO services (name, description) VALUES (%s, %s)",
                    (name, description),
                )
                conn.commit()
                flash("Módulo/serviço cadastrado com sucesso.", "success")

            elif form_type == "link":
                professional_id = request.form.get("professional_id", "").strip()
                service_id = request.form.get("service_id", "").strip()

                try:
                    professional_id = int(professional_id)
                    service_id = int(service_id)
                except ValueError:
                    flash("Profissional ou módulo inválido.", "danger")
                    return redirect(url_for("admin_servicos"))

                # Evita duplicidade
                cursor.execute(
                    """
                    INSERT IGNORE INTO professional_services (professional_id, service_id)
                    VALUES (%s, %s)
                    """,
                    (professional_id, service_id),
                )
                conn.commit()
                flash("Vínculo entre profissional e módulo criado com sucesso.", "success")

        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("admin_servicos"))

    # GET
    professionals = []
    services = []
    links = []
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, name FROM professionals WHERE active = 1 ORDER BY name"
        )
        professionals = cursor.fetchall()

        cursor.execute(
            "SELECT id, name, description, active FROM services ORDER BY name"
        )
        services = cursor.fetchall()

        cursor.execute(
            """
            SELECT ps.professional_id,
                   ps.service_id,
                   p.name AS professional_name,
                   s.name AS service_name
            FROM professional_services ps
            JOIN professionals p ON ps.professional_id = p.id
            JOIN services s ON ps.service_id = s.id
            ORDER BY p.name, s.name
            """
        )
        links = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template(
        "admin_services.html",
        professionals=professionals,
        services=services,
        links=links,
    )


if __name__ == "__main__":
    app.run(debug=True)
