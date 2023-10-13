import argparse
import logging
import os
import sys
from datetime import datetime
import mysql.connector as mysql
import pandas as pd
import ezomero
import time
import pymsteams
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver
import read_config as cfg
import az_devops as az
from logging.handlers import TimedRotatingFileHandler
import glob
import shutil


"""
1. Monitor the drop-box for log file, parse the log message if detected
2. Update the image import status table
    -> If import success, set import status to be "success" and add log message to "message" column
    -> If failed, send a message to slack channel and update import status to be "fail" and add log message to "message" column
3. Query the db for filename and testcode, use the filename to generate omero url
4. Create a csv file using omero url and testcode

TODO 10-13-2023

Add remove folder functionality
"""


class MonitorFolder(FileSystemEventHandler):

    #Function to handle newly created file in monitoring folder
    def on_created(self, event):
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)
        file_added = event.src_path
        logger.info(file_added)
        error_message = ""
        if file_added.endswith(".log"):

            try:
                success_imported_files = []

                # Parse the newly generated log file
                with open(fr"{file_added}", "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        if "Success" in line:
                            line_split = line.split(" ")
                            filename = line_split[3] if line_split[3].endswith(".JPG") or line_split[3].endswith(".tif") else f"{line_split[3]} {line_split[4]} {line_split[5]}"
                            logger.info(filename)
                            success_imported_files.append(filename)
                            send_message_on_teams(Message =f"{filename} successfully imported to OMERO")
                        
                    imported_images = Imported_Images(images=success_imported_files, status="Success")
                    test_name = imported_images.get_test_name()
                    test_code = imported_images.get_test_code()
                    image_urls = imported_images.get_omero_urls()

                    # Generate .csv file in the corresponding folder
                    IMG_INFO = pd.concat([image_urls, test_code], axis=1).rename_axis(None)
                    csv_file_name = file_added.split("\\")[-1].replace(".", "-")
                    logger.info(csv_file_name)
                   
                    target = dest[test_name]
                    IMG_INFO.to_csv(f"{target}/{csv_file_name}.csv")
                    
                    logger.info("Moving all successful files into archive . . .")
                    imported_images.migrate_files()
                     
            except Exception as err:
                error_message = str(err)
                logger.error(error_message)
                
            finally:
                if error_message:
                    az.create_work_item(error_message)
    
            

    #Function to handle file modification in monitoring folder
    def on_modified(self, event):
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)

    #Function to handle file delete in monitoring folder
    def on_deleted(self, event):
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)

    #Function to handle file movement in monitoring folder
    def on_moved(self, event):
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)


class Imported_Images:

    def __init__(self, images, status) -> None:
        self.images = images
        self.status = status


    #Function to query omero urls
    def get_omero_urls(self) -> pd.DataFrame:
        """
        :return: Metadata of images, e.g. testcode, animalid etc
        :rtype: pd.DataFrame
        """

        urls = []
        for file in self.images:
            base_url = "https://omeroweb.jax.org/webgateway/img_detail/"
            conn_to_omero = ezomero.connect(user=omero_username,
                                            password=omero_password,
                                            host="ctomero01lp.jax.org",
                                            port=4064,
                                            group="KOMP_eye",
                                            secure=True,
                                            config_path='.ezomero')
            conn_to_omero.connect()
            datasets = ezomero.get_dataset_ids(conn_to_omero, 203)
            for data in datasets:
                images_ids = ezomero.get_image_ids(conn_to_omero, dataset=data)
                im_filter_ids = ezomero.filter_by_filename(conn_to_omero,
                                                           images_ids,
                                                           file,
                                                           True)

                for image_id in im_filter_ids:
                    url = base_url + str(image_id)
                    urls.append(url)
                    print(url)
                    logger.info(f"Image url is {url}")

        conn_to_omero.close()
        IMG_URL = pd.DataFrame(urls, columns=["Filename"])
        return IMG_URL

    #Function to query database for testcode
    def get_test_code(self) -> pd.DataFrame:

        """
        Function to get metadata of an image from database
        :return: Metadata of images, e.g. testcode, animalid etc
        :rtype: pd.DataFrame
        """

        logger.info("Connecting to database")
        conn = mysql.connect(host=db_server, user=db_username, password=db_password, database="rslims")
        cursor = conn.cursor(buffered=True, dictionary=True)
        cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        stmt = """ SELECT
                        _ProcedureInstance_key AS 'Test Code'
                    FROM
                        Organism
                    INNER JOIN
                        ProcedureInstanceOrganism USING (_Organism_key)
                    INNER JOIN
                        ProcedureInstance USING (_ProcedureInstance_key)
                    WHERE
                        _ProcedureDefinitionVersion_key = {} 
                    AND 
                        OrganismID = '{}';"""

        DB_RECORDS = []

        for file in self.images:
            organism_id = file.split("_")[1]
            test = TEST[file.split("_")[0]]
            logger.debug(f"Test of image {file} is {test}")
            procedureDefkey = procedureDefVersionKey[test]
            logger.debug(f"Procedure definition version key of {file} is {procedureDefkey}")
            logger.debug(f"Get metadata of image associated with animal {organism_id}")
            cursor.execute(stmt.format(procedureDefkey, organism_id))
            record = cursor.fetchall()

            if record:
                DB_RECORDS.append(record[0])

        cursor.close()
        conn.close()

        TEST_CODE = pd.DataFrame(DB_RECORDS, columns=["Test Code"])
        print(TEST_CODE)

        return TEST_CODE

    #Function to get the test/experiment of the image
    def get_test_name(self) -> str:

        img_types = []
        try:
            for file in self.images:
                test_of_img = file.split("_")[0]
                logger.info(f"Fetching test for {test_of_img}")
                #assert test_of_img in TEST.keys()
                type = TEST[test_of_img]
                img_types.append(type)
                assert all(x == img_types[0] for x in img_types)

        except (AssertionError, KeyError) as err:
                error_message = str(err)
                logger.error(error_message)
                az.create_work_item(personal_access_token=access_token,
                                    type="Bug",
                                    state="New",
                                    title=f"Errors detected in {job_name} in function get_test_name()",
                                    comment=error_message,
                                    assign_to=az_username,
                                    team=az_team)
                
        logger.debug(img_types)
        return img_types[0]

    #Function to move succesfully imported files to archive folder
    def migrate_files(self) -> None:
        files = self.images

        #Get locations of files to move 
        files_to_move = []
        for file in files:
            pathname = r"\\jax.org\jax\phenotype\OMERO\KOMP\ImagesToBeImportedIntoOmero"
            files_to_move.extend(glob.glob(pathname=pathname + "/**/" + file, recursive=True))
            print(f"Files needs to move is {files_to_move}")
            
        #Move file to the archive folder
        for f in files_to_move:
            logger.info(f"Moving file {f}")
            shutil.copy(f, archive)
        

def send_message_on_teams(Message: str) -> None:
    myTeamsMessage = pymsteams.connectorcard("https://jacksonlaboratory.webhook.office.com/webhookb2/bd1ec35a-4544-41cd-a6aa-0f1b378d70a8@5d665caa-d62e-4678-9f5f-e707cf9ecbd1/IncomingWebhook/8e140d840e964c78987c792740a566d3/ab0e816b-f287-45e4-a845-7a4937f09c6d")
    myTeamsMessage.text(Message)
    myTeamsMessage.send()


def rm_dir() -> None:
    pass

 # Setup logger
def createLogHandler(log_file):
    logger = logging.getLogger(__name__)
    FORMAT = "[%(asctime)s->%(filename)s->%(funcName)s():%(lineno)s]%(levelname)s: %(message)s"
    logging.basicConfig(format=FORMAT, filemode="w", level=logging.DEBUG, force=True)
    handler =TimedRotatingFileHandler(log_file, when="midnight", backupCount=10)
    handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(handler)
    return logger
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='JaxLims Image Import')
    parser.add_argument(
        "-c", "--conf", action="store", dest="conf_file",
        help="Path to config file"
    )

    args = parser.parse_args()
    cfg = cfg.parse_config(path="config.yml")

    # Setup credentials for database
    db_server = cfg['database']['host']
    db_name = cfg['database']['name']
    db_username = cfg['database']['user']
    db_password = cfg['database']['password']

    # Setup credentials of omero
    omero_username = cfg['user']['username']
    omero_password = cfg['user']['password']

    # Setup credentials for Azure DevOps
    access_token = cfg['azure']['access token']
    az_username = cfg['azure']['email']
    az_team = cfg['azure']['team']

    # Setup data for the app
    dest = cfg['transfer_to_lims']['dest']
    TEST = cfg['transfer_to_lims']['TEST']
    procedureDefVersionKey = cfg['transfer_to_lims']['procedureDefVersionKey']
    archive = cfg['transfer_to_lims']['archive']

    #Setup logger
    job_name = 'transfer_to_lims'
    logging_dest = cfg['transfer_to_lims']['log_path']
    date = datetime.now().strftime("%B-%d-%Y")
    logging_filename = logging_dest + "/" + f'{job_name}-{date}.log'
    logger = createLogHandler(logging_filename)
    logger.info('Logger has been created')

    # Create file watcher
    src_path = r"\\jax.org\jax\omero-drop\dropbox"
    #src_path = os.getcwd()
    event_handler = MonitorFolder()
    observer = PollingObserver()
    observer.schedule(event_handler, path=src_path, recursive=True)
    logger.info("Monitoring started")
    observer.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        sys.exit()
