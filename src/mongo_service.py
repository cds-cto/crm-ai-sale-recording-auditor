# ******* External Imports
import requests
import configparser
import os
from datetime import datetime, timedelta, timezone

# ******* Project Imports
from mongoDB import MongoConnect


class MongoService:
    def __init__(self, config_file, config_name):
        self.current_folder = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_folder, config_file)
        config = configparser.ConfigParser()
        config.read(config_file_path)

        self.ai_sale_general_error_list = MongoConnect(
            config_file=config_file,
            config_name=config_name,
        )

    # ********************************************************************************************************
    # Get General Error List
    # ********************************************************************************************************
    def get_general_error_list(self):
        prompt = ""
        general_error_list = self.ai_sale_general_error_list.collection.find()
        for error in general_error_list:
            prompt += f"- {error['issue_code']}: {error['issue_name']}\n"
            for check in error["issue_check"]:
                prompt += f"{check}\n"
            prompt += "\n\n"
        return prompt

    # ********************************************************************************************************
    # Find Error List by Code
    # ********************************************************************************************************

    def find_error_list_by_code(self, error_code: str):
        # ********  Find error list by code
        error_list = self.ai_sale_general_error_list.collection.find_one({"issue_code": error_code})
        return error_list
