// Controls the car speed and direction in arduino

#include <Wire.h>
#include <Adafruit_MotorShield.h>

Adafruit_MotorShield AFMS = Adafruit_MotorShield();

Adafruit_DCMotor *M1 = AFMS.getMotor(1);
Adafruit_DCMotor *M2 = AFMS.getMotor(2);
Adafruit_DCMotor *M3 = AFMS.getMotor(3);
Adafruit_DCMotor *M4 = AFMS.getMotor(4);

String command = "";

void setup() {
  Serial.begin(9600);
  AFMS.begin();

  M1->setSpeed(200);
  M2->setSpeed(200);
  M3->setSpeed(200);
  M4->setSpeed(200);

  Serial.println("Motor + Serial Debug Ready");
}

void loop() {

  // ===== READ FULL STRING =====
  if (Serial.available()) {
    command = Serial.readStringUntil('\n'); 
    command.trim();  

    Serial.print("Received: ");
    Serial.println(command);

    // ===== COMMANDS =====
    if (command == "F") {
      Serial.println("MOVING FORWARD");
      forward();
    }

    else if (command == "B") {
      Serial.println("MOVING BACKWARD");
      backward();
    }

    else if (command == "L") {
      Serial.println("TURNING LEFT");
      left();
    }

    else if (command == "R") {
      Serial.println("TURNING RIGHT");
      right();
    }

    else if (command == "S") {
      Serial.println("CAR STOPPED");
      stopAll();
    }

    else if (command == "STOP") {
      Serial.println("POTHOLE DETECTED . CAR STOPPING");
      stopAll();
    }

    else {
      Serial.println("UNKNOWN COMMAND");
    }
  }
}

// ===== MOTOR FUNCTIONS =====

void forward() {
  M1->run(FORWARD);
  M2->run(FORWARD);
  M3->run(FORWARD);
  M4->run(FORWARD);
}

void backward() {
  M1->run(BACKWARD);
  M2->run(BACKWARD);
  M3->run(BACKWARD);
  M4->run(BACKWARD);
}

void left() {
  M1->run(FORWARD);
  M2->run(FORWARD);
  M3->run(BACKWARD);
  M4->run(BACKWARD);
}

void right() {
  M1->run(BACKWARD);
  M2->run(BACKWARD);
  M3->run(FORWARD);
  M4->run(FORWARD);
}

void stopAll() {
  M1->run(RELEASE);
  M2->run(RELEASE);
  M3->run(RELEASE);
  M4->run(RELEASE);
}