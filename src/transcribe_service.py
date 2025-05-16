# ******** project import
from common import FolderNames, Utility

# ******** external import
import requests, json
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import configparser
from datetime import datetime, time, timezone
from os import listdir, path
import json
import pytz
import time
import boto3
import re


# ******** schemas import
from models import RecordingBatchModel, RecordingModel


class TranscribeService:
    def __init__(self, config_file, config_name):
        self.session = None
        self.current_folder = path.dirname(path.abspath(__file__))
        config_file_path = path.join(self.current_folder, config_file)
        config = configparser.ConfigParser()
        config.read(config_file_path)
        self.config = config

        self.BUCKET_NAME = config[config_name]["BUCKET_NAME"]

    def load_aws_config(self):
        """Load AWS credentials from config file"""
        try:
            return {
                "aws_access_key_id": self.config["AWS"]["AWS_ACCESS_KEY_ID"],
                "aws_secret_access_key": self.config["AWS"]["AWS_SECRET_ACCESS_KEY"],
                "region_name": self.config["AWS"]["REGION"],
            }
        except Exception as e:
            print(f"Error reading config file: {str(e)}")
            return None

    def upload_to_s3(self, file_name, bucket, object_name=None):
        """Upload a file to an S3 bucket"""
        if object_name is None:
            object_name = file_name

        aws_config = self.load_aws_config()
        if not aws_config:
            return False
        print(aws_config)
        s3_client = boto3.client("s3", **aws_config)
        try:
            response = s3_client.upload_file(file_name, bucket, object_name)
            print(f"Successfully uploaded to S3: {file_name} -> {bucket}/{object_name}")
            print(response)
        except NoCredentialsError:
            print("Error: Credentials not found.")
            return False
        except PartialCredentialsError:
            print("Error: Incomplete credentials.")
            return False
        except Exception as e:
            print(f"Error uploading to S3: {str(e)}")
            return False
        return True

    def start_transcription_job(
        self, job_name, bucket, file_name, file_extension, language_code="en-US"
    ):
        """Start a transcription job in AWS Transcribe"""
        aws_config = self.load_aws_config()
        if not aws_config:
            return False

        transcribe_client = boto3.client("transcribe", **aws_config)

        try:
            response = transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": f"s3://{bucket}/{file_name}"},
                MediaFormat=file_extension,
                LanguageCode=language_code,
                Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": 2},
            )
            print("Transcription job started.")
        except Exception as e:
            print(f"Error starting transcription job: {str(e)}")

    def check_transcription_job(self, job_name):
        """Check the status of the transcription job"""
        aws_config = self.load_aws_config()
        if not aws_config:
            return False

        transcribe_client = boto3.client("transcribe", **aws_config)

        while True:
            response = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            status = response["TranscriptionJob"]["TranscriptionJobStatus"]

            print(f"Job status: {status}")

            if status in ["COMPLETED", "FAILED"]:
                break

            time.sleep(10)

        if status == "COMPLETED":
            transcript_uri = response["TranscriptionJob"]["Transcript"][
                "TranscriptFileUri"
            ]
            return transcript_uri
        return None

    def download_transcript(self, transcript_uri, file_name):
        """Download the transcript from the provided URI"""
        import requests

        response = requests.get(transcript_uri)
        if response.status_code == 200:
            with open(file_name, "w") as f:
                f.write(response.text)
            print("Transcript downloaded successfully.")
        else:
            print("Failed to download transcript.")

    ################ handle transciprt ###############

    # region handle transciprt
    def convert_format_text(self, filename, output_filename):
        with open(filename, "r") as file, open(output_filename, "w") as output_file:
            transcript_data = json.load(file)
            for segment in transcript_data["data"]:
                output_file.write(
                    f"[{segment['start_time']}-{segment['end_time']}] {segment['speaker_label']}: {segment['transcript']}\n"
                )

    def keep_only_audio_segments(self, filename):
        # read json file
        with open(filename, "r") as file:
            transcript_data = json.load(file)
        # Iterate through elements in `audio_segments` and remove the `items` field
        for segment in transcript_data["results"]["audio_segments"]:
            if "items" in segment:
                del segment["items"]
        # keep only the ['results']['audio_segments'] field and remove the whole JSON file
        transcript_data = transcript_data["results"]["audio_segments"]

        # save the modified data to the transcript.json file
        with open(filename, "w") as file:
            json.dump({"data": transcript_data}, file, indent=4)

    # endregion

    # ********************************************************************************************************
    # Process
    # ********************************************************************************************************
    def process(self, recording: RecordingModel):
        file_name = Utility.remove_audio_extension(recording.document_name)
        AUDIO_FILE = recording.recording_file_path
        SCRIPT_FOLDER_DOWNLOAD = f"{FolderNames.TRANSCRIPT.value}/{file_name}.json"
        SCRIPT_FOLDER_DOWNLOAD_TEXT = f"{FolderNames.TRANSCRIPT.value}/{file_name}.txt"

        job_name = f"ai_sale_transcription_job_{file_name.strip()}{int(time.time())}"
        # Remove any characters that don't match the allowed pattern

        job_name = re.sub(r"[^0-9a-zA-Z._-]", "", job_name)
        # Ensure job name is not empty after cleaning
        if not job_name:
            job_name = f"ai_sale_transcription_job_{int(time.time())}"

        if self.upload_to_s3(
            path.join(self.current_folder, AUDIO_FILE), self.BUCKET_NAME
        ):
            self.start_transcription_job(
                job_name=job_name,
                bucket=self.BUCKET_NAME,
                file_name=path.join(self.current_folder, AUDIO_FILE),
                file_extension=recording.file_extension,
            )
            # Check the status of the transcription job
            transcript_uri = self.check_transcription_job(job_name)
            if transcript_uri:
                # Download the transcript
                self.download_transcript(
                    transcript_uri,
                    path.join(self.current_folder, SCRIPT_FOLDER_DOWNLOAD),
                )

                # convert format text
                self.keep_only_audio_segments(
                    path.join(self.current_folder, SCRIPT_FOLDER_DOWNLOAD)
                )
                # remove_speaker_label_that_appears_least(FILENAME_JSON)
                self.convert_format_text(
                    path.join(self.current_folder, SCRIPT_FOLDER_DOWNLOAD),
                    path.join(self.current_folder, SCRIPT_FOLDER_DOWNLOAD_TEXT),
                )
                time.sleep(5)
