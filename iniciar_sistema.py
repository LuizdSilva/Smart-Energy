import logging
import os
import socket
from pathlib import Path


def carregar_env(caminho):
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.split("=", 1)

        os.environ[nome.strip()] = valor.strip().strip('"').strip("'")


carregar_env(Path(__file__).parent / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app import create_app

app = create_app()

def porta_em_uso(porta, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, porta)) == 0


if __name__ == "__main__":
    host = "127.0.0.1"
    porta_desejada = int(os.environ.get("PORT", 5000))
    porta = porta_desejada
    while porta_em_uso(porta, host) and porta < porta_desejada + 20:
        porta += 1
    if porta != porta_desejada:
        print("=" * 70)
        print(f"ATENCAO: a porta {porta_desejada} JA ESTA EM USO por outro programa")
        print("(provavelmente uma versão antiga do sistema ainda aberta em outro terminal).")
        print(f"Este sistema vai usar a porta {porta}. Abra o endereço abaixo:")
        print("Para liberar a 5000:  netstat -ano | findstr :5000   e depois   taskkill /PID <numero> /F")
        print("=" * 70)
    print(f"\n>>> Abra no navegador: http://{host}:{porta}/login   (teste: http://{host}:{porta}/saude)\n")

    app.run(host=host, port=porta, debug=False, use_reloader=False)
