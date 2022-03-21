import logging


class Logger:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("Diagnose")

    def getLogger(self):
        handler1 = logging.FileHandler("base" + ".log")
        handler1.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s|%(name)-12s+ %(levelname)-8s++%(message)s')
        handler1.setFormatter(formatter)
        self.logger.addHandler(handler1)
        return self.logger
