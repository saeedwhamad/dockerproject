import time
from pathlib import Path
from flask import Flask, request
from detect import run
import uuid
import yaml
from loguru import logger
import os
import boto3
from pymongo import MongoClient
import json



os.environ['BUCKET_NAME'] = 'dockerprojectbucket'

with open("data/coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello'
@app.route('/status')
def status():
    return 'OK'


@app.route('/predict', methods=['POST'])
def predict():
    # Generates a UUID for this current prediction HTTP request. This id can be used as a reference in logs to identify and track individual prediction requests.
    prediction_id = str(uuid.uuid4())

    logger.info(f'prediction: {prediction_id}. start processing')

    # Receives a URL parameter representing the image to download from S3
    img_name = request.args.get('imgName')

    # TODO download img_name from S3, store the local image path in original_img_path
    #  The bucket name should be provided as an env var BUCKET_NAME.
    directory_path = '/yolo'
    # Use os.makedirs to create the directory and its parent directories if they don't exist
    os.makedirs(directory_path, exist_ok=True)

    original_img_path = f'{prediction_id}_downloaded_img.png'


    s3_resource = boto3.resource('s3')

    # Download image from S3 bucket
    s3 = boto3.client(
        's3'
    )
    s3.download_file(os.environ['BUCKET_NAME'], img_name, original_img_path)

    logger.info(f'Prediction ID: {prediction_id}. Image downloaded from S3.')



    # Predicts the objects in the image
    run(
        weights='yolov5s.pt',
        data='data/coco128.yaml',
        source=original_img_path,
        project='static/data',
        name=prediction_id,
        save_txt=True
    )

    logger.info(f'prediction: {prediction_id}/{original_img_path}. done')

    # This is the path for the predicted image with labels
    # The predicted image typically includes bounding boxes drawn around the detected objects, along with class labels and possibly confidence scores.
    predicted_img_path = Path(f'static/data/{prediction_id}/{original_img_path}')


    # TODO Uploads the predicted image (predicted_img_path) to S3 (be careful not to override the original image).

    s3.upload_file(predicted_img_path, os.environ['BUCKET_NAME'], f'imagesafterprediction/predicted_{img_name}')
    logger.info(f'Prediction ID: {prediction_id}. Predicted image uploaded to S3.')

    # Parse prediction labels and create a summary
    pred_summary_path = Path(f'static/data/{prediction_id}/labels/{original_img_path.split(".")[0]}.txt')
    if pred_summary_path.exists():
        with open(pred_summary_path) as f:
            labels = f.read().splitlines()
            labels = [line.split(' ') for line in labels]
            labels = [{
                'class': names[int(l[0])],
                'cx': float(l[1]),
                'cy': float(l[2]),
                'width': float(l[3]),
                'height': float(l[4]),
            } for l in labels]

        logger.info(f'prediction: {prediction_id}/{original_img_path}. prediction summary:\n\n{labels}')

        prediction_summary = {
            'prediction_id': prediction_id,
            'original_img_path': str(original_img_path),
            'predicted_img_path': str(predicted_img_path),
            'labels': labels,
            'time': time.time()
        }

        # TODO store the prediction_summary in MongoDB
        mongo_client = MongoClient('http://mongo1:27017/')
        db = mongo_client['prediction_db']
        collection = db['prediction_collection']

        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""

            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            if isinstance(obj, ObjectId):
                return str(obj)
            raise TypeError("Type %s not serializable" % type(obj))


        json_data = json.dumps(prediction_summary, default=json_serial)
        parsed_data = json.loads(json_data)

        collection.insert_one(parsed_data)

        logger.info('data is inserted to mongoDB')

        return prediction_summary
    else:
        return f'prediction: {prediction_id}/{original_img_path}. prediction result not found', 404


if __name__ == "__main__":
    app.run(debug=True, port=8080, host='0.0.0.0')


