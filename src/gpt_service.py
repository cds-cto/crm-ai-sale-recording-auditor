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
import base64


class GPTService:
    def __init__(self, config_file, config_name):
        self.session = None
        self.current_folder = path.dirname(path.abspath(__file__))
        config_file_path = path.join(self.current_folder, config_file)
        config = configparser.ConfigParser()
        config.read(config_file_path)
        OPENAI_API_KEY = config[config_name]["OPENAI_API_KEY"]
        self.MODEL_NAME = config[config_name]["MODEL_NAME"]
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    # ********************************************************************************************************
    # Audit with GPT
    # ********************************************************************************************************
    def audit_with_gpt(
        self,
        chunk,
        recording: RecordingModel,
        general_error_list: str,
        previous_summary=None,
    ):
        """
        Send chunk and previous summary to GPT to audit the conversation
        """
        # Create context
        prompt = """
                ## Previous Context
                {previous_context}

                ## Current Chunk
                {current_chunk}

                """

        if previous_summary:
            prompt = prompt.format(
                previous_context=f"Previous Response:\n{previous_summary}",
                current_chunk=f"Next Chunk of Data:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}",
            )
        else:
            prompt = prompt.format(
                previous_context="No previous context available.",
                current_chunk=f"Next Chunk of Data:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}",
            )

        # Send request to GPT-4
        response = self.client.chat.completions.create(
            model=self.MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        """
# Compliance Content Filter

## Role
You are a compliance content filter analyzing sales conversations.

## Input
A transcript of a conversation between a salesperson and a client.

## Process
1. Read the entire conversation
2. Check for violations of the following rules:

### Error Codes and Rules
"""
                        + general_error_list
                        + """
- F100: Base on the content, the recording wasn't a sales recording
- S105: Claim that we can achieve better settlement than """
                        + str(recording.weight_percentage)
                        + """
  1. We want to avoid quoting unrealistic settlement percentage to the client, the percentage is already pre-calculated and that is the best percetange we can archieve for the client.

## Output Format
You must respond **only** with a JSON object in one of the following formats. **No additional explanation, notes, or text is allowed.**

### If violations are found:
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
                    "entity": "<have to be client or salesperson>",
                    "detail": "<exact quote from transcript>"
                }
            ]
        }
    ]
}

### If no violations are found:
{
    "status": "success",
    "is_sale_recording": "true",
    "error_code_list": []
}

"""
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
        )

        return response.choices[0].message.content

    # ********************************************************************************************************
    # Detect Sale Recording
    # ********************************************************************************************************
    def detect_sale_recording(self, chunk, previous_summary=None):
        """
        Send chunk and previous summary to GPT to detect sale recording
        """
        # Create context
        prompt = """
# Sales Recording Detection Request

## Previous Context
{previous_context}

## Current Chunk
{current_chunk}

## Instructions
Focus only on detection of sales recording. Create an updated summary that includes information exclusively about detection of sales recording. Ignore any unrelated details. Keep the summary concise and accurate.

If the next chunk of data doesn't provide any new info about the detection of sales recording, and the JSON summary stays the same, please return the previous response.
"""

        if previous_summary:
            prompt = prompt.format(
                previous_context=f"Previous Summary:\n{previous_summary}",
                current_chunk=f"Next Chunk of Data:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}",
            )
        else:
            prompt = prompt.format(
                previous_context="No previous context available.",
                current_chunk=f"Next Chunk of Data:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}",
            )

        # Send request to GPT-4
        response = self.client.chat.completions.create(
            model=self.MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        """
# Sales Recording Detection System

## Role
You are a compliance content filter analyzing sales conversations.

## Task
Determine if this is a sales recording by looking for these key indicators:

### Key Indicators
1. Agent introduces themselves and mentions a company
2. Agent confirms identity of the person
3. Mention of debt relief, debt settlement, or credit consolidation
4. Caller references a referral or previous interest
5. Explanation of a program or service
6. Discussion about user's financial situation:
   - Income
   - Expenses
   - Debts
   - Credit score
7. Agent collects personal details:
   - Full name, date of birth, address
   - Bank account and routing number
8. Mention of soft credit pull or checking credit report
9. Discussion of monthly payment plan and deposit schedule
10. Agent asks for consent or confirmation
11. Mention of contract or e-signature
12. User gives approval or agreement
13. Reference to future steps or welcome call
14. Closing with positive tone and next contact time

## Output Format
You must respond **only** with a JSON object in one of the following formats. **No additional explanation, notes, blank, or text is allowed.**

### If this is not a sales recording:
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

### If this is a sales recording:
{
    "is_sale_recording": "true"
}


"""
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
        )

        return response.choices[0].message.content

    # ********************************************************************************************************
    # Split JSON List
    # ********************************************************************************************************
    def _split_json_list(self, data_list, chunk_size):
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
    # Append Error Codes
    # ********************************************************************************************************
    def _append_error_codes(self, error_code_list, new_errors):
        """
        Append new error codes to the existing list while avoiding duplicates.

        Args:
            error_code_list (list): The existing list of error codes
            new_errors (list): New error codes to append

        Returns:
            list: Updated error code list
        """
        for new_error in new_errors:
            # Flag to check if this error time already exists
            is_duplicate = False

            # Compare with existing errors
            for existing_errors in error_code_list:
                # Check if same error code and time
                if (
                    new_error["error_code"] == existing_errors["error_code"]
                    and new_error["error_reference"][0]["time_occurred"]
                    == existing_errors["error_reference"][0]["time_occurred"]
                ):
                    is_duplicate = True
                    break

            # Only append if not a duplicate time
            if not is_duplicate:
                error_code_list.append(new_error)

        return error_code_list

    # ********************************************************************************************************
    # Process
    # ********************************************************************************************************
    def process(self, recording: RecordingModel, general_error_list: str):
        FILENAME = path.join(
            self.current_folder,
            f"{FolderNames.TRANSCRIPT.value}/{Utility.remove_audio_extension(recording.document_name)}.txt",
        )

        with open(FILENAME, "r", encoding="utf-8") as file:
            data = file.readlines()

        # ********  save transcript
        recording.transcript = base64.b64encode("".join(data).encode("utf-8")).decode(
            "utf-8"
        )

        # ********  split transcript
        data_array = [line.strip() for line in data]

        # Check if this is a sale recording by processing chunks
        chunk_size = 100000
        detection_summary = None

        # ******** detect sale recording
        # region detect sale recording
        for idx, chunk in enumerate(self._split_json_list(data_array, chunk_size)):
            print(f"Checking chunk {idx + 1} for sale recording...")
            chunk_is_sale = self.detect_sale_recording(chunk, detection_summary)

            detection_summary = chunk_is_sale  # Store summary for next iteration
            break  # TODO: For testing

        result = json.loads(Utility.edit_gpt_response(detection_summary))
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
            for idx, chunk in enumerate(self._split_json_list(data_array, chunk_size)):
                print(f"Handle chunk {idx + 1} for file {FILENAME}...")
                summary = self.audit_with_gpt(
                    chunk, recording, general_error_list, summary
                )
                print(
                    f"Update summary after chunk {idx + 1} for file {FILENAME}:\n{summary}\n"
                )
                sale_result = json.loads(Utility.edit_gpt_response(summary))

                # ********  append error code list
                if sale_result["status"] == "false":
                    error_code_list = self._append_error_codes(
                        error_code_list, sale_result["error_code_list"]
                    )
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
