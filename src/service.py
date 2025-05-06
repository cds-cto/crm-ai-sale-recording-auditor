# ******* External Imports
import requests
import configparser
import os
from datetime import datetime, timedelta, timezone
import re
import json
import pytz

# ******* Project Imports
from constant import TRANSACTION_CODES
from gpt_service import GPTService
from crm_api_service import CrmAPIService
from mongoDB import MongoConnect
from models import RecordingBatchModel, RecordingModel
from reporting_service import ReportingService
from transcribe_service import TranscribeService
from validation_service import ValidationService


class AISaleService:
    def __init__(self):
        self.current_folder = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_folder, "config.ini")
        config = configparser.ConfigParser()
        config.read(config_file_path)
        self.TRANS_CODE = TRANSACTION_CODES()

    # ********************************************************************************************************
    # Get External IP
    # ********************************************************************************************************

    def _get_external_ping(self):
        r = requests.Session()
        res = r.get("https://curlmyip.org/", verify=False)
        print(res.text)

    # ********************************************************************************************************
    # Process
    # ********************************************************************************************************

    def process(self):
        # ******** get external IP
        self._get_external_ping()

        # ********  Init Mongo DB
        self.ai_sale_logs = MongoConnect(
            config_file="config.ini",
            config_name="AI_SALE_LOGS",
        )

        # ********  Init transcription Service
        self.transcribe_service = TranscribeService(
            config_file="config.ini", config_name="AWS"
        )

        # ********  Init CRM API Service
        self.crm_api_service = CrmAPIService(
            config_file="config.ini", config_name="CRM"
        )

        # ********  Init Validation Service
        self.validation_service = ValidationService()

        # ********  Init GPT Service
        self.gpt_service = GPTService(config_file="config.ini", config_name="OPENAI")

        # ********  Init Reporting Service
        self.reporting_service = ReportingService()

        # ********  Init batch model
        recordings = RecordingBatchModel(batch=[])

        # ********  Get Recordings
        self.crm_api_service.get_recordings(Recordings=recordings)

        print("************************************************************")

        self.handleTask(recordings=recordings)

    # ********************************************************************************************************
    # Solo Handling
    # ********************************************************************************************************
    def handling(self, recording: RecordingModel):
        # ********  Check existing in mongo
        if self.ai_sale_logs.collection.find_one(
            {"document_id": recording.document_id}
        ):
            return self.TRANS_CODE.GENERAL.ERROR_CODE.X100

        # ******** validate audio file
        if not self.validation_service.valid_audio_file(
            file_path=recording.document_name
        ):
            return self.TRANS_CODE.GENERAL.ERROR_CODE.F101

        # ********  Get Recording URL
        recording.recording_url = self.crm_api_service.get_recordings_url(
            document_id=recording.document_id
        )

        # ********  Download Recording
        self.crm_api_service.download_recording(recording=recording)

        # ********  Transcribe Recording
        self.transcribe_service.process(recording=recording)

        # ********  Calculate Weight Percentage
        recording.weight_percentage = self.crm_api_service.calculate_weight_percentage(
            profile_id=recording.profile_id
        )

        # ********  GPT process
        gpt_response = self.gpt_service.process(recording=recording)

        gpt_response = json.loads(gpt_response)

        # # ********  Validate Transcript
        # validation_result = self.validation_service.validate_all(
        #     summary_dict=summary_dict
        # )

        if gpt_response["status"] == "false":
            recording.success = False
            recording.error_code_list = gpt_response["error_code_list"]
        else:
            recording.success = True

        # ******** log to mongo
        document = {
            "document_name": recording.document_name,
            "document_id": recording.document_id,
            "document_title": recording.document_title,
            "profile_id": recording.profile_id,
            "first_name": recording.first_name,
            "last_name": recording.last_name,
            "sale_company": recording.sale_company,
            "sale_employee_id": recording.sale_employee_id,
            "sale_employee_name": recording.sale_employee_name,
            "document_uploaded_by_id": recording.document_uploaded_by_id,
            "document_uploaded_by_name": recording.document_uploaded_by_name,
            "document_uploaded_at": recording.document_uploaded_at,
            "success": recording.success,
            "duration": recording.duration,
            "transcript": recording.transcript,
            "error_code_list": gpt_response["error_code_list"],
            "created_at": datetime.now(pytz.utc),
            "modified_at": datetime.now(pytz.utc),
        }
        self.ai_sale_logs.collection.insert_one(document=document)

    # ********************************************************************************************************
    # MAIN HANDLING
    # ********************************************************************************************************
    def handleTask(self, recordings: RecordingBatchModel):

        for recording in recordings.batch:

            # ********  Handling
            Action = self.handling(recording=recording)

            if Action == self.TRANS_CODE.GENERAL.ERROR_CODE.F101:
                # Add error code for non-audio file
                recording.error_code_list = [
                    {
                        "error_code": "F101",
                        "error_message": self.TRANS_CODE.GENERAL.ERROR_CODE.F101,
                        "error_reference": [],
                    }
                ]
                # Log and report error
                self.reporting_service.saveAndReport(recording=recording)
            elif Action != self.TRANS_CODE.GENERAL.ERROR_CODE.X100:
                # Send to Gchat for other cases except X100
                self.reporting_service.saveAndReport(recording=recording)
            else:
                # Just print for X100 case
                print(f"Document {recording.document_id} already exists in mongo")

            print("------------------------------Done------------------------------")
