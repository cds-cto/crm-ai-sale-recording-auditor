from enum import Enum

######################## CONSTANTS ID ########################
CONTACT_ID = {
    "HOME_PHONE": "0bcd9965-4876-4034-bf35-6cdf1770167e",
    "CELL_PHONE": "ca134159-7b02-4578-a25a-6510d03f8ac5",
}

SALE_RECORDING_CATEGORY = "ce25a439-86de-48c0-aebb-18de5d46ea61"


PROFILE_ASSIGNEE_SALES = "028f546a-0429-4c9a-b50d-436bfa655075"

# class TaskStatus(Enum):
#     OPEN = 0  # Open
#     PROCESSING = 1  # Attempted
#     COMPLETED = 2  # Completed
#     CLOSED = 3  # Closed
#     RECEIVED = 4  # Received
#     INPROCESS = 5  # Processing


# ######################## SEARCH OPERATORS ########################
# class SearchOperator(Enum):
#     EQUALS = 0  # Equals
#     NOT_EQUALS = 1  # Not Equals
#     ONE_OF = 2  # One Of
#     NOT_ONE_OF = 3  # Not One Of
#     IN_RANGE = 4  # In Range
#     NOT_IN_RANGE = 5  # Not In Range
#     STARTS_WITH = 6  # Start With
#     CONTAINS = 7  # Contains


######################## CRM CONFIG ########################
CHUNK_SIZE = 1

######################## SETTLEMENT PAYMENT CONFIG ########################


######################## FOLDER NAMES ########################
class FolderNames(Enum):
    TRANSCRIPT = "transcript"
    RECORDING = "recordings"


class Utility:
    @staticmethod
    def remove_audio_extension(file_path):
        return file_path.replace(".mp3", "").replace(".wav", "")

    @staticmethod
    def edit_gpt_response(response: str) -> str:
        """
        Cleans and formats GPT response by removing newlines and JSON code block markers
        Args:
            response (str): Raw GPT response string
        Returns:
            str: Cleaned response string
        """
        return (
            response.replace("\n", "").replace("```json", "").replace("```", "").strip()
        )
