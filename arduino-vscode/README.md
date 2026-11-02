# ESP32 no VS Code (PlatformIO + Wokwi)

Mesmo firmware da pasta arduino, para rodar sem o site wokwi.com.

## Requisitos
- VS Code com as extensões PlatformIO IDE e Wokwi Simulator
- Sistema Smart Energy ligado, com a sala A01 cadastrada

## Como rodar
1. Abra esta pasta (arduino-vscode) no VS Code (File > Open Folder).
2. Compile: ícone do PlatformIO > Project Tasks > esp32dev > Build.
3. Abra diagram.json e clique no play.
4. Veja "MQTT conectado!" no Serial Monitor e o card da sala A01 em Tempo Real.

Rode só uma simulação por vez: o broker é público e o tópico é compartilhado.
Se o arduino/sketch.ino mudar, atualize também o src/main.cpp (mantendo #include <Arduino.h> na primeira linha).
