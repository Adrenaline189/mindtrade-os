#include <TFT_eSPI.h>
#include <SPI.h>

#ifndef TFT_BL
#define TFT_BL 4
#endif

TFT_eSPI tft = TFT_eSPI();

void setup() {
  Serial.begin(115200);
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  delay(200);

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("BOOT", 95, 55, 4);
  delay(500);
}

void loop() {
  tft.fillScreen(TFT_RED);
  tft.setTextColor(TFT_WHITE, TFT_RED);
  tft.drawString("RED", 100, 55, 4);
  delay(1200);

  tft.fillScreen(TFT_GREEN);
  tft.setTextColor(TFT_BLACK, TFT_GREEN);
  tft.drawString("GREEN", 85, 55, 4);
  delay(1200);

  tft.fillScreen(TFT_BLUE);
  tft.setTextColor(TFT_WHITE, TFT_BLUE);
  tft.drawString("BLUE", 95, 55, 4);
  delay(1200);

  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString("DISPLAY OK", 60, 55, 4);
  delay(1200);
}
