# 3rd party import
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from typing import Any
import certifi
import configparser
import os
import json


class MongoJSONEncoder(json.JSONEncoder):

    def default(self, o: Any) -> Any:
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return str(o)
        return json.JSONEncoder.default(self, o)


class MongoConnect:
    def __init__(self, config_file, config_name):
        # config load
        current_folder = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_folder, config_file)
        config = configparser.ConfigParser()
        config.read(config_file_path)

        # define class value
        self.connectiong_str = config[config_name]["uri"]
        self.db_name = config[config_name]["db_name"]
        self.collection_name = config[config_name]["collection"]

        # start client
        self.makeClient()

    # Create a new client and connect to the server
    def makeClient(self):
        self.client = MongoClient(self.connectiong_str, tlsCAFile=certifi.where())
        db = self.client.get_database(self.db_name)
        self.collection = db.get_collection(self.collection_name)

    # Close the MongoDB connection
    def closeConnection(self):
        if hasattr(self, "client"):
            self.client.close()
