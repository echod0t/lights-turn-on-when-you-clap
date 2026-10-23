from sensor.sensor import detect_clap
import time


light_on = False

clap_count = 0
last_clap_time = 0

CLAP_WINDOW = 1.5


def turn_light_on():
    global light_on

    light_on = True
    print("LIGHT ON")


def turn_light_off():
    global light_on

    light_on = False
    print("LIGHT OFF")


def main():
    global clap_count
    global last_clap_time

    print("Assistant running...")
    print()
    print("= LIGHT ON")
    print("= LIGHT OFF")
    print()

    while True:

        if detect_clap():

            current_time = time.time()

            # Start a new sequence if too much time has passed
            if current_time - last_clap_time > CLAP_WINDOW:
                clap_count = 0

            clap_count += 1
            last_clap_time = current_time

            print(
                "Clap count:",
                clap_count
            )

            if clap_count == 2:
                turn_light_on()

            
            elif clap_count == 3:
                turn_light_off()
                clap_count = 0


if __name__ == "__main__":
    main()
