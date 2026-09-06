#include <Wire.h>
#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoDistance distanceSensor;
volatile int current_distance = -1;

String getDistanceHandler(String args) {
  return String(current_distance);
}

void setup() {
  Bridge.begin();

  // Initialize Qwiic bus (Wire1 on UNO Q)
  Wire1.begin();
  delay(100);

  // Bind Modulino library to Wire1
  Modulino.begin(Wire1);
  delay(200);

  // Start Time-of-Flight sensor
  distanceSensor.begin();
  delay(100);

  // Register MessagePack-RPC method
  Bridge.provide("get_distance", getDistanceHandler);
}

void loop() {
  Bridge.update();

  // Poll sensor continuously on the STM32 loop
  if (distanceSensor.available()) {
    int val = distanceSensor.get();
    if (val > 0) {
      current_distance = val;
    }
  }

  delay(100);
}