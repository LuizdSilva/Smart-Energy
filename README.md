# SMART ENERGY
Sistema web de monitoramento de energia da FACENS. Mostra consumo mensal, geração solar, anomalias e o estado das salas em tempo real (ESP32 via MQTT), além de um relatório Power BI incorporado na página inicial.

## Tecnologias
- Python 3.8+ e Flask
- SQLite
- MQTT (paho-mqtt), com ESP32 ou simulador
- HTML, CSS, Bootstrap e Chart.js
- Power BI 

## Como rodar

**Requisitos:** Python 3.8+ e internet, para o Power BI e o MQTT.

1. Abra um terminal na pasta do projeto e instale as dependências (só na primeira vez):
   pip install -r requirements.txt
   
2. Inicie o sistema:
   python iniciar_sistema.py
   
3. Endereço no navegador
   http://127.0.0.1:5000/login
   
4. Entre com:
   - Usuário: `facens`
   - Senha: `facens123`

## Integrantes
- Gabriela Oliveira Lino
- Kayky Fraga da Silva
- Luiz Augusto Castilho Pereira da Silva
- Matheus Henrique dos Santos
- Otávio Lutz Nunes de Souza
- Sérgio Luíz da Silva
