const int numLeds = 6;
const int ledPins[] = {5,6,7,8,9,10};
const int maxSequenceLength = 10;
const int minSequenceLength = 6;

int sequence[maxSequenceLength];
int userSequence[maxSequenceLength];
int sequenceLength;
int currentStep = 0;
int currentRound = 0;
bool gameActive = false;
bool inputEnabled = false;
bool gamePaused = false;  // NEW: Pause state
int score = 0;            // NEW: Score tracker

// Round configurations: [sequence_length, delay_speed]
int rounds[3][2] = {
  {6, 600},
  {8, 750},
  {10, 1000}
};

void setup() {
  Serial.begin(9600);
  
  for(int i = 0; i < numLeds; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
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
     // startGame();
    }
    // NEW: Stop/pause functionality
    else if(input.equalsIgnoreCase("stop")) {
      togglePause();
    }
    else if(gameActive && inputEnabled && !gamePaused) {  // MODIFIED: Check pause state
      processInput(input);
    }
  }
}

// NEW: Toggle pause function
void togglePause() {
  if (!gameActive) return;
  
  gamePaused = !gamePaused;
  if (gamePaused) {
    Serial.println("⏸️ GAME PAUSED");
    Serial.println("📊 Current Score: " + String(score));
    // Turn off all LEDs when paused
    for(int i = 0; i < numLeds; i++) {
      digitalWrite(ledPins[i], LOW);
    }
  } else {
    Serial.println("▶️ GAME RESUMED");
    Serial.println("💡 Continue entering the sequence...");
  }
}

void startGame() {
  gameActive = true;
  gamePaused = false;  // NEW: Reset pause state
  score = 0;           // NEW: Reset score
  currentRound = 1;
  Serial.println("📊 Score reset to 0");
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
  if (gamePaused) return;  // NEW: Don't play sequence if paused
  
  int roundDelay = rounds[currentRound-1][1];
  
  Serial.println("💡 Playing LED sequence:");
  for(int i = 0; i < sequenceLength; i++) {
    if (gamePaused) break;  // NEW: Break if paused during playback
    
    Serial.print("   Step ");
    Serial.print(i + 1);
    Serial.print(": LED ");
    Serial.print(sequence[i] + 1);
    Serial.println(" [ON]");
    
    digitalWrite(ledPins[sequence[i]], HIGH);
    delay(roundDelay);
    
    Serial.print("   Step ");
    Serial.print(i + 1);
    Serial.print(": LED ");
    Serial.print(sequence[i] + 1);
    Serial.println(" [OFF]");
    
    digitalWrite(ledPins[sequence[i]], LOW);
    delay(roundDelay/2);
    if (gamePaused) return;
  }
}

void processInput(String input) {
  if (gamePaused) return;  // NEW: Don't process input if paused
  
  int number = input.toInt();
  
  if(number >= 1 && number <= numLeds) {
    int ledIndex = number - 1;
    
    Serial.print("You entered: ");
    Serial.println(number);
    
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
    Serial.println("GAME_LOST");
    Serial.println("📊 Final Score: " + String(score));  // NEW: Show final score
    gameLost();
    return;
  } else {
    Serial.println(" ✅ CORRECT!");
    score++;  // NEW: Increment score for correct guess
    Serial.println("📊 Score: " + String(score));  // NEW: Show updated score
  }
  
  currentStep++;
  
  if(currentStep == sequenceLength) {
    Serial.println("ROUND_WON");
    Serial.println("📊 Current Score: " + String(score));  // NEW: Show score
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
  
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], HIGH);
  }
  
  for(int i = 5; i > 0; i--) {
    Serial.print("⏰ Next round in: ");
    Serial.print(i);
    Serial.println(" seconds...");
    delay(1000);
  }
  
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], LOW);
  }
  
  if(currentRound < 3) {
    currentRound++;
    startRound();
  } else {
    Serial.println("GAME_WON");
    Serial.println("📊 Final Score: " + String(score) + "/" + String(getTotalPossibleScore()));  // NEW: Show final score
    gameWon();
  }
}

// NEW: Calculate total possible score
int getTotalPossibleScore() {
  int total = 0;
  for(int i = 0; i < 3; i++) {
    total += rounds[i][0];
  }
  return total;
}

void gameWon() {
  inputEnabled = false;
  Serial.println("🎉🎉🎉 CONGRATULATIONS! YOU WON THE ENTIRE GAME! 🎉🎉🎉");
  Serial.println("💡 All LEDs will stay ON for 30 seconds!");
  
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], HIGH);
  }
  
  for(int i = 30; i > 0; i--) {
    Serial.print("⏰ ");
    Serial.print(i);
    Serial.println(" seconds remaining...");
    delay(1000);
  }
  
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], LOW);
  }
  
  resetGame();
}

void gameLost() {
  inputEnabled = false;
  Serial.println("💥💥💥 GAME OVER! YOU LOST! 💥💥💥");
  Serial.println("💡 All LEDs will blink rapidly for 10 seconds!");
  
  unsigned long startTime = millis();
  bool ledState = false;
  
  while(millis() - startTime < 10000) {
    ledState = !ledState;
    for(int i = 0; i < numLeds; i++) {
      digitalWrite(ledPins[i], ledState ? HIGH : LOW);
    }
    delay(100);
  }
  
  for(int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], LOW);
  }
  
  resetGame();
}

void resetGame() {
  gameActive = false;
  gamePaused = false;  // NEW: Reset pause state
  inputEnabled = false;
  currentRound = 0;
  score = 0;           // NEW: Reset score
  Serial.println("\n🔄 Game Reset!");
  Serial.println("🎮 Type 'start' to play again.");
  Serial.println("=================================");
}