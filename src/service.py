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
from sqlconnect import SqlConnect

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
    # Get General Error List
    # ********************************************************************************************************
    def _get_general_error_list(self):
        prompt = ""
        general_error_list = self.ai_sale_general_error_list.collection.find()
        for error in general_error_list:
            prompt += f"- {error['issue_code']}: {error['issue_name']}\n"
            for check in error["issue_check"]:
                prompt += f"  {check.format(assign_company='Citizen Debt Services')}\n"

        return prompt
    
    # ********************************************************************************************************
    # Get Recordings With SQL 
    # ********************************************************************************************************
    def get_recordings_with_sql(
        self,
        Recordings: RecordingBatchModel,
        from_date_time: datetime,
        to_date_time: datetime,
    ):
        """Get tasks from start_date to end_date"""
        
        SQL = """SELECT
                    Documents.Name As DocumentName,
                    Documents.DocumentId As DocumentId,
                    Documents.Title As DocumentTitle,
                    Documents.ProfileId As ProfileId,
                    CONCAT(Profiles.FirstName, ' ', Profiles.LastName) As ClientName,
                    Companies.Name As SalesCompany,
                    sales.EmployeeId As SalesId,
                    sales.Alias As SalesName,
                    documentupload.EmployeeId As DocumentUploadedById,
                    documentupload.Alias As DocumentUploadedByName,
                    DATEADD(HOUR, -7, Documents.CreatedAt) As DocumentUploadedAt,
                    Profiles.SubmittedDate



                FROM Documents
                    LEFT JOIN Profiles ON Documents.ProfileId = Profiles.ProfileId
                    LEFT JOIN ProfileAssignees ON Profiles.ProfileId = ProfileAssignees.ProfileId
                        AND ProfileAssignees.AssigneeId = '028F546A-0429-4C9A-B50D-436BFA655075'
                    LEFT JOIN Employees sales ON ProfileAssignees.EmployeeId = sales.EmployeeId
                    LEFT JOIN Companies ON sales.CompanyId = Companies.CompanyId
                    LEFT JOIN Employees documentupload ON Documents.CreatedBy = documentupload.EmployeeId
                    LEFT JOIN ProfileAdditionalStatuses RecordingStatus ON Profiles.ProfileId = RecordingStatus.ProfileId
                        AND RecordingStatus.AdditionalStatusId = '50C25FCA-23E0-4E69-844E-22EDF8E88DA2'
                    LEFT JOIN ProfileAdditionalStatuses WCStatus ON Profiles.ProfileId = WCStatus.ProfileId
                        AND WCStatus.AdditionalStatusId = 'E390DAEA-B84B-42A7-B95B-FE1FAC50F7C3'
                WHERE Companies.Type = 1
                    AND Profiles.Status = 1
                    AND RecordingStatus.Value = 'Uploaded'
                    AND WCStatus.Value = 'COMPLETED'
                    AND Documents.Category = 'ce25a439-86de-48c0-aebb-18de5d46ea61'
                    AND Documents.CreatedAt >= ?
                """
        
        fetch_data = self.sql_service.fetchall(SQL, [from_date_time])

        for data in fetch_data:
            document_name = data[0]
            document_id = data[1].lower()
            document_title = data[2]
            profile_id = data[3]
            first_name = data[4]
            last_name = data[5]
            sale_company = data[6]
            sale_employee_id = data[7].lower()
            sale_employee_name = data[8]
            document_uploaded_by_id = data[9].lower()
            document_uploaded_by_name = data[10]
            document_uploaded_at = data[11]
            submitted_date = data[12]
            Recordings.batch.append(
                RecordingModel(
                    document_name=document_name,
                    document_id=document_id,
                    document_title=document_title,
                    profile_id=profile_id,
                    first_name=first_name,
                    last_name=last_name,
                    sale_company=sale_company,
                    sale_employee_id=sale_employee_id,
                    sale_employee_name=sale_employee_name,
                    document_uploaded_by_id=document_uploaded_by_id,
                    document_uploaded_by_name=document_uploaded_by_name,
                    document_uploaded_at=document_uploaded_at,
                    submitted_date=submitted_date,
                    success=False,
                    duration=0,
                    error_code_list=[],
                    # ********  extra fields
                    recording_url="",
                    recording_file_path="",
                )
            )
        print("Total Tasks: ", len(Recordings.batch))

    

    # ********************************************************************************************************
    # Process
    # ********************************************************************************************************

    def process(
        self,
        from_date_time: datetime,
        to_date_time: datetime,
    ):
        # ******** get external IP
        self._get_external_ping()

        # ********  Init Mongo DB
        self.ai_sale_logs = MongoConnect(
            config_file="config.ini",
            config_name="AI_SALE_LOGS",
        )

        self.ai_sale_general_error_list = MongoConnect(
            config_file="config.ini",
            config_name="AI_SALE_GENERAL_ERROR_LIST",
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

        # ********  Init SQL
        self.sql_service = SqlConnect(
            config_file="config.ini", config_name="SQL_NEW"
        )
        self.sql_service.init()

        # ********  Init batch model
        recordings = RecordingBatchModel(batch=[])

        # ********  Get Recordings
        # self.crm_api_service.get_recordings(
        #     Recordings=recordings,
        #     from_date_time=from_date_time,
        #     to_date_time=to_date_time,
        # )

        self.get_recordings_with_sql(Recordings=recordings, from_date_time=from_date_time, to_date_time=to_date_time)

        print("************************************************************")

        self.handleTask(recordings=recordings)

    # ********************************************************************************************************
    # Solo Handling
    # ********************************************************************************************************
    def handling(self, recording: RecordingModel, general_error_list: str):
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
        gpt_response = self.gpt_service.process(
            recording=recording, general_error_list=general_error_list
        )

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
        # ********  Get General Error List
        general_error_list = self._get_general_error_list()

        for recording in recordings.batch:

            # ********  Handling
            Action = self.handling(
                recording=recording, general_error_list=general_error_list
            )

            # get profile info
            profile_info = self.crm_api_service.get_profile_info(
                profile_id=recording.profile_id
            )
            recording.profile_status = profile_info["statusName"]
            recording.enrolled_date = profile_info["enrolledDate"]

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
                self.reporting_service.push_blank_call_to_make_report(recording=recording)
                self.reporting_service.push_to_make_report(recording=recording)
                
            elif Action != self.TRANS_CODE.GENERAL.ERROR_CODE.X100:
                # Send to Gchat for other cases except X100
                self.reporting_service.push_blank_call_to_make_report(recording=recording)
                self.reporting_service.push_to_make_report(recording=recording)
            else:
                # Just print for X100 case
                print(f"Document {recording.document_id} already exists in mongo")

            print("------------------------------Done------------------------------")

    # ********************************************************************************************************
    # TESTING Process Check GPT
    # ********************************************************************************************************
    def process_check_gpt(self):
        """
        Process a text file and check its content using GPT for testing
        Args:
            file_path (str): Path to the text file to process
        """
        print("\n============================= START  ===============================")

        # ********  Init Mongo DB
        self.ai_sale_logs = MongoConnect(
            config_file="config.ini",
            config_name="AI_SALE_LOGS",
        )

        self.ai_sale_general_error_list = MongoConnect(
            config_file="config.ini",
            config_name="AI_SALE_GENERAL_ERROR_LIST",
        )
        # ********  Init Reporting Service
        self.reporting_service = ReportingService()

        general_error_list = self._get_general_error_list()

        # Create a recording model with the content
        recording = RecordingModel(
            document_name="7823615724d81e942492e34c9da6b27f9de65bd82735748.mp3",
            document_id="",
            document_title="",
            profile_id="",
            first_name="",
            last_name="",
            sale_company="",
            sale_employee_id="",
            sale_employee_name="",
            document_uploaded_by_id="",
            document_uploaded_by_name="",
            document_uploaded_at="",
            success=True,
            duration=100,
            transcript="",
            error_code_list=[],
            created_at=datetime.now(pytz.utc),
            modified_at=datetime.now(pytz.utc),
            recording_file_path="",
            recording_url="",
            file_extension="",
        )

        # Process with GPT
        self.gpt_service = GPTService(config_file="config.ini", config_name="OPENAI")
        gpt_response = self.gpt_service.process(
            recording=recording, general_error_list=general_error_list
        )
        gpt_response = json.loads(gpt_response)

        # Print results
        # print(
        #     "\n============================= GPT Analysis Results ==============================="
        # )
        # print(f"Status: {gpt_response['status']}")
        # print("\nError Codes:")
        # for error in gpt_response["error_code_list"]:
        #     print(f"- {error['error_code']}: {error['error_message']}")
        #     print(f"   {error['error_reference']}\n\n")
        # print(
        #     "====================================================================================\n"
        # )

        # get document from mongo by document_id
        document = self.ai_sale_logs.collection.find_one(
            {"document_name": recording.document_name}
        )
        document["error_code_list"] = gpt_response["error_code_list"]
        document["recording_url"] = ""
        document["recording_file_path"] = ""
        document["file_extension"] = ""
        document_final = RecordingModel(**document)

        self.reporting_service.push_to_make_report(recording=document_final)

        return True
