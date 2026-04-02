#include <TFT_eSPI.h>
#include <SPI.h>

TFT_eSPI tft = TFT_eSPI();
String incoming="";
String total="-", btc="-", eth="-", status="WAIT";

String getField(String src, String key){
  String token = key + "=";
  int i = src.indexOf(token);
  if(i<0) return "";
  i += token.length();
  int j = src.indexOf(';', i);
  if(j<0) j = src.length();
  return src.substring(i,j);
}

void render(){
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString("USDT", 10, 10, 4);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString(total, 90, 10, 4);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.drawString("BTC: " + btc, 10, 60, 2);
  tft.drawString("ETH: " + eth, 10, 80, 2);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.drawString("Status: " + status, 10, 110, 2);
}

void setup(){
  Serial.begin(115200);
  delay(200);
  tft.init();
  tft.setRotation(1);
  render();
  Serial.println("BOOT_OK");
}

void loop(){
  while(Serial.available()>0){
    char c=(char)Serial.read();
    if(c=='\n'){
      incoming.trim();
      if(incoming.length()>0){
        String v;
        v=getField(incoming,"TOTAL"); if(v.length()) total=v;
        v=getField(incoming,"BTC"); if(v.length()) btc=v;
        v=getField(incoming,"ETH"); if(v.length()) eth=v;
        v=getField(incoming,"STATUS"); if(v.length()) status=v;
        render();
      }
      incoming="";
    } else incoming += c;
  }
  delay(10);
}
