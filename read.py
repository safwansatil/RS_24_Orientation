import serial
import serial.tools.list_ports
import time

def read_and_write_serial():
    # --- 1. Port Selection ---
    ports = serial.tools.list_ports.comports()
    ports_info = {}

    print("Available Ports:")
    if not ports:
        print("No serial ports found. Please ensure your Arduino is plugged in.")
        return

    for i, onePort in enumerate(ports):
        port_name = onePort.device
        port_desc = f"{onePort.description} ({port_name})"
        ports_info[i] = port_name
        print(f"  {i+1}: {port_desc}")

    try:
        selection = input("Select Port Number: ")
        port_index = int(selection) - 1

        if port_index not in ports_info:
            print("Invalid selection. Exiting.")
            return

        selected_port = ports_info[port_index]
        print(f"Connecting to: {selected_port}")

    except ValueError:
        print("Invalid input. Please enter a number.")
        return

    # --- 2. Serial Connection and Communication Loop ---
    serialInst = None
    
    try:
        # Open the serial connection
        serialInst = serial.Serial(
            port=selected_port, 
            baudrate=9600, 
            timeout=1
        )
        
        # Give the Arduino time to reset after the connection is opened
        time.sleep(2) 
        
        print("\n✅ Serial connection established. Reading data...")
        print("   Press Ctrl+C to stop.")
        
        # Flag to determine if we should be waiting for user input 
        # (after the Arduino has finished showing the sequence and asks for the first number)
        waiting_for_user_input = False
        
        while True:
            # A. Check for incoming data from Arduino
            if serialInst.in_waiting:
                packet = serialInst.readline()
                try:
                    decoded_data = packet.decode('utf-8').strip()
                    print(decoded_data)
                    
                    # Set the flag when the Arduino is prompting for input
                    if "Enter the sequence" in decoded_data or "Next number" in decoded_data:
                        waiting_for_user_input = True
                        
                except UnicodeDecodeError:
                    print("[Could not decode data: Non-text bytes received]")
            
            # B. Check if it's time to send data to Arduino (from user)
            if waiting_for_user_input:
                try:
                    user_input = input(">> Your Input (1-5): ")
                    
                    if user_input in ('1', '2', '3', '4', '5'):
                        # Send the number as bytes, terminated with a newline ('\n') 
                        # for the Arduino's Serial.parseInt() function.
                        serialInst.write((user_input + '\n').encode('utf-8'))
                        
                        # Reset the flag immediately after sending a valid input
                        waiting_for_user_input = False 
                    else:
                        print("Invalid input. Please enter a number between 1 and 5.")
                except EOFError:
                    # Catch Ctrl+Z/D/etc.
                    print("\nExiting due to unexpected input event.")
                    break
                    
            # Small delay to keep the loop efficient
            time.sleep(0.01)

    except serial.SerialException as e:
        print(f"\n❌ Error: Failed to open or communicate with port {selected_port}.")
        if "PermissionError" in str(e):
            print("   The port is likely in use by another program (e.g., Arduino Serial Monitor).")
        else:
            print(f"   Details: {e}")

    except KeyboardInterrupt:
        print("\n\nSession terminated by user (Ctrl+C).")

    finally:
        # --- 3. Close Port ---
        if serialInst and serialInst.is_open:
            print(f"Closing port {serialInst.port}...")
            serialInst.close()

if __name__ == "__main__":
    read_and_write_serial()