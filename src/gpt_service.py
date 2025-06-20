# ******** project import
from common import FolderNames, Utility

# ******** external import
import datetime
from time import sleep
from models import RecordingModel
from mongo_service import MongoService
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
        # prompt = """
        #         ## Previous Context
        #         {previous_context}

        #         ## Current Chunk
        #         {current_chunk}

        #         """

        # if previous_summary:
        #     prompt = prompt.format(
        #         previous_context=f"Previous Response:\n{previous_summary}",
        #         current_chunk=f"Next Chunk of Data:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}",
        #     )
        # else:
        #     prompt = prompt.format(
        #         previous_context="No previous context available.",
        #         current_chunk=f"Next Chunk of Data:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}",
        #     )

        # changed: since chunk_size = 100000, so we can use one chunk
        prompt = json.dumps(chunk, ensure_ascii=False, indent=2)

        # Send request to GPT-4
        response = self.client.chat.completions.create(
            model=self.MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        """
## Role

You are a sales recording auditor for a debt settlement company named """
                        + recording.company_name
                        + """

## Goal

Your task is to audit a transcript of a conversation between a salesperson and a
client to determine whether the salesperson has violated any company rules, using
the provided list of error codes and rule descriptions.

You must:

- Evaluate the transcript **against each rule independently**, one by one.
- Detect **every instance** of a rule violation, even if **repeated**,
  **paraphrased**, or **indirectly implied**.
- Flag any part of the transcript that **matches, implies, or fails to disclose** required information per the rules.
- Always include **all occurrences** of each violation, even if they happen multiple times during the call.

## Input

A transcript of a conversation between a salesperson and a client. Each line
includes:

- `timestamp` in seconds (e.g. 125),
- `speaker` (either "salesperson" or "client"),
- `text` (spoken dialogue).

## Preprocessing Step (REQUIRED)

Before applying the rules, perform an **initial scan of the transcript** to detect
high-risk keywords and phrases such as:

- “bailout”, “federal”, “relief fund”, “state program”
- “your score will go up”, “we’ll repair your credit”, “it won’t hurt your credit”
- “we’ll loan you money”, “we give you a loan”
- “you won’t get sued”, “you don’t have to do anything”, “you’ll get a refund if unhappy”
- “use your same bank”, “we control the account”

These are often signs of hidden or indirect violations and must be carefully
checked against the rules, even if phrased differently.

## Output Format

Respond **only** with a JSON object in one of the following formats. **No
explanation, commentary, or extra text is allowed.**

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
"time_occurred": "HH:mm", # Convert timestamp to HH:mm (e.g. 645 =>
"10:45")
"entity": "<client or salesperson>",
"detail": "<verbatim or clear paraphrased quote from transcript showing the
violation>"
}
// Repeat if same error occurs multiple times
]
}

// Repeat block for each unique rule violated
]
}

- If the same rule is violated multiple times, **include each occurrence** in separate entries under `"error_reference"` for that rule.

### If no violations are found:

{
"status": "success",
"is_sale_recording": "true",
"error_code_list": []
}

## Evaluation Rules

You must use the provided list of error codes and associated rules to detect
violations. When checking each rule:

- **Do not skip** any rule. Evaluate every rule against the entire transcript.
- **Always flag** if a rule is violated more than once — include each instance.
- **Include indirect or suggestive language** (e.g., “bailout” implies government = E100).
- **Flag silence or failure to warn** when disclosure is required (e.g., credit damage not explained = E109).
- **Err on the side of inclusion**: better to include a possible violation than to miss a real one.

### Error Codes and Rules
"""
                        + general_error_list
                        + """
- F100: Base on the content, the recording wasn't a sales recording
- S105: Claim that we can achieve better settlement than """
                        + str(recording.weight_percentage)
                        + """
  1. We want to avoid quoting unrealistic settlement percentage to the client, the percentage is already pre-calculated and that is the best percetange we can archieve for the client.

"""
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0,
            top_p=1,
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
            temperature=0,
            top_p=1,
        )

        return response.choices[0].message.content

    # ********************************************************************************************************
    # Reflect Error
    # ********************************************************************************************************
    def reflect_error(self, claim: str, bot_response: str, conversation_context: str):

        # Send request to GPT-4
        response = self.client.chat.completions.create(
            model=self.MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        """
                        You are an evaluator. You are given:

                        1. A claim made by a user.
                        2. A bot-generated response
                        3. Converstation context

                        Your task is to evaluate whether the bot’s response correctly supports or reflects the user’s claim. Reply only “Yes” if it clearly and accurately supports the claim, or “No” if it does not reflect, contradicts, or misses the claim.

                        Provide your evaluation in this format:
                        Yes / No """
                    ),
                },
                {
                    "role": "user",
                    "content": f"Claim:' {claim}' \n Bot's response: '{bot_response}' \n Conversation Context: '{conversation_context}'",
                },
            ],
            max_tokens=200,
            temperature=0,
            top_p=1,
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
            # Check if error_reference has multiple items
            if len(new_error["error_reference"]) > 1:
                # Create separate error entries for each reference
                for ref in new_error["error_reference"]:
                    new_error_entry = {
                        "error_code": new_error["error_code"],
                        "error_message": new_error["error_message"],
                        "error_reference": [ref],  # Single reference per entry
                    }
                    error_code_list.append(new_error_entry)

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

        # ********  init mongo service
        self.mongo_service = MongoService(config_file="config.ini", config_name="AI_SALE_GENERAL_ERROR_LIST")

        FILENAME = path.join(
            self.current_folder,
            f"{FolderNames.TRANSCRIPT.value}/{Utility.remove_audio_extension(recording.document_name)}.txt",
        )

        with open(FILENAME, "r", encoding="utf-8") as file:
            data = file.readlines()

        # ********  save transcript
        recording.transcript = base64.b64encode("".join(data).encode("utf-8")).decode("utf-8")

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
                summary = self.audit_with_gpt(chunk, recording, general_error_list, summary)
                print(f"Update summary after chunk {idx + 1} for file {FILENAME}:\n{summary}\n")
                sale_result = json.loads(Utility.edit_gpt_response(summary))

                # ********  append error code list
                if sale_result["status"] == "false":
                    error_code_list = self._append_error_codes(error_code_list, sale_result["error_code_list"])
        else:
            print(f"Data format not supported for rolling summary of file {FILENAME}.")
        # endregion sale recording

        # ********  reflect error

        # region reflect error
        for error in error_code_list:
            issue_code = error["error_code"]
            claim = (
                issue_code
                + f": {error['error_message']}"
                + "\n"
                + "\n".join(self.mongo_service.find_error_list_by_code(issue_code)["issue_check"])
            )

            conversation_context = Utility.extract_conversation_segment(
                error["error_reference"][0]["time_occurred"], data
            )

            bot_response = error["error_reference"][0]["time_occurred"] + ": " + error["error_reference"][0]["detail"]

            reflect_result = self.reflect_error(claim, bot_response, conversation_context)
            error["reflect_result"] = reflect_result

        # endregion reflect error

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
