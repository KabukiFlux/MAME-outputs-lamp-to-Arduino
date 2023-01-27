/*
TEST script to read a byte from serial port and write to a
custom array of digital pins.

This code was tested on an arduino nano
*/
int serialByte;
byte pins[] = {2, 3, 4, 5, 6, 7, 8, 9};

void setup(){
  Serial.begin(115200);
  for (int i = 0; i < 8; i++) {
    pinMode(pins[i],OUTPUT);
    digitalWrite(pins[i], LOW);
  } 
}

void loop(){
  // TEST to check if the leds are mapped correctly
  /*
  for (int i = 0; i < 8; i++) {
     digitalWrite(pins[i], HIGH);
     delay(1000);
     digitalWrite(pins[i], LOW);
     delay(1000);
  }
  */
  if (Serial.available() > 0) {
    serialByte = Serial.read();
    for (int i = 0; i < 8; i++) {
      digitalWrite(pins[i], bitRead (serialByte, i));
    }
  }
}
