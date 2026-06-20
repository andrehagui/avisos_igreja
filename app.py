from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from datetime import datetime
import re
from urllib.parse import quote_plus

app = Flask(__name__)

app.secret_key = "troque_por_uma_chave_secreta"

ADMIN_PASSWORD = "123456"


def conectar():
    conn = sqlite3.connect("avisos.db")
    conn.row_factory = sqlite3.Row
    return conn


def endereco_disponivel(endereco):
    return endereco and endereco.strip().lower() != "consultar o ministério"


def coordenadas_disponiveis(igreja):
    return igreja["latitude"] and igreja["longitude"]


def endereco_tem_municipio(endereco):
    return bool(re.search(r"\b[\wŌŪōū-]+-(shi|cho|chō|machi|gun)\b", endereco, re.IGNORECASE))


def montar_consulta_mapa(igreja, endereco):
    partes = [endereco.strip()]

    cidade = igreja["cidade"]
    estado = igreja["estado"]

    if cidade and cidade not in endereco and not endereco_tem_municipio(endereco):
        partes.append(cidade)

    if estado and estado not in endereco:
        partes.append(estado)

    partes.append("Japan")

    return ", ".join(partes)


def montar_links_mapa(igreja):
    endereco = igreja["endereco"]
    tem_coordenadas = coordenadas_disponiveis(igreja)

    if not tem_coordenadas and not endereco_disponivel(endereco):
        return []

    enderecos = [
        parte.strip()
        for parte in (endereco or "").split(" / ")
        if parte.strip()
    ]

    if tem_coordenadas:
        destino = f"{igreja['latitude']},{igreja['longitude']}"
        destino_url = quote_plus(destino)
        consulta = montar_consulta_mapa(igreja, enderecos[0]) if enderecos else destino

        return [{
            "rotulo": "Endereço",
            "consulta": consulta,
            "google": f"https://www.google.com/maps/dir/?api=1&destination={destino_url}",
            "apple": f"https://maps.apple.com/?ll={destino_url}&q={destino_url}"
        }]

    links = []

    for indice, endereco_item in enumerate(enderecos, start=1):
        consulta = montar_consulta_mapa(igreja, endereco_item)
        consulta_url = quote_plus(consulta)
        rotulo = "Endereço" if len(enderecos) == 1 else f"Local {indice}"

        links.append({
            "rotulo": rotulo,
            "consulta": consulta,
            "google": f"https://www.google.com/maps/dir/?api=1&destination={consulta_url}",
            "apple": f"https://maps.apple.com/?q={consulta_url}"
        })

    return links


def preparar_igreja(igreja):
    dados = dict(igreja)
    dados["mapa_links"] = montar_links_mapa(igreja)
    return dados


def preparar_igrejas(igrejas):
    return [preparar_igreja(igreja) for igreja in igrejas]


def garantir_coluna(conn, tabela, coluna, tipo):
    colunas = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    nomes = [coluna_existente["name"] for coluna_existente in colunas]

    if coluna not in nomes:
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


def criar_banco():
    conn = conectar()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS avisos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            categoria TEXT NOT NULL,
            data TEXT NOT NULL
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS cultos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        data TEXT NOT NULL,
        horario TEXT NOT NULL,
        descricao TEXT NOT NULL
    )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS igrejas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estado TEXT NOT NULL,
            cidade TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            culto_domingo TEXT,
            culto_semana TEXT,
            culto_sabado TEXT,
            rjm TEXT,
            endereco TEXT,
            latitude TEXT,
            longitude TEXT,
            cooperador TEXT,
            jovens TEXT
        )
    """)

    garantir_coluna(conn, "igrejas", "latitude", "TEXT")
    garantir_coluna(conn, "igrejas", "longitude", "TEXT")

    conn.commit()
    conn.close()
def inserir_igrejas_iniciais():
    igrejas = [
        (
            "Aichi-ken",
            "Anjo-shi",
            "anjo",
            "Dom. 19:00",
            "Qua. 20:00",
            "Sáb. 20:00",
            "1º e 3º Dom. 14:00",
            "Anjo-shi Akamatsu-chō Nishishimo - 40",
            "Vilson Sérgio Kojo",
            "Carlos Roberto Ogata"
        ),
        (
            "Aichi-ken",
            "Nagoya-shi",
            "nagoya",
            "1º e 3º Dom. 19:00",
            "",
            "Sáb. 19:00",
            "2º e 4º Dom. 14:00",
            "Consultar o Ministério",
            "Ronaldo Kazumi Sakamoto",
            "Jean Akio Takaesu"
        ),
        (
            "Aichi-ken",
            "Toyohashi-shi",
            "toyohashi",
            "Dom. 19:30",
            "Qua. 20:00",
            "Sáb. 20:00",
            "Dom. 10:00",
            "Toyohashi-shi Owaki-chō Owaki 20-4",
            "Luiz Katsumi Oshima",
            "Sunao Ibusuki"
        ),
        (
            "Chiba-ken",
            "Kashiwa-shi",
            "kashiwa",
            "2º e 4º Dom. 13:00",
            "",
            "",
            "3º Dom. 13:00",
            "Kashiwa-shi Kashiwa 3 chome 7-21",
            "Julio Kiyosuke Sakai",
            "Daniel Shimizu"
        ),
        (
            "Gifu-ken",
            "Kakamigahara-shi",
            "kakamigahara",
            "2º e 4º Dom. 19:00",
            "",
            "Sáb. 20:00",
            "1º e 3º Dom. 10:00",
            "Kakamigahara-shi Nakasakura Machi 1 chome 19",
            "Paulo Borges da Silva",
            "Fabio Konishi"
        ),
        (
            "Gunma-ken",
            "Ota-shi",
            "ota",
            "2º e 4º Dom. 18:00",
            "",
            "Sáb. 20:00",
            "1º e 3º Dom. 10:00",
            "Ota-shi Kamitajima-chō 388-2",
            "José Augusto de Oliveira Mazzoni",
            "André Camargo Hagui"
        ),
        (
            "Hiroshima-ken",
            "Fukuyama-shi",
            "fukuyama",
            "4º Dom. 17:30",
            "",
            "Sáb. 20:00",
            "1º e 3º Dom. 10:00",
            "Fukuyama-shi Matsunaga-chō 3 chome 3-18",
            "Laerte Hiromita Lopes",
            "Édison Terumitsu Kajita"
        ),
        (
            "Hiroshima-ken",
            "Shiwa-cho",
            "shiwa",
            "1º e 3º Dom. 17:30",
            "",
            "Sáb. 20:00",
            "2º Dom. 10:00 / 4º Dom. 10:00",
            "Higashi Hiroshima-shi Shiwa-chō Shiwa-Higashi 4454-1 / View Port Kure Hotel, Kure-shi Nakadori 1 chome 1-2",
            "Marcos Tomita",
            "Ulisses Massaki de Souza"
        ),
        (
            "Ibaraki-ken",
            "Tsukubamirai-shi",
            "tsukubamirai",
            "Dom. 19:00",
            "Qua. 20:00",
            "Sáb. 20:00",
            "2º e 4º Dom. 10:00",
            "Tsukubamirai-shi Hososhiro 730-1",
            "Edson Hiroshi Inoui",
            "Carlos Hirooka"
        ),
        (
            "Kanagawa-ken",
            "Aiko-gun",
            "aiko",
            "3º Dom. 14:00",
            "",
            "Sáb. 20:00",
            "2º e 4º Dom. 14:00",
            "Aiko-gun Aikawa-Machi 3 chome 6-18",
            "Mamoru Oshiro",
            "Samuel Vianna"
        ),
        (
            "Mie-ken",
            "Kameyama-shi",
            "kameyama",
            "1º e 3º Dom. 19:00",
            "Qui. 19:30",
            "Sáb. 19:30",
            "2º e 4º Dom. 10:00",
            "Kameyama-shi Wakayama-chō 7-10",
            "Joemir Koozo Kawamura",
            "Fernando Vaz Shiga"
        ),
        (
            "Nagano-ken",
            "Okaya-shi",
            "okaya",
            "2º e 4º Dom. 19:00",
            "",
            "1º, 2º e 4º Sáb. 20:00 / 3º Sáb. 19:00",
            "1º e 3º Dom. 10:00",
            "Okaya-shi Osachigongen-chō 3 chome 5-16 - 2º Floor / Sakashita kōkaidō Ina-shi 3266",
            "Marcos Rogério Akira Furumiti",
            "José Maria Tito da Mota"
        ),
        (
            "Nagano-ken",
            "Suzaka-shi",
            "suzaka",
            "",
            "",
            "1º e 2º Sáb. 19:30 / 3º Sáb. 19:30",
            "4º Dom. 14:00 / 2º Dom. 14:00",
            "Suzaka-shi Former City Office Tokiwa-cho 812-2 / Maruko Bunka Kaikan, Ueda-shi Kamimaruko 1488",
            "César Akira Torigoe",
            ""
        ),
        (
            "Ōita-ken",
            "Ōita-shi",
            "oita",
            "3º Dom. 10:00",
            "",
            "1º Sáb. 10:00",
            "",
            "Oita-shi Takasaki 1-12-13",
            "Todaka Akimassa",
            ""
        ),
        (
            "Shiga-ken",
            "Gamou-gun",
            "gamou",
            "Dom. 18:00",
            "",
            "Sáb. 20:00",
            "1º e 3º Dom. 10:00",
            "Gamou-gun Hino-chō 2492-33 Nishioji",
            "Amarildo Alvarenga",
            "Rafael Hiroshi Iwanaga"
        ),
        (
            "Shiga-ken",
            "Nagahama-shi",
            "nagahama",
            "1º e 3º Dom. 14:00",
            "",
            "Sáb. 19:00",
            "2º e 4º Dom. 10:00",
            "Nagahama-shi Jifukuji-cho 4-36",
            "Marcos Alves Katsui",
            "Diego Viana de Souza"
        ),
        (
            "Okayama-ken",
            "Kurashiki-shi",
            "kurashiki",
            "2º Dom. 18:30",
            "",
            "",
            "4º Dom. 14:00",
            "Kurashiki-shi Mabi-cho Yata 40-1",
            "Osni Camargo de Almeida",
            ""
        ),
        (
            "Ōsaka-fu",
            "Hirakata-shi",
            "hirakata",
            "1º Dom. 14:00",
            "",
            "3º Sáb. 19:30",
            "2º e 4º Dom. 14:00",
            "Consultar o Ministério",
            "Gilberto Pereira da Cruz",
            ""
        ),
        (
            "Shimane-ken",
            "Izumo-shi",
            "izumo",
            "1º Dom. 11:00",
            "",
            "",
            "3º Dom. 11:00",
            "Izumo-shi Ekinan-cho 1-5",
            "Marcos Rozetti",
            "Eleazaro Souza"
        ),
        (
            "Shizuoka-ken",
            "Fuji-shi",
            "fuji",
            "2º e 4º Dom. 19:00",
            "",
            "Sáb. 20:00",
            "1º e 3º Dom. 14:00",
            "Fuji-shi Obuchi 1483",
            "Osvaldo Costa Filho",
            "Thiago Imada Almeida"
        ),
        (
            "Shizuoka-ken",
            "Hamamatsu-shi",
            "hamamatsu",
            "Dom. 19:00",
            "Qui. 20:00",
            "Sáb. 20:00",
            "2º e 4º Dom. 14:00",
            "Hamamatsu-shi Minami-ku Higashi Machi 268",
            "Samuel Seiki Inamine",
            "Alexandre Vila Rebniker"
        ),
        (
            "Shizuoka-ken",
            "Iwata-shi",
            "iwata",
            "1º e 3º Dom. 14:00",
            "",
            "Sáb. 19:00",
            "2º e 4º Dom. 10:00",
            "Consultar o Ministério",
            "Nelson Bruschi da Silva",
            "Wellington Luís Sebastião"
        ),
        (
            "Shizuoka-ken",
            "Kakegawa-shi",
            "kakegawa",
            "1º e 3º Dom. 19:00",
            "",
            "Sáb. 19:30",
            "2º e 4º Dom. 14:00",
            "Goshobara 17-1",
            "Alex Maximilian Calixto",
            "Alfredo Shiokawa Gimenez"
        ),
        (
            "Shizuoka-ken",
            "Yaizu-shi",
            "yaizu",
            "2º e 4º Dom. 19:00",
            "Sex. 20:00",
            "Sáb. 20:00",
            "1º e 3º Dom. 10:00",
            "Yaizu-shi Sōuemon 15-2",
            "Paulo Okada",
            "Jhouberth Seto da Mota"
        ),
        (
            "Toyama-ken",
            "Takaoka-shi",
            "takaoka",
            "1º e 3º Dom. 18:00",
            "",
            "Sáb. 20:00",
            "2º e 4º Dom. 10:00",
            "Takaoka-Shi Nishi Tōheizō 656-1",
            "Edson Akio Ishizaki",
            ""
        ),
        (
            "Yamanashi-ken",
            "Chuo-shi",
            "chuo",
            "1º e 3º Dom. 19:00",
            "",
            "Sáb. 20:00",
            "2º e 4º Dom. 10:00",
            "Consultar o Ministério",
            "Almir Rogerio da Silva",
            "Clayton Bezerra Franco da Silva Matsukita"
        ),
        (
            "Fukui-ken",
            "Fukui-shi",
            "fukui",
            "",
            "",
            "Sáb. 11:00",
            "",
            "Echizen-shi Central 2-5-1",
            "Anicio Dias Rosemberg",
            ""
        )
    ]

    conn = conectar()

    for igreja in igrejas:
        estado, cidade, slug, culto_domingo, culto_semana, culto_sabado, rjm, endereco, cooperador, jovens = igreja

        existente = conn.execute(
            "SELECT id FROM igrejas WHERE slug = ?",
            (slug,)
        ).fetchone()

        if existente:
            conn.execute("""
                UPDATE igrejas
                SET estado = ?,
                    cidade = ?,
                    culto_domingo = ?,
                    culto_semana = ?,
                    culto_sabado = ?,
                    rjm = ?,
                    endereco = ?,
                    cooperador = ?,
                    jovens = ?
                WHERE slug = ?
            """, (
                estado,
                cidade,
                culto_domingo,
                culto_semana,
                culto_sabado,
                rjm,
                endereco,
                cooperador,
                jovens,
                slug
            ))
        else:
            conn.execute("""
                INSERT INTO igrejas
                (
                    estado,
                    cidade,
                    slug,
                    culto_domingo,
                    culto_semana,
                    culto_sabado,
                    rjm,
                    endereco,
                    cooperador,
                    jovens
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, igreja)

    conn.commit()
    conn.close()

@app.route("/")
def index():

    conn = conectar()

    avisos = conn.execute(
        "SELECT * FROM avisos ORDER BY id DESC LIMIT 5"
    ).fetchall()

    igrejas = conn.execute(
        """
        SELECT *
        FROM igrejas
        ORDER BY estado, cidade
        LIMIT 6
        """
    ).fetchall()

    conn.close()

    igrejas = preparar_igrejas(igrejas)

    return render_template(
        "index.html",
        avisos=avisos,
        igrejas=igrejas
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        senha = request.form.get("senha", "")

        if senha == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))

        return render_template(
            "login.html",
            erro="Senha incorreta"
        )

    return render_template("login.html")


@app.route("/admin", methods=["GET", "POST"])
def admin():

    if not session.get("admin"):
        return redirect(url_for("login"))

    if request.method == "POST":

        titulo = request.form["titulo"]
        mensagem = request.form["mensagem"]
        categoria = request.form["categoria"]

        data = datetime.now().strftime("%d/%m/%Y %H:%M")

        conn = conectar()

        conn.execute(
            """
            INSERT INTO avisos
            (titulo, mensagem, categoria, data)
            VALUES (?, ?, ?, ?)
            """,
            (titulo, mensagem, categoria, data)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin"))

    conn = conectar()

    avisos = conn.execute(
        "SELECT * FROM avisos ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        avisos=avisos
    )


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):

    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = conectar()

    aviso = conn.execute(
        "SELECT * FROM avisos WHERE id = ?",
        (id,)
    ).fetchone()

    if not aviso:
        conn.close()
        return redirect(url_for("admin"))

    if request.method == "POST":

        titulo = request.form["titulo"]
        mensagem = request.form["mensagem"]
        categoria = request.form["categoria"]

        conn.execute(
            """
            UPDATE avisos
            SET titulo = ?,
                mensagem = ?,
                categoria = ?
            WHERE id = ?
            """,
            (
                titulo,
                mensagem,
                categoria,
                id
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin"))

    conn.close()

    return render_template(
        "editar.html",
        aviso=aviso
    )


@app.route("/apagar/<int:id>", methods=["POST"])
def apagar(id):

    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = conectar()

    conn.execute(
        "DELETE FROM avisos WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.route("/sair")
def sair():

    session.clear()

    return redirect(url_for("index"))

@app.route("/localidades")
def localidades():

    conn = conectar()

    igrejas = conn.execute("""
        SELECT *
        FROM igrejas
        ORDER BY estado, cidade
    """).fetchall()

    conn.close()

    igrejas = preparar_igrejas(igrejas)

    return render_template(
        "localidades.html",
        igrejas=igrejas
    )

@app.route("/localidade/<slug>")
def localidade(slug):

    conn = conectar()

    igreja = conn.execute(
        "SELECT * FROM igrejas WHERE slug = ?",
        (slug,)
    ).fetchone()

    conn.close()

    if not igreja:
        return redirect(url_for("localidades"))

    igreja = preparar_igreja(igreja)

    return render_template(
        "localidade.html",
        igreja=igreja
    )

@app.route("/admin/localidades", methods=["GET", "POST"])
def admin_localidades():

    if not session.get("admin"):
        return redirect(url_for("login"))

    if request.method == "POST":
        estado = request.form["estado"].strip()
        cidade = request.form["cidade"].strip()
        slug = request.form["slug"].strip().lower()
        culto_domingo = request.form["culto_domingo"].strip()
        culto_semana = request.form["culto_semana"].strip()
        culto_sabado = request.form["culto_sabado"].strip()
        rjm = request.form["rjm"].strip()
        endereco = request.form["endereco"].strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()
        cooperador = request.form["cooperador"].strip()
        jovens = request.form["jovens"].strip()

        conn = conectar()

        conn.execute("""
            INSERT OR IGNORE INTO igrejas
            (
                estado,
                cidade,
                slug,
                culto_domingo,
                culto_semana,
                culto_sabado,
                rjm,
                endereco,
                latitude,
                longitude,
                cooperador,
                jovens
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            estado,
            cidade,
            slug,
            culto_domingo,
            culto_semana,
            culto_sabado,
            rjm,
            endereco,
            latitude,
            longitude,
            cooperador,
            jovens
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_localidades"))

    conn = conectar()

    igrejas = conn.execute("""
        SELECT *
        FROM igrejas
        ORDER BY estado, cidade
    """).fetchall()

    conn.close()

    return render_template(
        "admin_localidades.html",
        igrejas=igrejas
    )

@app.route("/editar-localidade/<int:id>", methods=["GET", "POST"])
def editar_localidade(id):

    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = conectar()

    igreja = conn.execute(
        "SELECT * FROM igrejas WHERE id = ?",
        (id,)
    ).fetchone()

    if not igreja:
        conn.close()
        return redirect(url_for("admin_localidades"))

    if request.method == "POST":
        estado = request.form["estado"].strip()
        cidade = request.form["cidade"].strip()
        slug = request.form["slug"].strip().lower()
        culto_domingo = request.form["culto_domingo"].strip()
        culto_semana = request.form["culto_semana"].strip()
        culto_sabado = request.form["culto_sabado"].strip()
        rjm = request.form["rjm"].strip()
        endereco = request.form["endereco"].strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()
        cooperador = request.form["cooperador"].strip()
        jovens = request.form["jovens"].strip()

        conn.execute("""
            UPDATE igrejas
            SET estado = ?,
                cidade = ?,
                slug = ?,
                culto_domingo = ?,
                culto_semana = ?,
                culto_sabado = ?,
                rjm = ?,
                endereco = ?,
                latitude = ?,
                longitude = ?,
                cooperador = ?,
                jovens = ?
            WHERE id = ?
        """, (
            estado,
            cidade,
            slug,
            culto_domingo,
            culto_semana,
            culto_sabado,
            rjm,
            endereco,
            latitude,
            longitude,
            cooperador,
            jovens,
            id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_localidades"))

    conn.close()

    return render_template(
        "editar_localidade.html",
        igreja=igreja
    )


@app.route("/apagar-localidade/<int:id>", methods=["POST"])
def apagar_localidade(id):

    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = conectar()

    conn.execute(
        "DELETE FROM igrejas WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_localidades"))


if __name__ == "__main__":

    criar_banco()
    inserir_igrejas_iniciais()

    app.run(debug=True)
