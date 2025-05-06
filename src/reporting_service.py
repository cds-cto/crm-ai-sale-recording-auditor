from openpyxl import Workbook
from httplib2 import Http
import datetime, os, configparser, json, pytz

# ***** project
from models import RecordingModel
from s3connect import S3Connect

# ***** constant
from constant import TRANSACTION_CODES


class ReportingService:
    def _getTodayTime(self):
        utc_now = datetime.datetime.now(pytz.utc)
        pdt_timezone = pytz.timezone("America/Los_Angeles")
        pdt_now = utc_now.astimezone(pdt_timezone)
        return pdt_now

    # ********************************************************************************************************
    # GChat Message
    # ********************************************************************************************************
    def GChat_Message(self, recording: RecordingModel, caption: str):

        current_folder = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_folder, "config.ini")
        config = configparser.ConfigParser()
        config.read(config_file_path)

        chaturl = config["GCHAT"]["HourlyGgcsSync"]

        # ******** Initialize

        SalesRecordingSection = [
            {
                "collapsible": "false",
                "widgets": [
                    {
                        "buttonList": {
                            "buttons": [
                                {
                                    "text": "Transcript",
                                    "onClick": {
                                        "openLink": {
                                            "url": "https://www.google.com",
                                        }
                                    },
                                },
                            ],
                        }
                    },
                    {
                        "textParagraph": {
                            "text": caption,
                        },
                    },
                ],
            },
        ]
        bot_message = {
            "cardsV2": [
                {
                    "cardId": "unique-card-id",
                    "card": {
                        "header": {
                            "title": f"Sales recording of {recording.first_name} {recording.last_name} - {recording.profile_id}",
                        },
                        "sections": SalesRecordingSection,
                    },
                }
            ],
        }
        message_headers = {"Content-Type": "application/json; charset=UTF-8"}
        http_obj = Http()
        response = http_obj.request(
            uri=chaturl,
            method="POST",
            headers=message_headers,
            body=json.dumps(bot_message),
        )
        print(response)

    # ********************************************************************************************************
    # Save and Send Report
    # ********************************************************************************************************
    def saveAndReport(self, recording: RecordingModel):

        # s3_bucket = S3Connect(
        #     config_file="config.ini", config_name="S3_SaleRecordingReports"
        # )

        # ************ Save file
        # today = self._getTodayTime()
        # date_time_str = today.strftime("%m-%d-%Y")
        # report_time_str = today.strftime("%m-%d-%Y %H:%M")

        # file_name = rf"sale_recording_{date_time_str}.xlsx"

        # current_folder = os.path.dirname(os.path.abspath(__file__))
        # file_path = os.path.join(current_folder, file_name)

        # self.wb.save(file_path)

        # # ****** s3 upload
        # s3_bucket.uploadFile(
        #     s3_file_name=f"{file_name}", local_file_path=rf"{file_path}"
        # )

        caption = (
            "Result : ✅ True" + "\n"
            if recording.success
            else "Result : ❌ False" + "\n"
        )

        caption += f"Date uploaded : {recording.document_uploaded_at}" + "\n\n"
        caption += f"Sales employee : {recording.sale_employee_name}" + "\n"
        caption += f"Sales company : {recording.sale_company}" + "\n\n"
        caption += f"Duration : {recording.duration}" + "\n\n"

        if not recording.success:
            caption += f"Fail reason :" + "\n"

        count = 0
        for error in recording.error_code_list:
            times = (
                error["error_reference"][0]["time_occurred"]
                if "error_reference" in error and error["error_reference"]
                else ""
            )
            caption += (
                f"{times} - {error['error_code']} - {error['error_message']}" + "\n"
            )
            count += 1
            if count % 4 == 0:
                caption += "\n"

        print(caption)
        self.GChat_Message(
            recording=recording,
            caption=caption,
        )
