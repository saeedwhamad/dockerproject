import uuid

import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
import boto3
import requests



class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )
    def summary(self,prediction_summry):
        # Count occurrences of each class
        object_counts = {}
        for obj in prediction_summry.json()["labels"]:
            obj_class = obj['class']
            object_counts[obj_class] = object_counts.get(obj_class, 0) + 1

        # Generate the desired output
        output = "Detected objects:"
        for obj_class, count in object_counts.items():
            output += f" {obj_class} {count},"

        # Remove the trailing comma and display the result

        output = output.rstrip(',')
        output = output.replace(', ', '\n')
        output = output.replace(': ', ':\n')
        return output

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        if 'message' in msg and 'text' in msg['message']:
         if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])





class ObjectDetectionBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if self.is_current_msg_photo(msg):
            pass
            # TODO download the user photo (utilize download_user_photo)
            downloadedphotopath=Bot.download_user_photo(self,msg)
            logger.info("photo is downloaded")

            image_id = str(uuid.uuid4())
            imageName=f'Image_{image_id}.png'
            # TODO upload the photo to S3
            s3 = boto3.client('s3')
            s3.upload_file(downloadedphotopath,"dockerprojectbucket",imageName)
            logger.info("photo is uploaded !!! ")


            # TODO send a request to the `yolo5` service for prediction

            try:
                # TODO: Send a request to the `yolo5` service for prediction
                url = 'http://yolo:8080/predict'
                data = {'imgName': imageName}

                prediction_result = requests.post(url, params=data)
                logger.info("Request is sent")

                # Check if the request was successful (status code 200)
                if prediction_result.status_code == 200:
                  output = Bot.summary(self, prediction_result)
                else:
                    logger.error(f"Request failed with status code: {prediction_result.status_code}")
                    output = "unable to detect objects"

            except requests.RequestException as e:
                logger.error(f"Request Error: {e}")


            # TODO send results to the Telegram end-user
            Bot.send_text(self,msg['chat']['id'],output)
            logger.info("result is send")

        else:
         logger.info("message is not photo")