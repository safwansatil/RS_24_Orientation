// Reaction Duel. Pin assignments are for an Arduino Uno R3.
constexpr uint8_t cuePin = 8, playerOne = 9, playerTwo = 10, buzzerPin = 11;
constexpr bool useBuzzer = false;  // Set true for an active-high buzzer module.
constexpr unsigned long debounceUs = 8000, tieUs = 2000;
constexpr unsigned long responseUs = 3000000, beepUs = 90000;

enum Phase { Idle, Release, Waiting, Live };
Phase phase = Idle;
unsigned long roundId, waitStarted, waitMs, cueAt;
char command[32];
uint8_t commandLength = 0;
bool discardLine = false;

struct Button {
  uint8_t pin;
  bool raw = false;
  bool held = false;
  unsigned long changedAt = 0;
  unsigned long pressedAt = 0;
  bool pressed = false;

  explicit Button(uint8_t inputPin) : pin(inputPin) {}

  void sample(unsigned long now) {
    bool down = digitalRead(pin) == LOW;
    if (down != raw) {
      raw = down;
      changedAt = now;
    }
    if (raw != held && now - changedAt >= debounceUs) {
      held = raw;
      if (held && !pressed) {
        pressedAt = changedAt;
        pressed = true;
      }
    }
  }
};

Button left(playerOne), right(playerTwo);

void lightsOff() {
  digitalWrite(cuePin, LOW);
  digitalWrite(buzzerPin, LOW);
}

void event(const __FlashStringHelper* name) {
  Serial.print(name);
  Serial.print(',');
  Serial.println(roundId);
}

void result(const __FlashStringHelper* outcome, int player, unsigned long elapsed) {
  lightsOff();
  phase = Idle;
  Serial.print(F("RESULT,"));
  Serial.print(roundId);
  Serial.print(',');
  Serial.print(outcome);
  Serial.print(',');
  Serial.print(player);
  Serial.print(',');
  Serial.println(elapsed / 1000);
}

void readCommands() {
  // Bound the work per loop so input sampling stays responsive.
  for (uint8_t count = 0; count < 16 && Serial.available(); ++count) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch != '\n') {
      if (commandLength < sizeof(command) - 1 && !discardLine) {
        command[commandLength++] = ch;
      } else {
        discardLine = true;
      }
      continue;
    }
    command[commandLength] = '\0';
    commandLength = 0;
    if (discardLine) {
      discardLine = false;
      continue;
    }
    if (strcmp(command, "HELLO") == 0) {
      Serial.println(F("REACTION_DUEL,1"));
    } else if (strcmp(command, "CANCEL") == 0) {
      phase = Idle;
      lightsOff();
    } else if (phase == Idle && strncmp(command, "ARM,", 4) == 0) {
      char* end;
      unsigned long id = strtoul(command + 4, &end, 10);
      if (id && *end == '\0') {
        roundId = id;
        phase = Release;
        event(F("RELEASE"));
      }
    }
  }
}

void setup() {
  pinMode(cuePin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);
  lightsOff();
  pinMode(playerOne, INPUT_PULLUP);
  pinMode(playerTwo, INPUT_PULLUP);
  randomSeed(analogRead(A0) ^ micros());
  Serial.begin(115200);
}

void loop() {
  unsigned long now = micros();
  left.sample(now);
  right.sample(now);
  readCommands();

  if (phase == Release && !left.held && !right.held && !left.raw && !right.raw
      && now - left.changedAt >= debounceUs && now - right.changedAt >= debounceUs) {
    left.pressed = right.pressed = false;
    waitMs = random(2000, 5001);
    waitStarted = millis();
    phase = Waiting;
    event(F("WAIT"));
  }

  if ((phase == Waiting || phase == Live) && (left.pressed || right.pressed)) {
    bool leftFirst = left.pressed && (!right.pressed || long(left.pressedAt - right.pressedAt) <= 0);
    unsigned long first = leftFirst ? left.pressedAt : right.pressedAt;
    if (now - first >= debounceUs + tieUs) {
      bool tied = left.pressed && right.pressed &&
                  (leftFirst ? right.pressedAt - first : left.pressedAt - first) <= tieUs;
      int player = tied ? 0 : (leftFirst ? 1 : 2);
      if (phase == Waiting || long(first - cueAt) < 0) {
        result(F("EARLY"), player, 0);
      } else if (first - cueAt > responseUs) {
        result(F("MISS"), 0, 0);
      } else if (tied && first - cueAt + (leftFirst ? right.pressedAt - first : left.pressedAt - first) <= responseUs) {
        result(F("TIE"), 0, 0);
      } else {
        result(F("WIN"), leftFirst ? 1 : 2, first - cueAt);
      }
    }
  }

  // A button currently settling keeps the cue off until the edge is resolved.
  if (phase == Waiting && !left.raw && !right.raw && !left.pressed && !right.pressed
      && millis() - waitStarted >= waitMs) {
    cueAt = micros();
    digitalWrite(cuePin, HIGH);
    if (useBuzzer) digitalWrite(buzzerPin, HIGH);
    phase = Live;
    event(F("GO"));
  }
  if (phase == Live && long(now - cueAt) >= 0) {
    if (useBuzzer && now - cueAt >= beepUs) digitalWrite(buzzerPin, LOW);
    if (now - cueAt >= responseUs + debounceUs + tieUs && !left.pressed && !right.pressed) {
      result(F("MISS"), 0, 0);
    }
  }
}
