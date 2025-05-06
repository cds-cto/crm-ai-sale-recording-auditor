# ******** project import
from common import FolderNames, Utility

# ******** external import
import datetime
from time import sleep
from models import RecordingModel
from openai import OpenAI
from os import listdir, path
import json
import configparser


class GPTService:
    def __init__(self, config_file, config_name):
        self.session = None
        self.current_folder = path.dirname(path.abspath(__file__))
        config_file_path = path.join(self.current_folder, config_file)
        config = configparser.ConfigParser()
        config.read(config_file_path)
        OPENAI_API_KEY = config[config_name]["OPENAI_API_KEY"]
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    # ********************************************************************************************************
    # Audit with GPT
    # ********************************************************************************************************
    def audit_with_gpt(self, chunk, recording: RecordingModel, previous_summary=None):
        """
        Send chunk and previous summary to GPT to audit the conversation
        """
        # Create context
        prompt = """
                Here is the previous Response and the next chunk of data. Review the conversation for any violations of compliance rules, focusing on:

                - Claims about government programs or affiliation
                - Misrepresenting as a loan company
                - False claims about debt validation
                - Misleading statements about credit repair
                - Unauthorized fees or charges
                - Deceptive marketing practices
                - Violations of consumer protection laws

            """

        if previous_summary:
            prompt += f"\nPrevious Response:\n{previous_summary}\n"
        prompt += f"\nNext Chunk of Data:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}\n"

        # Send request to GPT-4
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        """You are a compliance content filter analyzing sales conversations.

Input: A transcript of a conversation between a sales representative and a customer.

Process:
#Read the entire conversation then check for violations of the following rules:

E100 - Claim that program is from the government
E101 - Claim that we are a loan company or will loan money to clients
E102 - Claim that we do debt validation
E103 - Claim that we do credit repair
E104 - Claim that we will have an attorney represent clients if anything happens
E105 - Claim that we do not charge any fees
E106 - Claim that we can achieve better settlement than """
                        + str(recording.weight_percentage)
                        + """
E107 - Claim that we will refund if clients are not happy
E108 - Claim that the client can cancel anytime without any issue
E109 - Claim that credit score won't have any impact or only short-term impact
E110 - Claim that enrolled accounts will be temporarily closed after or during the settlement
E111 - Claim that program will not affect client's military/security clearance
E112 - Claim that client can keep using the same bank who issued the enrolled credit cards
E113 - Claim that the client won't get sued
E114 - Claim or accepts an account with promotional interest or zero interest for enrollment
E115 - Claim or accepts secured debt to the program
E116 - Claim that the program does not require the client's active engagement and responsiveness
E117 - Failure to disclose that the client owns and controls the dedicated account
E118 - Claim that we have full control over client's dedicated account
S115 - Salesperson did not go through budgeting with client
F100 - Base on the content, the recording wasn't a sales recording

Output format: You must respond **only** with a JSON object in one of the following formats. **No additional explanation, notes, or text is allowed.**
If any violations are found, return:
{
    "status": "false", 
    "is_sale_recording": "true",
    "error_code_list": [
        {
            "error_code": "<error code from the list>",
            "error_message": "<exact rule from the list>", 
            "error_reference": [
                {   
                    "time_occurred": "HH:mm",  // Convert start_time when violation first occurred from seconds to HH:mm format
                    "entity": "<client or salesperson>",
                    "detail": "<exact quote from transcript>"
                }
            ]
        }
    ]
}

If no violations are found, return:
{
    "status": "success",
    "is_sale_recording": "true",
    "error_code_list": []
}"""
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
        )

        return response.choices[0].message.content

    def detect_sale_recording(self, chunk, previous_summary=None):
        """
        Send chunk and previous summary to GPT to detect sale recording
        """
        # Create context
        prompt = """
                    Here is the previous summary and the next chunk of data. Focus only on detection of sales recording. 
                    Create an updated summary that includes information exclusively about detection of sales recording. 
                    Ignore any unrelated details. Keep the summary concise and accurate. 
                    If the next chunk of data doesn't provide any new info about the detection of sales recording, and the JSON summary stays the same, please return the previous response :\n"
                """

        if previous_summary:
            prompt += f"\nPrevious Summary:\n{previous_summary}\n"
        prompt += f"\nNext Chunk of Data:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}\n"

        # Send request to GPT-4
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        """You are a compliance content filter analyzing sales conversations.

Your task is to determine if this is a sales recording

Look for these key indicators:
# Agent introduces themselves and mentions a company
# Agent confirms identity of the person
# Mention of debt relief, debt settlement, or credit consolidation
# Caller references a referral or previous interest
# Explanation of a program or service
# Discussion about user's financial situation:
    ## Income
    ## Expenses
    ## Debts
    ## Credit score
# Agent collects personal details:
    ## Full name, date of birth, address
    ## Bank account and routing number
# Mention of soft credit pull or checking credit report
# Discussion of monthly payment plan and deposit schedule
# Agent asks for consent or confirmation
# Mention of contract or e-signature
# User gives approval or agreement
# Reference to future steps or welcome call
# Closing with positive tone and next contact time

Output:
If this is not a sales recording, return exactly:
{
    "is_sale_recording": "false",
    "error_code_list": [
        {
            "error_code": "F100",
            "error_message": "Base on the content, the recording wasn't a sales recording", 
            "error_reference": [
                {   
                    "time_occurred": "HH:mm",  // Convert start_time when violation first occurred from seconds to HH:mm format
                    "entity": "<client or salesperson>",
                    "detail": "<exact quote from transcript>"
                }
            ]
        }
    ]
}

If this is a sales recording, return exactly:
{
    "is_sale_recording": "true"
}"""
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
        )

        return response.choices[0].message.content

    # split json list
    def split_json_list(self, data_list, chunk_size):
        total_tokens = 0
        start_index = 0

        while start_index < len(data_list):
            for i in range(start_index, len(data_list)):
                total_tokens += len(data_list[i])
                if total_tokens > chunk_size:
                    yield data_list[start_index:i]
                    start_index = i
                    total_tokens = 0
                    break
            else:
                yield data_list[start_index:]
                break

    # ********************************************************************************************************
    # Process
    # ********************************************************************************************************
    def process(self, recording: RecordingModel):
        FILENAME = path.join(
            self.current_folder,
            f"{FolderNames.TRANSCRIPT.value}/{Utility.remove_audio_extension(recording.document_name)}.txt",
        )

        with open(FILENAME, "r", encoding="utf-8") as file:
            data = file.readlines()

        # ********  save transcript
        recording.transcript = "\n".join(data)

        # ********  split transcript
        data_array = [line.strip() for line in data]

        # Check if this is a sale recording by processing chunks
        chunk_size = 10000
        detection_summary = None

        # ******** detect sale recording
        # region detect sale recording
        for idx, chunk in enumerate(self.split_json_list(data_array, chunk_size)):
            print(f"Checking chunk {idx + 1} for sale recording...")
            chunk_is_sale = self.detect_sale_recording(chunk, detection_summary)

            detection_summary = chunk_is_sale  # Store summary for next iteration
            break  # TODO: For testing

        result = json.loads(detection_summary.replace("\n", "").strip())
        if result["is_sale_recording"] == "False":
            error_result = {
                "status": "false",
                "is_sale_recording": "false",
                "error_code_list": [],
            }
            return json.dumps(error_result)

        # endregion detect sale recording

        # ********  audit sale recording

        # region audit sale recording
        summary = None
        error_code_list = []
        if isinstance(data_array, list):
            for idx, chunk in enumerate(self.split_json_list(data_array, chunk_size)):
                print(f"Handle chunk {idx + 1} for file {FILENAME}...")
                summary = self.audit_with_gpt(chunk, recording, summary)
                print(
                    f"Update summary after chunk {idx + 1} for file {FILENAME}:\n{summary}\n"
                )
                sale_result = json.loads(summary.replace("\n", "").strip())

                # ********  append error code list
                if sale_result["status"] == "false":
                    # Check each error in the current result
                    for new_error in sale_result["error_code_list"]:
                        # Flag to check if this error time already exists
                        is_duplicate = False

                        # Compare with existing errors
                        for existing_errors in error_code_list:

                            # Check if same error code and time
                            if (
                                new_error["error_code"] == existing_errors["error_code"]
                                and new_error["error_reference"][0]["time_occurred"]
                                == existing_errors["error_reference"][0][
                                    "time_occurred"
                                ]
                            ):
                                is_duplicate = True
                                break

                        # Only append if not a duplicate time
                        if not is_duplicate:
                            error_code_list.append(new_error)
        else:
            print(f"Data format not supported for rolling summary of file {FILENAME}.")

        # ********  return result
        print(f"Handle file {FILENAME} has been completed!")

        if len(error_code_list) > 0:
            error_result = {
                "status": "false",
                "is_sale_recording": "true",
                "error_code_list": error_code_list,
            }
            return json.dumps(error_result)
        else:
            success_result = {
                "status": "success",
                "is_sale_recording": "true",
                "error_code_list": [],
            }
            return json.dumps(success_result)

        # endregion sale recording
