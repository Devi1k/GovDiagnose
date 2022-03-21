import logging
import os
import re
from logging.handlers import TimedRotatingFileHandler


class Logger:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.log_path = os.getcwd() + '/log/asr'
        self.log_fmt = '%(asctime)s\tFile \"%(filename)s\",line %(lineno)s\t%(levelname)s: %(message)s'
        self.formatter = logging.Formatter(self.log_fmt)
        self.logger = logging.getLogger("Diagnose")

    def getLogger(self):
        self.logger.setLevel(logging.INFO)
        self.logger.suffix = "%Y-%m-%d_%H-%M.log"
        self.logger.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}.log$")
        log_file_handler = TimedRotatingFileHandler(filename=self.log_path, when="D", interval=1, backupCount=7)
        log_file_handler.setFormatter(self.formatter)

        self.logger.addHandler(log_file_handler)
        return self.logger
