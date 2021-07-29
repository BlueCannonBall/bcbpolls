from flask import Flask, request, send_from_directory
import string, random, json, hashlib, waitress, logging, os, html, threading

logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)

db_lock = threading.Lock()

def load_polls():
    db_lock.acquire()
    polls_file = open("polls.json", "r")
    data = None
    try:
        data = json.loads(polls_file.read())
    except json.decoder.JSONDecodeError:
        data = {}
    polls_file.close()
    db_lock.release()
    return data

def save_polls(content):
    db_lock.acquire()
    polls_file = open("polls.json", "w")
    polls_file.write(json.dumps(content))
    polls_file.close()
    db_lock.release()

def load_accounts():
    db_lock.acquire()
    accounts_file = open("accounts.json", "r")
    data = None
    try:
        data = json.loads(accounts_file.read())
    except json.decoder.JSONDecodeError:
        data = {}
    accounts_file.close()
    db_lock.release()
    return data

def save_accounts(content):
    db_lock.acquire()
    accounts_file = open("accounts.json", "w")
    accounts_file.write(json.dumps(content))
    accounts_file.close()
    db_lock.release()

def gen_code(length):
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

app = Flask(__name__, static_url_path='')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Load polls
polls = None
try:
    polls = load_polls()
except FileNotFoundError:
    polls = {}

# Load accounts
accounts = None
try:
    accounts = load_accounts()
except FileNotFoundError:
    accounts = {}

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers["Access-Control-Allow-Origin"] = "*";
    return r

@app.route("/")
def send_index():
  return send_from_directory("static", "index.html")

@app.route("/api/signup", methods=['POST', 'GET'])
def signup():
    if html.escape(request.args['username']) in accounts:
        return "Imagine signing up twice", 400
    accounts[html.escape(request.args['username'])] = hashlib.sha256(request.args['password'].encode()).hexdigest()
    save_accounts(accounts);

    return "Successfully signed up", 200

@app.route("/api/login", methods=['POST', 'GET'])
def login():
    if html.escape(request.args['username']) not in accounts:
        return "Imagine logging into a nonexistent account", 400
    
    if accounts[html.escape(request.args['username'])] == hashlib.sha256(request.args['password'].encode()).hexdigest():
        return "Successfully logged in", 200

    return "Wrong password 😂", 401

@app.route("/api/createPoll", methods=['POST'])
def create_poll():
    if html.escape(request.args['username']) in accounts:
        if hashlib.sha256(request.args['password'].encode()).hexdigest() != accounts[html.escape(request.args['username'])]:
            return "Incorrect password", 403
    else:
        return "Log in or sign up please", 401

    c = None
    while True:
        c = gen_code(6)
        if c in polls:
            continue
        else:
            break

    polls[c] = {
        "topic": html.escape(request.json["topic"]),
        "owner": html.escape(request.args['username']),
        "results": {}
    }
    for option in request.json["options"]:
        polls[c]["results"][html.escape(option)] = []

    save_polls(polls)
    return c

@app.route("/api/deletePoll", methods=['POST', 'GET'])
def delete_poll():
    if html.escape(request.args['username']) in accounts:
        if hashlib.sha256(request.args['password'].encode()).hexdigest() != accounts[html.escape(request.args['username'])]:
            return "Incorrect password", 403
    else:
        return "Log in or sign up please", 401

    c = request.args["code"]
    if html.escape(request.args['username']) != polls[c]["owner"]:
        return "You don't own this poll", 403
    del polls[c]

    save_polls(polls)
    return f"Successfully deleted poll {c}"

@app.route("/api/pollInfo")
def get_poll_info():
    c = request.args["code"]

    if c not in polls:
        return "Poll does not exist", 400

    poll_info = {
        "topic": polls[c]["topic"],
        "results": {},
    }

    results = {}
    for option in polls[c]["results"]:
        results[option] = len(polls[c]["results"][option])
    poll_info["results"] = results

    return json.dumps(poll_info)

@app.route("/api/vote", methods=['POST', 'GET'])
def vote():
    if html.escape(request.args['username']) in accounts:
        if hashlib.sha256(request.args['password'].encode()).hexdigest() != accounts[html.escape(request.args['username'])]:
            return "Incorrect password", 403
    else:
        return "Log in or sign up please", 401

    c = request.args["code"]
    if html.escape(request.args['username']) in polls[c]["results"][request.args["option"]]:
        return "You already voted for that option smh my head", 409

    for option in polls[c]["results"]:
        polls[c]["results"][option][:] = [user for user in polls[c]["results"][option] if user != html.escape(request.args['username'])]

    if request.args["option"] not in polls[c]["results"]:
        return "Please vote for a legit option", 400

    polls[c]["results"][request.args["option"]].append(html.escape(request.args['username']))

    save_polls(polls)
    return f"Successfully voted: {request.args['option']}"

@app.route("/api/unvote", methods=['POST', 'GET'])
def unvote():
    if html.escape(request.args['username']) in accounts:
        if hashlib.sha256(request.args['password'].encode()).hexdigest() != accounts[html.escape(request.args['username'])]:
            return "Incorrect password", 403
    else:
        return "Log in or sign up please", 401

    c = request.args["code"]
    for option in polls[c]["results"]:
        polls[c]["results"][option][:] = [user for user in polls[c]["results"][option] if user != html.escape(request.args['username'])]

    save_polls(polls)
    return "Removed vote"

if __name__ == '__main__':
    waitress.serve(app, host="0.0.0.0", port=int(os.environ["PORT"]))
