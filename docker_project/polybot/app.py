import flask
from flask import request
import os
from bot import ObjectDetectionBot, Bot,QuoteBot
from loguru import logger

app = flask.Flask(__name__)

os.environ['TELEGRAM_TOKEN'] = '6317053123:AAG6RX591M9_bPdz0ULtDL0EfbRdsXhQ50Y'
os.environ['TELEGRAM_APP_URL'] = 'https://fa9b-2a06-c701-4f9d-3700-f8ba-2b86-30a2-b160.ngrok-free.app'


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route('/6317053123:AAG6RX591M9_bPdz0ULtDL0EfbRdsXhQ50Y/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])

    return 'Ok'


if __name__ == "__main__":

    bot = ObjectDetectionBot(os.environ['TELEGRAM_TOKEN'], os.environ['TELEGRAM_APP_URL'] )


    app.run(debug=True,host='0.0.0.0', port=8443)
