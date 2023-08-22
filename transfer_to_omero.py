import argparse
import errno
import logging
import os
import shutil
import sys
from datetime import datetime
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver
import mysql.connector
import pandas as pd
import time
import openpyxl
import pymsteams
import read_config as cfg
import az_devops as az


class MonitorFolder(FileSystemEventHandler):

    def on_created(self, event):
        """

        :param event:
        :type event:
        :return:
        :rtype:
        """
        print(event.src_path, event.event_type)

        created_file = event.src_path.replace("\\", "/")
        logger.info(created_file + " " + event.event_type)
        image_metadata = []
        time.sleep(10)
        if os.path.isdir(created_file):
            try:
                curr_processing_folder = FolderToBeSent(directory=created_file, 
                                                        wkgroup=wkgroup, 
                                                        wkgroup_owner=group_owner, 
                                                        submission_form_name=submission_form_name,
                                                        dest = dest)
                IMG_INFO = curr_processing_folder.get_image_info()
                image_metadata.append(IMG_INFO)
                curr_processing_folder.generate_submission_form(IMG_INFO=IMG_INFO)
                curr_processing_folder.copyanything()
                
                '''
                def copyanything(src, dst) -> None:
                    """
                    Function to copy and paste a folder
                    Parameters
                    ----------
                    src : Source folder
                    dst : Location to place the copied and pasted folder

                    Returns
                    -------
                    """
                    logger.info(f"Copying {src} to {dst}")
                    try:
                        shutil.copytree(src, dst)
                    except OSError as exc:
                        if exc.errno in (errno.ENOTDIR, errno.EINVAL):
                            shutil.copy(src, dst)

                logger.debug(f"Drop folder {created_file} to OMERO Dropbox {dest}")
                copyanything(src=created_file,
                         dst=dest + "\\" + created_file.split("/")[-1])
                '''
            except IndexError as err1:
                error_message = str(err1)
                logger.error(error_message)
                az.create_work_item(personal_access_token=access_token,
                                    type="Bug",
                                    state="New",
                                    title=f"Errors detected in {job_name}",
                                    comment=error_message,
                                    assign_to=az_username,
                                    team=az_team)
                send_message_on_teams(Message=f"{error_message} at {job_name}")

            except pd.errors as err2:
                error_message = str(err2)
                logger.error(error_message)
                az.create_work_item(personal_access_token=access_token,
                                    type="Bug",
                                    state="New",
                                    title=f"Errors detected in {job_name}",
                                    comment=error_message,
                                    assign_to=az_username,
                                    team=az_team)
                send_message_on_teams(Message=f"{error_message} at {job_name}")

            except FileNotFoundError as err3:
                error_message = str(err3)
                logger.error(error_message)
                az.create_work_item(personal_access_token=access_token,
                                    type="Bug",
                                    state="New",
                                    title=f"Errors detected in {job_name}",
                                    comment=error_message,
                                    assign_to=az_username,
                                    team=az_team)
                send_message_on_teams(Message=f"{error_message} at {job_name}")

        else:
            pass

    def on_modified(self, event):
        """

        :param event:
        :type event:
        :return:
        :rtype:
        """
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)

    def on_deleted(self, event):
        """

        :param event:
        :type event:
        :return:
        :rtype:
        """
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)

    def on_moved(self, event):
        """

        :param event:
        :type event:
        :return:
        :rtype:
        """
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)


class FolderToBeSent:

    def __init__(self, 
                 directory, 
                 wkgroup_owner: str, 
                 wkgroup: str,
                 submission_form_name: str,
                 dest: str) -> None:
        
        self.directory = directory
        self.wkgroup_owner = wkgroup_owner
        self.wkgroup = wkgroup
        self.submission_form_name = submission_form_name
        self.dest = dest

    def get_image_info(self):
        """
        Function to get metadata of an image from database
        :param: FILE_TO_BE_IMPORTED: Subfolders in the OMERO import folder,
                i.e. //bht2stor.jax.org/phenotype/OMERO/KOMP/ImagesToBeImportedIntoOmero
        :type FILE_TO_BE_IMPORTED: str
        :return: Metadata of images
        :rtype: pd.DataFrame
        """

        logger.info("Connecting to database")
        conn = mysql.connector.connect(host=db_server, user=db_username, password=db_password, database=db_name)
        cursor = conn.cursor(buffered=True, dictionary=True)
        cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        stmt = """SELECT
                        'KOMP' as 'Project',  -- Project
                        StockNumber AS 'dataset',
                        'KOMP_EYE',  -- OMERO_group
                        OrganismID,
                        MarkerSymbol AS `gene`,
                        GenotypeSymbol AS `genotype`,
                        Sex, 
                        DateBirth, -- DATEDIFF(DateOfTest, DateBirth) in days
                        ProcedureAlias, 
                        DateCompleteMap.DateComplete
                    FROM
                        Organism
                            INNER JOIN
                        Line USING (_Line_key)
                            INNER JOIN
                        Genotype USING (_Organism_key)
                            INNER JOIN
                        cv_GenotypeSymbol USING (_GenotypeSymbol_key)
                            INNER JOIN
                        LineMarker USING (_Line_key)
                            INNER JOIN
                        Marker USING (_Marker_key)
                            INNER JOIN
                        cv_Sex USING (_Sex_key)
                            INNER JOIN
                        ProcedureInstanceOrganism USING (_Organism_key)
                            INNER JOIN
                        ProcedureInstance USING (_ProcedureInstance_key)
                            INNER JOIN
                        DateCompleteMap USING (_ProcedureInstance_key)
                    WHERE 
                        ProcedureAlias = 'Eye Morphology'
                    AND 
                        OrganismID = '{}';"""

        DB_RECORDS = []
        EYE_INFO = []
        FILE_NAMES = []
        files = os.listdir(self.directory)
        logger.info(f"Files pending processed are {files}")
        for f in files:
            logger.info(f"Process file {f}")
            FILE_NAMES.append(f)
            organism_id = f.split("_")[1]

            def get_eye():
                tmp = f.split("_")[2].split(" ")[0]
                for key in Eyes.keys():
                    if key in tmp:
                        return Eyes[key]
                return ""

            eye = get_eye()
            EYE_INFO.append(eye)
            logger.debug(f"Get metadata of image associated with animal {organism_id}")
            cursor.execute(stmt.format(organism_id))
            record = cursor.fetchall()
            if record:

                def to_lower_case(dict_: dict) -> dict:
                    if not dict_:
                        return {}

                    return {k.lower(): v for k, v in dict_.items()}

                DB_RECORDS.append(to_lower_case(record[0]))

        cursor.close()
        conn.close()

        EYE_INFO = pd.DataFrame(EYE_INFO)
        IMG_METADTA = pd.DataFrame(DB_RECORDS)
        IMG_FILE_NAME = pd.DataFrame(FILE_NAMES, columns=["filename"])

        IMG_INFO = pd.concat([IMG_FILE_NAME, IMG_METADTA, EYE_INFO], axis=1)
        IMG_INFO = IMG_INFO.reset_index(drop=True)

        print("Resulting cells are:")
        print(IMG_INFO)

        return IMG_INFO


    def generate_submission_form(self,
                                 IMG_INFO: pd.DataFrame,
                                 PARENT_DIR: str) -> None:
        """
            Function to create the submission form for omero import
            :param wkgroup_owner:
            :type wkgroup_owner:
            :param IMG_INFO:Metadata to be inserted into excel spreadsheet
            :type IMG_INFO: pd.DataFrame
            :param username: Username of OMERO
            :type username: String
            :param wkgroup: Work group of OMERO
            :type wkgroup: String
            :param filename: Name of generated excel file
            :type filename: String
            :param PARENT_DIR: Directory to put the generated submission form
            :type PARENT_DIR: String
            :return: None
            :rtype:
        """
        credentials = {"OMERO user:": self.wkgroup_owner, "OMERO group:": self.wkgroup}
        USER_INFO = pd.DataFrame.from_dict(credentials, orient="index")

        filename = self.submission_form_name
        logger.debug(f"Generating form {filename}")
        with pd.ExcelWriter(filename,
                            mode='w') as writer:
            USER_INFO.to_excel(writer, sheet_name='Submission Form', startrow=0, startcol=0, header=False)
            IMG_INFO.to_excel(writer, sheet_name='Submission Form', startrow=4, startcol=0, header=True, index=False)

        def send_to(file: str, dest: str) -> None:
            """
            :param file:
            :type file:
            :param dest:
            :type dest:
            :return:
            :rtype:
            """
            try:
                logger.debug(f"Send {file} to {dest}")
                shutil.copy(file, dest)

            except FileExistsError as e:
                pass

        send_to(file=filename, dest=PARENT_DIR)
        os.remove(filename)

    def copyanything(self) -> None:
        
        src = self.directory
        dst = self.dest
        logger.info(f"Copying {src} to {dst}")
        try:
            shutil.copytree(src, dst)
        except OSError as exc:
            if exc.errno in (errno.ENOTDIR, errno.EINVAL):
                shutil.copy(src, dst)

       

def send_message_on_teams(Message: str) -> None:
    myTeamsMessage = pymsteams.connectorcard("https://jacksonlaboratory.webhook.office.com/webhookb2/67b2b0a4-f061-41e9-accb-f334ca625680@5d665caa-d62e-4678-9f5f-e707cf9ecbd1/IncomingWebhook/db63504c727b4f68bb77bdb36d7c5c83/ab0e816b-f287-45e4-a845-7a4937f09c6d")
    myTeamsMessage.text(Message)
    myTeamsMessage.send()



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='My awesome script')
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

    # Setup information for generating submission form
    group_owner = cfg['transfer_to_omero']['group_owner']
    wkgroup = cfg['transfer_to_omero']['wk_group']
    submission_form_name = cfg['transfer_to_omero']['submission_form_name']
    Eyes = cfg['transfer_to_omero']['Eye']
    src = cfg['transfer_to_omero']['src']
    dest = cfg['transfer_to_omero']['dest']

    # Setup credentials for Azure DevOps
    access_token = cfg['azure']['access token']
    az_username = cfg['azure']['email']
    az_team = cfg['azure']['team']


    # Setup logger
    def createLogHandler(log_file):
        logger = logging.getLogger(__name__)
        FORMAT = "[%(asctime)s->%(filename)s->%(funcName)s():%(lineno)s]%(levelname)s: %(message)s"
        logging.basicConfig(format=FORMAT, filemode="w", level=logging.DEBUG, force=True)
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(FORMAT))
        logger.addHandler(handler)

        return logger


    job_name = 'transform_to_omero'
    logging_dest = cfg['transfer_to_omero']['log_path']
    date = datetime.now().strftime("%B-%d-%Y")
    logging_filename = logging_dest + "/" + f'{job_name}-{date}.log'
    logger = createLogHandler(logging_filename)
    logger.info('Logger has been created')

    # Contruct the WatchDog to monitor the file system
    #src = r"\\jax.org\jax\phenotype\OMERO\KOMP\ImagesToBeImportedIntoOmero"
    #dest = r"\\jax.org\jax\omero-drop\dropbox"
    event_handler = MonitorFolder()
    observer = PollingObserver()
    observer.schedule(event_handler, path=src, recursive=True)
    logger.info("Monitoring started")
    observer.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        sys.exit()
