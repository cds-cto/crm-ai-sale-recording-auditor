import boto3
import configparser
import os


class S3Connect:
    def __init__(self, config_file: str, config_name: str):
        # config load
        current_folder = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_folder, config_file)
        config = configparser.ConfigParser()
        config.read(config_file_path)

        # define class value
        self.aws_access_key_id = config[config_name]["aws_access_key_id"]
        self.aws_secret_access_key = config[config_name]["aws_secret_access_key"]
        self.bucket_name = config[config_name]["bucket_name"]
        self.folder_name = config[config_name]["folder_name"]

    # create client here
    def createClient(self):
        # Create an S3 client
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    # close client
    def closeClient(self):
        # Close the S3 client
        self.s3.close()
        print("S3 client closed")

    # upload object
    def uploadObj(
        self,
        file_obj,
        file_name: str,
    ):
        self.createClient()
        # Upload the file
        s3_file_key = self.folder_name + "/" + file_name
        res = self.s3.upload_fileobj(file_obj, self.bucket_name, s3_file_key)
        print(f"{file_name} uploaded to {self.bucket_name}/{self.folder_name} ")
        self.closeClient()

    # download file
    def downloadFile(self):
        self.createClient()
        file_key = "recordings/a9ba407d3b1a45de9a7a5d2e64223319.mp3"
        local_file_path = "downloaded_audio.mp3"  # Specify the local file path
        self.s3.download_file(self.bucket_name, file_key, local_file_path)
        self.closeClient()

    # check file existed
    def checkFileExists(self, file_name):
        self.createClient()
        s3_file_key = f"{self.folder_name}/{file_name}"
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=s3_file_key)
            self.closeClient()
            return True  # The file exists
        except:
            self.closeClient()
            return False  # The file doesn't exist

    # upload a file from a local path
    def uploadFile(self, local_file_path: str, s3_file_name: str):
        self.createClient()
        s3_file_key = f"{self.folder_name}/{s3_file_name}"
        self.s3.upload_file(local_file_path, self.bucket_name, s3_file_key)
        print(f"{s3_file_name} uploaded to {self.bucket_name}/{self.folder_name}")
        self.closeClient()
