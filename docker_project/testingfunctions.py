import boto3

s3_client = boto3.client('s3')

s3_client.upload_file(
    Filename='yolo5/saveimage/img.png',
    Bucket='dockerprojectbucket',
    Key='imagesafterprediction/abcd.png'
)