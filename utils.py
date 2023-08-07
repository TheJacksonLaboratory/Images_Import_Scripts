import logging

username = "chent"
password = "Ql4nc,tzjzsblj!"

db_server = "rslims.jax.org"
db_username = "dba"
db_password = "rsdba"

"""Setup logger"""

def createLogHandler(log_file):
    logger = logging.getLogger(__name__)
    FORMAT = "[%(asctime)s->%(filename)s->%(funcName)s():%(lineno)s]%(levelname)s: %(message)s"
    logging.basicConfig(format=FORMAT, filemode="w", level=logging.DEBUG, force=True)
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(handler)

    return logger


Eyes = {
        "OD": "Right eye",
        "OS": "Left Eye",
        "OU": "Both"
    }

TEST = {
        "fundus2": "Eye Morphology",
        "path": "Gross Pathology",
        "fundus": "ERG"
    }

    # ProcedureDefinitionKey: Eye Morphology=231, Gross Pathology = 230, ERGv2=274

PROC_DEF_KEY = {
        "Eye Morphology": 231,
        "Gross Pathology": 230,
        "ERGv2": 274
    }

RECORD_EXIST = 1