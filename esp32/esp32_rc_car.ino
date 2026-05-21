#include <Arduino.h>
#include <ESP32Servo.h>

// Update these pins to match your chassis wiring.
constexpr int ENA_PIN = 14;
constexpr int IN1_PIN = 27;
constexpr int IN2_PIN = 26;
constexpr int ENB_PIN = 25;
constexpr int IN3_PIN = 33;
constexpr int IN4_PIN = 32;
constexpr int SERVO_PIN = 13;

Servo steering;

String lineBuffer;
int currentSpeed = 0;
int centerAngle = 90;
int leftAngle = 55;
int rightAngle = 125;

void driveForward(int speedValue) {
  analogWrite(ENA_PIN, speedValue);
  analogWrite(ENB_PIN, speedValue);
  digitalWrite(IN1_PIN, HIGH);
  digitalWrite(IN2_PIN, LOW);
  digitalWrite(IN3_PIN, HIGH);
  digitalWrite(IN4_PIN, LOW);
}

void stopMotors() {
  analogWrite(ENA_PIN, 0);
  analogWrite(ENB_PIN, 0);
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, LOW);
  digitalWrite(IN3_PIN, LOW);
  digitalWrite(IN4_PIN, LOW);
}

int mapSpeedPercent(int percent) {
  percent = constrain(percent, 0, 100);
  return map(percent, 0, 100, 0, 255);
}

int parseSpeed(const String& line) {
  int idx = line.indexOf("speed=");
  if (idx < 0) {
    return currentSpeed;
  }
  return line.substring(idx + 6).toInt();
}

String parseDirection(const String& line) {
  int idx = line.indexOf("dir=");
  if (idx < 0) {
    return "straight";
  }
  int end = line.indexOf(' ', idx);
  if (end < 0) {
    end = line.length();
  }
  return line.substring(idx + 4, end);
}

void applyCommand(const String& line) {
  if (line.startsWith("STOP")) {
    steering.write(centerAngle);
    currentSpeed = 0;
    stopMotors();
    return;
  }

  if (line.startsWith("CRUISE")) {
    steering.write(centerAngle);
    currentSpeed = parseSpeed(line);
    driveForward(mapSpeedPercent(currentSpeed));
    return;
  }

  if (line.startsWith("SLOW")) {
    steering.write(centerAngle);
    currentSpeed = parseSpeed(line);
    driveForward(mapSpeedPercent(currentSpeed));
    return;
  }

  if (line.startsWith("AVOID")) {
    String dir = parseDirection(line);
    currentSpeed = parseSpeed(line);
    if (dir == "left") {
      steering.write(leftAngle);
    } else if (dir == "right") {
      steering.write(rightAngle);
    } else {
      steering.write(centerAngle);
    }
    driveForward(mapSpeedPercent(currentSpeed));
    return;
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  pinMode(ENB_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);

  steering.attach(SERVO_PIN);
  steering.write(centerAngle);
  stopMotors();
}

void loop() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      lineBuffer.trim();
      if (lineBuffer.length() > 0) {
        applyCommand(lineBuffer);
      }
      lineBuffer = "";
    } else {
      lineBuffer += c;
    }
  }
}

