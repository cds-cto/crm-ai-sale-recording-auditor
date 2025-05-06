# ******** project import
from common import (
    CHUNK_SIZE,
    PROFILE_ASSIGNEE_SALES,
    SALE_RECORDING_CATEGORY,
    FolderNames,
)
import configparser
from datetime import datetime, time, timezone
import os
import json
import time

# ******** external import
import requests, json
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
import math
from models import RecordingBatchModel, RecordingModel, WeightPercentageModel

# ******** schemas import


class CrmAPIService:
    def __init__(self, config_file, config_name):
        self.session = None
        self.current_folder = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_folder, config_file)
        config = configparser.ConfigParser()
        config.read(config_file_path)
        self.base_url = config[config_name]["URL_CRM_API"]
        self.username = config[config_name]["USERNAME"]
        self.password = config[config_name]["PASSWORD"]

        self._get_login_session()

    def _get_login_session(self):
        """Initialize login session for CRM API calls"""
        AUTH_URL = f"{self.base_url}/api/User/auth"
        data = {
            "userName": self.username,
            "password": self.password,
            "returnUrl": "",
        }
        headers = {"Content-type": "application/json"}

        self.crm_r = requests.Session()

        # Add retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.crm_r.post(
                    AUTH_URL,
                    data=json.dumps(data),
                    headers=headers,
                    timeout=30,  # Add timeout
                )
                if response.status_code == 200:
                    self.token = response.json()["data"]["token"]
                    self.refresh_token = response.json()["data"]["refreshToken"]
                    return True
                else:
                    raise ValueError(
                        f"Login failed with status code: {response.status_code}"
                    )

            except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                if attempt == max_retries - 1:  # Last attempt
                    raise Exception(
                        f"Failed to connect after {max_retries} attempts: {str(e)}"
                    )
                time.sleep(2**attempt)  # Exponential backoff: 1, 2, 4 seconds

    # ********************************************************************************************************
    # Get Recordings
    # ********************************************************************************************************
    def get_recordings(self, Recordings: RecordingBatchModel):
        """Get tasks from start_date to end_date"""

        url = f"{self.base_url}/api/Document/search"

        headers = {
            "Content-type": "application/json",
            "authorization": f"Bearer {self.token}",
        }

        try:
            data = {
                "start": 0,
                "length": 1,
                "columns": [
                    {
                        "columnName": "category",
                        "search": {
                            "value": SALE_RECORDING_CATEGORY,
                            "operator": 2,
                        },
                    }
                ],
                "order": [
                    {"columnName": "status", "direction": 0, "directionName": "asc"},
                    {"columnName": "createdAt", "direction": 0, "directionName": "asc"},
                ],
            }

            response = self.crm_r.post(
                url, headers=headers, data=json.dumps(data), verify=False
            )
            if response.status_code != 200:
                raise Exception(
                    f"Fetching tasks failed with code {response.status_code}"
                )

            total_records = response.json()["data"]["totalRecords"]
            all_data = []

            # Fetch data in chunks
            for start in range(0, total_records, CHUNK_SIZE):
                data["start"] = start
                data["length"] = CHUNK_SIZE

                response = self.crm_r.post(
                    url, headers=headers, data=json.dumps(data), verify=False
                )

                if response.status_code != 200:
                    raise Exception(
                        f"Fetching tasks failed with code {response.status_code}"
                    )

                all_data.extend(response.json()["data"]["data"])
                # break  # TODO: for testing

            for data in all_data:

                profile_assignment = self._filter_profile_assignments_sales(
                    data["profileAssignees"]
                )
                Recordings.batch.append(
                    RecordingModel(
                        document_name=data["name"],
                        document_id=data["documentId"],
                        document_title=data["title"],
                        profile_id=data["profileId"],
                        first_name=(
                            data["profileName"].split()[0]
                            if data["profileName"]
                            else ""
                        ),
                        last_name=(
                            " ".join(data["profileName"].split()[1:])
                            if data["profileName"]
                            else ""
                        ),
                        sale_company=(
                            profile_assignment["companyName"]
                            if profile_assignment
                            else ""
                        ),
                        sale_employee_id=(
                            profile_assignment["employeeId"]
                            if profile_assignment
                            else ""
                        ),
                        sale_employee_name=(
                            profile_assignment["employeeName"]
                            if profile_assignment
                            else ""
                        ),
                        document_uploaded_by_id=data["createdBy"],
                        document_uploaded_by_name=data["createdByName"],
                        document_uploaded_at=data["createdAt"],
                        success=False,
                        duration=0,
                        error_code_list=[],
                        # ********  extra fields
                        recording_url="",
                        recording_file_path="",
                    )
                )
            print("Total Tasks: ", len(Recordings.batch))

        except Exception as e:
            print(f"Error fetching tasks: {str(e)}")
            raise Exception(f"Error fetching tasks: {str(e)}")

    # ********************************************************************************************************
    # Get Recordings URL
    # ********************************************************************************************************
    def get_recordings_url(self, document_id: str):

        url = f"{self.base_url}/api/Document/{document_id}/preview"

        headers = {
            "Content-type": "application/json",
            "authorization": f"Bearer {self.token}",
        }

        try:
            data = {"URL": True}

            response = self.crm_r.post(
                url, headers=headers, data=json.dumps(data), verify=False
            )
            if response.status_code != 200:
                raise Exception(
                    f"Fetching tasks failed with code {response.status_code}"
                )

            url_link = response.json()["data"]["url"]

            return url_link

        except Exception as e:
            print(f"Error fetching tasks: {str(e)}")
            raise Exception(f"Error fetching tasks: {str(e)}")

    # ********************************************************************************************************
    # Download Recording
    # ********************************************************************************************************
    def download_recording(self, recording: RecordingModel):
        try:
            # Generate unique filename based on timestamp
            file_path = os.path.join(
                self.current_folder,
                f"{FolderNames.RECORDING.value}/{recording.document_name}",
            )

            # Download file directly without streaming
            response = requests.get(recording.recording_url, verify=False, stream=False)
            if response.status_code != 200:
                raise Exception(
                    f"Downloading recording failed with code {response.status_code}"
                )

            with open(file_path, "wb") as f:
                f.write(response.content)

            recording.recording_file_path = file_path

            # Get duration of audio file based on extension
            if file_path.lower().endswith(".mp3"):
                audio = MP3(file_path)
                recording.duration = int(audio.info.length)
                recording.file_extension = "mp3"
            elif file_path.lower().endswith(".wav"):
                audio = WAVE(file_path)
                recording.duration = int(audio.info.length)
                recording.file_extension = "wav"

        except Exception as e:
            print(f"Error downloading recording: {str(e)}")
            raise Exception(f"Error downloading recording: {str(e)}")

    # ********************************************************************************************************
    # Send Note
    # ********************************************************************************************************
    def _sendNote(self, profile_id: str, liability_id: str, content: str):
        try:
            data = {
                "content": content,
                "parentNoteId": "",
                "liabilityId": liability_id,
                "important": False,
                "mentionedEmails": "",
                "noteReferenceId": "",
                "referenceType": "",
                "usedTemplate": None,
                "targets": [],
                "profileId": profile_id,
            }
            headers = {
                "Content-type": "application/json",
                "authorization": f"Bearer {self.token}",
            }

            res = self.crm_r.post(
                f"{self.base_url}/api/Note/{profile_id}/profile",
                data=json.dumps(data),
                headers=headers,
            )

            if res.status_code != 200:
                raise Exception(f"Posting Note To Crm Code {res.status_code}")
            else:
                note_data = res.json()["data"]
                return note_data
        except Exception as e:
            print(f"Error sending note: {str(e)}")
            raise Exception(f"Error sending note: {str(e)}")

    # ********************************************************************************************************
    # Get liablity profile for calulateWeightPercentage
    # ********************************************************************************************************
    def get_liability_profile(self, profile_id: str):

        url = f"{self.base_url}/api/liability/{profile_id}/profile"
        headers = {
            "Content-type": "application/json",
            "authorization": f"Bearer {self.token}",
        }
        try:
            response = self.crm_r.get(url, headers=headers, verify=False)
            if response.status_code != 200:
                raise Exception(
                    f"Fetching libility profile failed with code {response.status_code}"
                )

            data = response.json()["data"]
            results = []
            for item in data:
                results.append(
                    WeightPercentageModel(
                        enrolled=item["enrolled"],
                        accountType=item["accountType"],
                        averageSettlementLegalPercentage=item[
                            "averageSettlementLegalPercentage"
                        ],
                        averageSettlementPercentage=item["averageSettlementPercentage"],
                        originalBalance=item["originalBalance"],
                    )
                )

            return results

        except Exception as e:
            print(f"Error fetching libility profile: {str(e)}")
            raise Exception(f"Error fetching libility profile: {str(e)}")

    # ---------------------------------------------------------------------------------------------------------
    # Utility Functions
    # ---------------------------------------------------------------------------------------------------------

    # ********************************************************************************************************
    # Filter Profile Assignments Sales
    # ********************************************************************************************************
    def _filter_profile_assignments_sales(self, profile_assignments: list):
        for profile_assignment in profile_assignments:
            if profile_assignment["assigneeId"] == PROFILE_ASSIGNEE_SALES:
                return profile_assignment
        return None

    # ********************************************************************************************************
    # Calculate Weight Percentage
    # ********************************************************************************************************
    def calculate_weight_percentage(self, profile_id: str) -> str:
        """
        Calculate weighted percentage based on liability profile data
        Returns percentage as string with % symbol
        """
        total_unsecured_debts = 0
        total_weighted_amount = 0

        liability_profiles = self.get_liability_profile(profile_id)

        for item in liability_profiles:
            if item.enrolled:
                average_percentage = (
                    item.averageSettlementLegalPercentage
                    if item.accountType == 1
                    else item.averageSettlementPercentage
                )

                # Use 0.5 as default if no average percentage
                average_percentage = average_percentage if average_percentage else 0.5

                total_unsecured_debts += item.originalBalance
                total_weighted_amount += item.originalBalance * average_percentage

        if total_unsecured_debts == 0:
            return "0 %"

        percentage = math.ceil((total_weighted_amount / total_unsecured_debts) * 100)
        return f"{percentage} %"
