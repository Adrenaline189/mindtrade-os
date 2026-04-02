String incoming = "";

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("ESP32 Binance Balance Display ready");
  Serial.println("Waiting for host data...");
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n') {
      incoming.trim();
      if (incoming.length() > 0) {
        Serial.println("------------------------------");
        Serial.println("BINANCE BALANCE");
        Serial.println(incoming);
        Serial.println("------------------------------");
      }
      incoming = "";
    } else {
      incoming += c;
    }
  }
}
