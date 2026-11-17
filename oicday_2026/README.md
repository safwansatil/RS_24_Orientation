# Reaction Duel

Two players race to press after a shared green light. The higher score after seven rounds wins. Early presses, ties within 2 ms, and rounds with no response in 3 seconds use up a round and earn no points. Equal scores after the seventh round end the contest in a draw. The seven slots above the arena show who won each round. A dash means no point was awarded.

## Run it on the laptop

Use Python 3.10 or newer with Tkinter. From this folder, run:

```powershell
python -m pip install -r requirements.txt
python game.py
```

Enter the player names and select **Start**. Keyboard mode uses **A** and **L** and works without an Arduino. Press **F11** to toggle fullscreen and **Esc** to leave fullscreen. Use **Setup** to stop a match and edit names. **Play Again** keeps the names and clears the results.

## Wire the Arduino

This pin map assumes a 5 V Uno R3. Unplug USB while wiring. Put the shared LED where both players can see it and give each player a normally open momentary pushbutton.

| Component | Connection |
| --- | --- |
| Cue LED | D8 → 220 Ω resistor → LED anode (long leg). LED cathode (short leg) → GND. |
| Player 1 button | D9 → one switch contact. Other contact → GND. |
| Player 2 button | D10 → one switch contact. Other contact → GND. |
| Optional 5 V active-high buzzer module | D11 → signal, 5V → module power, GND → module ground. |

Use a shared ground. The firmware uses `INPUT_PULLUP`, so an open button reads HIGH and a press reads LOW. With a four-leg tactile switch, identify the two switch contacts with a continuity meter if the pinout is unclear. Connect one leg from each switched pair.

The buzzer is off by default. Set `useBuzzer` to `true` in the sketch to enable a 90 ms beep. The pin map assumes a module with a logic-level signal input and its own driver. Check the current rating and driver requirements of a bare buzzer before connecting it.

## Use physical buttons

1. Open `reaction_duel/reaction_duel.ino` in Arduino IDE. Select **Arduino Uno** and the actual USB port, then upload the sketch. The original memory game sketch remains in its own folder. Uploading this sketch replaces whichever program is currently on the board.
2. Close Arduino Serial Monitor if it is open. Launch `game.py`, open **Input**, select your port, and click **USB**. If the port appeared after launch, use the refresh arrow.
3. Once the screen says **Arduino ready**, start a match. In USB mode the physical light is the cue to watch. The screen mirrors it over serial.

## Project layout

| File | Role |
| --- | --- |
| `game.py` | Tkinter cabinet, name entry, keyboard mode, and GIF playback. |
| `match.py` | Round state, scorekeeping, and validation of incoming events. |
| `connection.py` | USB serial worker and board identification handshake. |
| `reaction_duel/reaction_duel.ino` | Physical cue, non-blocking round timing, button debounce, and winner detection. |
| `art/` | Two original animated competitors for the arena. |

The laptop owns names and match scores. The Arduino owns physical timing and reports one result per round. Communication uses ASCII lines at 115200 baud. The laptop sends `HELLO`, `ARM,<round id>`, and `CANCEL`. The board identifies itself with `REACTION_DUEL,1`, then reports `RELEASE`, `WAIT`, `GO`, or `RESULT` with the round ID. A result is `RESULT,<id>,<WIN|EARLY|TIE|MISS>,<player>,<milliseconds>`. Player 0 means neither player won or both jumped early. Reaction time is reported only for a winning press.
