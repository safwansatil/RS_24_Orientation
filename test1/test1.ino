const int numLeds = 6;
const int ledPins[] = {2,3,4,5,6,7}; // LED pins: 2,3,4,5,6,7
const int maxSequenceLength = 10;
const int minSequenceLength = 6;

int sequence[maxSequenceLength];
int userSequence[maxSequenceLength];
int sequenceLength;
int currentStep = 0;
int currentRound = 0;
bool gameActive = false;
bool inputEnabled = false;

// Round configurations: [sequence_length, delay_speed]
int rounds[3][2] = {
  {6, 600},   // Round 1: 9 bulbs, 800ms delay
  {8, 750},  // Round 2: 11 bulbs, 600ms delay  
  {10, 1000}   // Round 3: 17 bulbs, 400ms delay
};

void setup() {
  Serial.begin(9600);
  
  // Initialize LED pins as outputs
  for(int i = 0; i < numLeds; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW); // Ensure all LEDs start OFF
  }
  
  randomSeed(analogRead(0));
  Serial.println("=== LED Memory Game ===");
  Serial.println("🎮 Game Ready! Type 'start' to begin.");
  Serial.println("🎯 3 Rounds - Get ready to test your memory!");
}

void loop() {
  if(Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if(!gameActive && input.equalsIgnoreCase("start")) {
      startGame();
    }
    else if(input.equalsIgnoreCase("restart")) {
      resetGame();
      startGame();
    }
    else if(gameActive && inputEnabled) {
      processInput(input);
    }
  }
}

void startGame() {
  gameActive = true;
  currentRound = 1;
  startRound();
}

void startRound() {
  currentStep = 0;
  sequenceLength = rounds[currentRound-1][0];
  
  Serial.println("\n🎮 ===== ROUND " + String(currentRound) + " =====");
  Serial.print("🔢 Generating ");
  Serial.print(sequenceLength);
  Serial.println(" random LEDs...");
  
  generateSequence();
  playSequence();
  
  Serial.println("💡 Enter the sequence (numbers 1-6):");
  Serial.println("   (Type each number followed by Enter)");
  inputEnabled = true;
}

void generateSequence() {
  Serial.print("🔢 Sequence: ");
  for(int i = 0; i < sequenceLength; i++) {
    sequence[i] = random(0, numLeds);
    Serial.print(sequence[i] + 1);
    Serial.print(" ");
  }
  Serial.println();
}

void playSequence() {
  int roundDelay = rounds[currentRound-1][1];
  
  Serial.println("💡 Playing LED sequence:");
  for(int i = 0; i < sequenceLength; i++) {
    Serial.print("   Step ");
    Serial.print(i + 1);
    Serial.print(": LED ");
    Serial.print(sequence[i] + 1);
    Serial.println(" [ON]");
    
    // Turn ON the actual LED
    digitalWrite(ledPins[sequence[i]], HIGH);
    delay(roundDelay);
    
    Serial.print("   Step ");
    Serial.print(i + 1);
    Serial.print(": LED ");
    Serial.print(sequence[i] + 1);
    Serial.println(" [OFF]");
    
    // Turn OFF the actual LED
    digitalWrite(ledPins[sequence[i]], LOW);
    delay(roundDelay/2); // Shorter pause between LEDs
  }
}

void processInput(String input) {
  int number = input.toInt();
  
  if(number >= 1 && number <= numLeds) {
    int ledIndex = number - 1;
    
    Serial.print("You entered: ");
    Serial.println(number);
    
    // Light up the LED that user selected
    digitalWrite(ledPins[ledIndex], HIGH);
    delay(300);
    digitalWrite(ledPins[ledIndex], LOW);
    
    checkSequence(ledIndex);
  } else {
    Serial.println("❌ Invalid input! Please enter numbers 1-6 only.");
  }
}

void checkSequence(int input) {
  userSequence[currentStep] = input;
  
  Serial.print("🔍 Checking step ");
  Serial.print(currentStep + 1);
  Serial.print(": You entered ");
  Serial.print(input + 1);
  Serial.print(", Expected ");
  Serial.print(sequence[currentStep] + 1);
  
  if(userSequence[currentStep] != sequence[currentStep]) {
    Serial.println(" ❌ WRONG!");
    Serial.println("GAME_LOST");  // Signal loss for external UI
    gameLost();
    return;
  } else {
    Serial.println(" ✅ CORRECT!");
  }
  
  currentStep++;
  
  if(currentStep == sequenceLength) {
    Serial.println("ROUND_WON");  // Signal round win for external UI
    roundWon();
  } else {
    Serial.print("➡️ Next number (");
    Serial.print(sequenceLength - currentStep);
    Serial.println(" remaining):");
  }
}

void roundWon() {
  inputEnabled = false;
  Serial.println("🎉🎉🎉 ROUND " + String(currentRound) + " COMPLETED! 🎉🎉🎉");
  Serial.println("💡 All LEDs will stay ON for 5 seconds!");
  
  // Turn ON all LEDs for 5 seconds (end of round indicator)
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], HIGH);
  }
  
  // Countdown for 5 seconds
  for(int i = 5; i > 0; i--) {
    Serial.print("⏰ Next round in: ");
    Serial.print(i);
    Serial.println(" seconds...");
    delay(1000);
  }
  
  // Turn OFF all LEDs
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], LOW);
  }
  
  // Check if there are more rounds
  if(currentRound < 3) {
    currentRound++;
    startRound();
  } else {
    Serial.println("GAME_WON");  // Signal final win for external UI
    gameWon();
  }
}

void gameWon() {
  inputEnabled = false;
  Serial.println("🎉🎉🎉 CONGRATULATIONS! YOU WON THE ENTIRE GAME! 🎉🎉🎉");
  Serial.println("💡 All LEDs will stay ON for 30 seconds!");
  
  // Turn ON all LEDs for 30 seconds
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], HIGH);
  }
  
  // Countdown for 30 seconds
  for(int i = 30; i > 0; i--) {
    Serial.print("⏰ ");
    Serial.print(i);
    Serial.println(" seconds remaining...");
    delay(1000);
  }
  
  // Turn OFF all LEDs
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], LOW);
  }
  
  resetGame();
}

void gameLost() {
  inputEnabled = false;
  Serial.println("💥💥💥 GAME OVER! YOU LOST! 💥💥💥");
  Serial.println("💡 All LEDs will blink rapidly for 10 seconds!");
  
  // Rapid blink all LEDs for 10 seconds
  unsigned long startTime = millis();
  bool ledState = false;
  
  while(millis() - startTime < 10000) {
    ledState = !ledState;
    for(int i = 0; i < numLeds; i++) {
      digitalWrite(ledPins[i], ledState ? HIGH : LOW);
    }
    delay(100); // Fast blinking (100ms on, 100ms off)
  }
  
  // Ensure all LEDs are off
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], LOW);
  }
  
  resetGame();
}

void resetGame() {
  gameActive = false;
  inputEnabled = false;
  currentRound = 0;
  Serial.println("\n🔄 Game Reset!");
  Serial.println("🎮 Type 'start' to play again.");
  Serial.println("=================================");
}