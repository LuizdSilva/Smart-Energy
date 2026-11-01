import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
os.environ["MQTT_ENABLED"] = "0"
sys.path.insert(0, str(RAIZ))
falhas = []


def ok(cond, msg):
    print(("  [OK]    " if cond else "  [FALHA] ") + msg)
    if not cond:
        falhas.append(msg)


print("1) Ambiente")
ok(sys.version_info >= (3, 8), f"Python {sys.version.split()[0]}")
try:
    import flask
    from importlib.metadata import version
    ok(True, f"Flask {version('flask')}")
except ImportError:
    ok(False, "Flask não instalado -> pip install -r requirements.txt")
    sys.exit(1)

print("2) Arquivo .env")
env = RAIZ / ".env"
ok(env.exists(), ".env existe na raiz do projeto")
valores = {}
if env.exists():
    for linha in env.read_text(encoding="utf-8-sig").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            valores[k.strip()] = v.strip().strip('"').strip("'")
    ok(bool(valores.get("APP_USER")), f"APP_USER = {valores.get('APP_USER')!r}")
    ok(bool(valores.get("APP_PASSWORD")), f"APP_PASSWORD definido ({len(valores.get('APP_PASSWORD',''))} caracteres)")

print("3) Arquivos usados pelo código")
for rel in re.findall(r"\"([\w\-/]+\.html)\"", (RAIZ / "app/rotas.py").read_text(encoding="utf-8")):
    ok((RAIZ / "app/templates" / rel).exists(), f"template {rel}")
for t in (RAIZ / "app/templates").glob("*.html"):
    for rel in re.findall(r"filename='([^']+)'", t.read_text(encoding="utf-8")):
        if rel.startswith("img/"):
            continue
        ok((RAIZ / "app/static" / rel).exists(), f"estático {rel} (usado em {t.name})")
ok((RAIZ / "app/data/dados_reais_2024.json").exists(), "app/data/dados_reais_2024.json")

print("4) Simulação do login")
for linha in valores.items():
    os.environ[linha[0]] = linha[1]
os.environ["MQTT_ENABLED"] = "0"
os.environ["DB_PATH"] = str(RAIZ / "data" / "_verificar.db")
from app import create_app

app = create_app()
c = app.test_client()
r = c.get("/login")
ok(r.status_code == 200, f"GET /login -> {r.status_code}")
tok = re.search(r'name="csrf_token" value="([^"]+)"', r.get_data(as_text=True))
ok(bool(tok), "formulário de login traz o token CSRF")
r = c.post("/login", data={"usuario": valores.get("APP_USER", ""), "senha": valores.get("APP_PASSWORD", ""),
                           "csrf_token": tok.group(1) if tok else ""})
ok(r.status_code == 302 and r.headers.get("Location", "").endswith("/"), "login com usuário/senha do .env entra")
ok(c.get("/").status_code == 200, "página inicial abre depois do login")
for url in ("/tempo-real", "/consumo", "/geracao-solar", "/anomalias", "/dados", "/salas"):
    ok(c.get(url).status_code == 200, f"página {url}")
try:
    os.remove(os.environ["DB_PATH"])
except OSError:
    pass
print("\n" + ("TUDO CERTO." if not falhas else f"{len(falhas)} problema(s) encontrado(s) — veja as linhas [FALHA]."))
sys.exit(1 if falhas else 0)
