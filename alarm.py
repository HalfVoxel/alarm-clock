from __future__ import print_function
from __future__ import division
from pyo import *
import time
from datetime import datetime, timedelta
from dateutil import parser
import os
#import accel
import math
import random
import sys
import select

# Make this a high priority process
# os.nice(-10)

#wakeTime = datetime.now() + timedelta(0, 20)
wakeTime = None
stoppedTime = datetime.utcnow()
wake_coroutine = None
coroutines = []


def start_coroutine(f):
    coroutines.append([datetime.now(), f])


def is_started(coroutine):
    for pair in coroutines:
        if pair[1] == coroutine:
            return True
    return False


def tick():
    current_coroutines = coroutines[:]
    for c in current_coroutines:
        if datetime.now() > c[0]:
            try:
                c[0] = datetime.now() + timedelta(0, next(c[1]))
            except StopIteration:
                coroutines.remove(c)


def monitor():
    while True:
        #gyro, acc = accel.get()
        # print("{0:.6f} {1:.6f} {2:.6f}".format(acc[0], acc[1], acc[2]))
        #item = (datetime.now(), gyro, acc)
        #print(item)
        yield 0.05


def alarm_time_has_passed():
    return wakeTime is not None and datetime.utcnow() >= wakeTime


def stop():
    global wakeTime, stoppedTime
    wakeTime = None
    stoppedTime = datetime.utcnow()


def wake_monitor():
    global wakeTime, stoppedTime, wake_coroutine
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            # New data on stdin
            command = sys.stdin.readline().strip()
            try:
                parts = command.split(' ')
                command = parts[0]
                if parts[0] == "SETTIME":
                    wakeTime = parser.parse(parts[1])
                    stoppedTime = None
                    print("Received new wake time: " + str(wakeTime))
                if command == "PLAY":
                    stoppedTime = None
                    play(" ".join(parts[1:]) if len(parts) > 1 else None)
                elif command == "STOP":
                    print("Received stop command")
                    stop()
                else:
                    print("Invalid command: " + command)
            except Exception as e:
                print("Invalid command\n" + str(e))

        if alarm_time_has_passed() and not is_started(wake_coroutine):
            play()

        if stoppedTime is not None and datetime.utcnow() >= stoppedTime + timedelta(seconds=30):
            print("Exiting...", file=sys.stderr)
            sys.exit(0)

        yield 2

def play(sound):
    print("Waking...")
    if sound is None:
        sound = get_audio("audio")
    wake_coroutine = wake_up(sound)
    start_coroutine(wake_coroutine)

def frquency_cutoff_lp(t):
    t = max(t - 10, 0)
    return min(100000, 800 + math.pow(t, 2.5) * 1.0)


def reverb_balance(t):
    return 0.5 / (t * 0.03 + 1)


def volume(t):
    return min(1, 0.0 + 0.007*t + max(0, t - 5) * 0.013)


def get_audio(path):
    alternatives = [file for file in os.listdir(path) if file.endswith(".aiff") or file.endswith(".flac")]
    return path + "/" + random.choice(alternatives)


def wake_up(sound_file_path):
    print("Playing: " + sound_file_path)
    s = Server(duplex=0, buffersize=1024)
    # pa_list_devices()
    # s.setInOutDevice(3)
    s.boot()

    t = SndTable(sound_file_path)
    # sf = SfPlayer(path, speed=[1, 1], loop=True, mul=0.8)
    # Avoid clipping => mul < 1
    sf = Osc(table=t, freq=t.getRate(), mul=0.9)
    but = ButLP(sf)
    verb = Freeverb(but, size=0.4, damp=0.6)
    verb.out()

    t = 0
    dt = 0.1
    alarm_timeout = 120
    while t < alarm_timeout:
        but.setFreq(frquency_cutoff_lp(t))
        # but2.setFreq(frquency_cutoff_hp(t))
        #verb.setBal(reverb_balance(t))
        s.amp = volume(t)
        time.sleep(dt)

        if t == 0:
            # Start the server in the first iteration after the
            # settings have been set
            s.start()

        t += dt
        yield dt

    t = 0
    while t < 6:
        s.amp *= math.pow(0.4, dt)
        t += dt
        yield dt

    print("Stopping audio server...", file=sys.stderr)
    if alarm_time_has_passed():
        stop()


start_coroutine(monitor())
start_coroutine(wake_monitor())

while True:
    tick()
    time.sleep(0.01)
