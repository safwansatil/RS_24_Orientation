"""Serial transport. Only the Tk thread reads events or changes the match."""
from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic


def available_ports():
    try:
        from serial.tools.list_ports import comports
    except ImportError:
        return []
    return [port.device for port in sorted(comports())]


class Board:
    def __init__(self, port):
        self.inbox = Queue()
        self.outbox = Queue()
        self.stopped = Event()
        Thread(target=self._run, args=(port,), daemon=True).start()

    def send(self, command):
        self.outbox.put(command)

    def close(self):
        self.stopped.set()

    def _run(self, port):
        try:
            import serial

            with serial.Serial(port, 115200, timeout=0.03, write_timeout=0.25) as link:
                deadline = monotonic() + 7
                next_hello = 0
                ready = False
                pending = b""
                try:
                    while not self.stopped.is_set():
                        now = monotonic()
                        if not ready:
                            if now >= deadline:
                                raise RuntimeError("Reaction Duel sketch did not answer")
                            if now >= next_hello:
                                link.write(b"HELLO\n")
                                next_hello = now + 0.4
                        else:
                            try:
                                command = self.outbox.get_nowait()
                            except Empty:
                                pass
                            else:
                                link.write((command + "\n").encode("ascii"))

                        pending += link.read_until(b"\n", 96)
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            message = line.decode("ascii", errors="replace").strip()
                            if message == "REACTION_DUEL,1" and not ready:
                                link.write(b"CANCEL\n")
                                ready = True
                                self.inbox.put(("connected", port))
                            elif ready:
                                self.inbox.put(("line", message))
                        if len(pending) > 256:
                            pending = b""
                finally:
                    if ready:
                        link.write(b"CANCEL\n")
        except ImportError:
            self.inbox.put(("error", "Install pyserial to connect the Arduino"))
        except Exception as error:
            self.inbox.put(("error", str(error)))
