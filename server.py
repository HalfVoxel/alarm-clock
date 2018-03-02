from flask import Flask, request, abort
from flask_compress import Compress
from dateutil import parser
from subprocess import Popen, PIPE
import json

app = Flask(__name__)
Compress(app)

alarmTime = parser.parse("2000-01-01 07:00")
alarmEnabled = False

alarmProcess = None

@app.route("/get", methods=["POST"])
def get():
    data = decode(request)
    authenticate(data)

    return json.dumps({
        "time": alarmTime.isoformat(),  # .strftime("%Y-%m-%dT%H:%M:%S"),
        "enabled": alarmEnabled
    })


def decode(request):
    try:
        return json.loads(request.data.decode('utf-8'))
    except Exception as e:
        print(e)
        abort(422)


def authenticate(data):
    try:
        if str(data["secret"]).strip() != open("./.secret").read().strip():
            abort(403)
    except:
        abort(403)


@app.route("/store", methods=["POST"])
def store():
    global alarmTime, alarmEnabled
    data = decode(request)
    authenticate(data)

    try:
        alarmTime = parser.parse(data["time"])
        alarmEnabled = bool(data["enabled"])
        print(alarmEnabled, alarmTime, data["time"])
        if alarmEnabled:
            startAlarm(alarmTime)
        else:
            stopAlarm()
    except Exception as e:
        print(e)
        abort(422)

    return "{}"


def startAlarm(time):
    global alarmProcess
    print(str(alarmProcess is None))

    if alarmProcess is not None:
        alarmProcess.poll()

    if alarmProcess is None or alarmProcess.returncode is not None:
        alarmProcess = Popen(["python", "alarm.py"], stdin=PIPE, bufsize=-1)

    alarmProcess.stdin.write(("SETTIME " + time.isoformat() + "\n").encode('utf-8'))
    alarmProcess.stdin.flush()

def stopAlarm():
    global alarmProcess

    if alarmProcess is not None:
        alarmProcess.poll()

    if alarmProcess is not None and alarmProcess.returncode is None:
        alarmProcess.stdin.write("STOP\n".encode('utf-8'))
        alarmProcess.stdin.flush()

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False, port=8000)
