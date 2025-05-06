import pyodbc
import os
import configparser


class SqlConnect():

    def __init__(self,config_file,config_name):
        # config load
        current_folder = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_folder, config_file)
        config = configparser.ConfigParser()
        config.read(config_file_path)
            
        self.server = config[config_name]['SERVER']
        self.database = config[config_name]['DATABASE']
        self.uid =  config[config_name]['UID'] 
        self.pwd =    config.get(config_name, 'PWD') 
        self.driver = 'ODBC Driver 17 for SQL Server'
        
    # CLOSE CONNECTION
    def close(self):
    
        self.c.close()
        self.conn.close()        
        print('SQL connection closed')
    
       
    # DATA BASE CONNECTION STRING
    def init(self):
        connection_string = (
            f'DRIVER={self.driver};'
            f'SERVER={self.server};'
            f'DATABASE={self.database};'
            f'UID={self.uid};'
            f'PWD={self.pwd};'
        )
        self.conn = pyodbc.connect(connection_string, timeout=20)
        self.c = self.conn.cursor()
    
    #Commit 
    def commit(self,SQL,param = None):
        self.c.execute(SQL,param)
        self.conn.commit()
    
    #FETCHONE  
    def fetchone(self,SQL,param = None):
        self.c.execute(SQL,param)       
        result = self.c.fetchone()    
        return result
    
    #FETCHALL
    def fetchall(self,SQL,param = None):
        self.c.execute(SQL,param)       
        result = self.c.fetchall()    
        return result
    
    
