from typing import List, Dict
from constant import TRANSACTION_CODES


class ValidationService:
    def __init__(self):
        self.transaction_codes = TRANSACTION_CODES()

    def valid_audio_file(self, file_path: str) -> bool:
        """Validate if file is an audio file"""
        audio_extensions = [".mp3", ".wav", ".m4a"]
        return any(file_path.lower().endswith(ext) for ext in audio_extensions)

    def validate_all(self, summary_dict: dict) -> Dict[str, List[str]]:
        """Validate error codes from GPT summary and return results"""
        error_codes = []

        # Check if summary_dict has error_code_list
        if "error_code_list" in summary_dict:
            for error in summary_dict["error_code_list"]:
                if isinstance(error, dict) and "error_code" in error:
                    error_codes.append(error["error_code"])
                elif isinstance(error, str):
                    error_codes.append(error)

        return {
            "status": "success" if not error_codes else "error",
            "error_code_list": error_codes,
        }
