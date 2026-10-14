
const int sensorPIR = 13;

const int ledLuz = 26;
const int ledAr = 27;

const int botaoLuz = 32;
const int botaoAr = 33;

// 20 segundos para demonstracao
// 600000 = 10 minutos reais
const unsigned long tempoLimite = 20000;

const unsigned long debounce = 200;

unsigned long inicioAusencia = 0;
unsigned long ultimoCliqueLuz = 0;
unsigned long ultimoCliqueAr = 0;

bool luzLigada = true;
bool arLigado = true;

bool movimentoAnterior = false;
bool movimentoJaDetectado = false;
bool contagemIniciada = false;
bool alertaGerado = false;

bool estadoAnteriorBotaoLuz = HIGH;
bool estadoAnteriorBotaoAr = HIGH;

void atualizarEquipamentos() {
  digitalWrite(ledLuz, luzLigada ? HIGH : LOW);
  digitalWrite(ledAr, arLigado ? HIGH : LOW);
}

void mostrarEstados() {
  Serial.print("Iluminacao: ");
  Serial.println(luzLigada ? "LIGADA" : "DESLIGADA");

  Serial.print("Ar-condicionado: ");
  Serial.println(arLigado ? "LIGADO" : "DESLIGADO");
}

void setup() {
  Serial.begin(115200);

  pinMode(sensorPIR, INPUT);

  pinMode(ledLuz, OUTPUT);
  pinMode(ledAr, OUTPUT);

  pinMode(botaoLuz, INPUT_PULLUP);
  pinMode(botaoAr, INPUT_PULLUP);

  atualizarEquipamentos();

  Serial.println("SMART ENERGY - FACENS");
  Serial.println("Sala 102 iniciada.");

  mostrarEstados();

  Serial.println("Aguardando movimento...");
}

void loop() {

  unsigned long agora = millis();

  // ---------------------------
  // CONTROLE DA ILUMINACAO
  // ---------------------------

  bool leituraLuz = digitalRead(botaoLuz);

  if (estadoAnteriorBotaoLuz == HIGH &&
      leituraLuz == LOW &&
      agora - ultimoCliqueLuz > debounce) {

    luzLigada = !luzLigada;
    ultimoCliqueLuz = agora;

    atualizarEquipamentos();

    Serial.println("Botao da iluminacao pressionado.");
    mostrarEstados();
  }

  estadoAnteriorBotaoLuz = leituraLuz;

  // ---------------------------
  // CONTROLE DO AR-CONDICIONADO
  // ---------------------------

  bool leituraAr = digitalRead(botaoAr);

  if (estadoAnteriorBotaoAr == HIGH &&
      leituraAr == LOW &&
      agora - ultimoCliqueAr > debounce) {

    arLigado = !arLigado;
    ultimoCliqueAr = agora;

    atualizarEquipamentos();

    Serial.println("Botao do ar-condicionado pressionado.");
    mostrarEstados();
  }

  estadoAnteriorBotaoAr = leituraAr;

  // ---------------------------
  // SENSOR DE MOVIMENTO
  // ---------------------------

  bool movimento = digitalRead(sensorPIR) == HIGH;

  if (movimento) {

    movimentoJaDetectado = true;

    if (!movimentoAnterior) {
      Serial.println("Movimento detectado!");

      alertaGerado = false;
    }

    // Cancelar a contagem
    contagemIniciada = false;

  } else {

    if (movimentoJaDetectado &&
        !contagemIniciada &&
        !alertaGerado &&
        (luzLigada || arLigado)) {

      inicioAusencia = agora;
      contagemIniciada = true;

      Serial.println("Movimento ausente.");
      Serial.println("Iniciando contagem...");
    }
  }

  movimentoAnterior = movimento;

  // ---------------------------
  // VERIFICACAO DE DESPERDICIO
  // ---------------------------

  if (contagemIniciada &&
      !movimento &&
      !alertaGerado) {

    // Nao ha desperdicio se tudo esta desligado
    if (!luzLigada && !arLigado) {

      contagemIniciada = false;

      Serial.println("Todos os equipamentos desligados.");
      Serial.println("Contagem cancelada.");

    } else if (agora - inicioAusencia >= tempoLimite) {

      Serial.println("--------------------------");
      Serial.println("ALERTA SMART ENERGY!");
      Serial.println("Possivel desperdicio na sala 102.");

      if (luzLigada) {
        Serial.println("Desligando iluminacao...");
        luzLigada = false;
      }

      if (arLigado) {
        Serial.println("Desligando ar-condicionado...");
        arLigado = false;
      }

      atualizarEquipamentos();

      mostrarEstados();

      Serial.println("Ocorrencia registrada.");
      Serial.println("--------------------------");

      alertaGerado = true;
      contagemIniciada = false;
    }
  }

  // Inicia nova contagem se algum equipamento
  // for ligado durante a ausencia de movimento

  if (!movimento &&
      movimentoJaDetectado &&
      !contagemIniciada &&
      alertaGerado &&
      (luzLigada || arLigado)) {

    alertaGerado = false;
    contagemIniciada = true;
    inicioAusencia = agora;

    Serial.println("Equipamento religado.");
    Serial.println("Nova contagem iniciada.");
  }

  delay(20);
}
