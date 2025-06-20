from enum import Enum
from datetime import datetime, timedelta
import re

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
CHUNK_SIZE = 50

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
        return response.replace("\n", "").replace("```json", "").replace("```", "").strip()

    @staticmethod
    def extract_conversation_segment(timestamp_str: str, conversation_array: list, time_window_minutes: int = 5) -> str:
        """
        Extract conversation segment around a given timestamp within a time window.

        Args:
            timestamp_str (str): Timestamp in format "MM:SS" (e.g., "15:36")
            conversation_array (list): Full conversation array with timestamps
            time_window_minutes (int): Time window in minutes before and after (default: 5)

        Returns:
            str: Extracted conversation segment within the time window
        """
        # try:
        # Parse the target timestamp (MM:SS format)
        minutes, seconds = map(int, timestamp_str.split(":"))
        target_seconds = minutes * 60 + seconds

        # Calculate time boundaries in seconds
        start_seconds = target_seconds - (time_window_minutes * 60)
        end_seconds = target_seconds + (time_window_minutes * 60)

        # Split conversation into lines
        lines = conversation_array
        extracted_lines = []

        for line in lines:
            # Look for timestamp pattern in the line
            # Pattern: [seconds-seconds] or MM:SS format
            timestamp_match = re.search(r"\[(\d+\.?\d*)-(\d+\.?\d*)\]|(\d{1,2}:\d{2})", line)

            if timestamp_match:
                if timestamp_match.group(3):  # MM:SS format
                    line_minutes, line_seconds = map(int, timestamp_match.group(3).split(":"))
                    line_total_seconds = line_minutes * 60 + line_seconds
                else:  # Convert seconds to total seconds
                    line_total_seconds = float(timestamp_match.group(1))

                # Check if line is within time window
                if start_seconds <= line_total_seconds <= end_seconds:
                    extracted_lines.append(line)
            else:
                # If no timestamp found, include line if we're already collecting
                if extracted_lines:
                    extracted_lines.append(line)

        return "\n".join(extracted_lines)

        # except Exception as e:
        #     print(f"Error extracting conversation segment: {e}")
        #     return ""
