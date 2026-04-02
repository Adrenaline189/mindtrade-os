#define USER_SETUP_LOADED
#define ST7789_DRIVER
#define TFT_WIDTH  135
#define TFT_HEIGHT 240
#define TFT_MISO -1
#define TFT_MOSI 19
#define TFT_SCLK 18
#define TFT_CS    5
#define TFT_DC   16
#define TFT_RST  23
#define TFT_BL    4
#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8
#define LOAD_GFXFF
#define SPI_FREQUENCY  40000000

#include <TFT_eSPI.h>
#include <SPI.h>

TFT_eSPI tft = TFT_eSPI();
String incoming = "";
String lastLine = "Waiting for data...";

void drawScreen(const String &line) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextFont(4);
  tft.drawString("USDT", 8, 4);
  tft.drawFastHLine(0, 24, 240, TFT_DARKGREY);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);

  int y = 44;
  int start = 0;
  while (start < line.length()) {
    int end = start + 14;
    if (end > line.length()) end = line.length();
    tft.drawString(line.substring(start, end), 6, y, 4);
    y += 28;
    start = end;
    if (y > 126) break;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  tft.init();
  tft.setRotation(1);
  drawScreen(lastLine);
  Serial.println("TTGO T-Display ready");
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n') {
      incoming.trim();
      if (incoming.length() > 0) {
        lastLine = incoming;
        drawScreen(lastLine);
        Serial.println("DISPLAY: " + lastLine);
      }
      incoming = "";
    } else {
      incoming += c;
    }
  }
}
