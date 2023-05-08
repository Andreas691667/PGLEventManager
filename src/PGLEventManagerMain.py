from threading import Event
import keyboard
from PGLEventManagerModel import PGLEventManagerModel
from PGLEventManagerController import PGLEventManagerController

def main():
    print("Press 'x' to terminate")

    model = PGLEventManagerModel("localhost", "PGL", "PGL", "PGL")
    controller = PGLEventManagerController("test.mosquitto.org", model)

    controller.startListening()

    try:
        while True:
            pass

    except KeyboardInterrupt:
        print("Exiting")
        controller.stopListening()


if __name__ == "__main__":
    main()
