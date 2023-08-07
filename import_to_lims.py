import logging
import os
import sys
from datetime import datetime
import mysql.connector as mysql
import pandas as pd
import ezomero
import utils
import time
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

"""
1. Monitor the drop-box for log file, parse the log message if detected
2. Update the image import status table
    -> If import success, set import status to be "success" and add log message to "message" column
    -> If failed, send a message to slack channel and update import status to be "fail" and add log message to "message" column
3. Query the db for filename and testcode, use the filename to generate omero url
4. Create a csv file using omero url and testcode

TODO 08/08/2023
1. Test the app in the production enviornment
"""


testfiles = ['fundus2_A-12625_OS1 08-41-46.059 06-07-23-1.tif',
            'fundus2_A-12625_OS 08-41-08.447 06-07-23-1.tif',
            'fundus2_A-12651_OD 10-34-27.137 06-07-23-1.tif']


class MonitorFolder(FileSystemEventHandler):

    def on_created(self, event):
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)

        file_added = event.src_path
        logger.info(file_added)

        if file_added.endswith(".log"):

            success_imported_files = []

            #Parse the log file
            with open(file_added, "r") as f:
                lines = f.readlines()
                for line in lines:
                    if "Success" in line:
                        line_split = line.split(" ")
                        filename = line_split[3] + " " + line_split[4] + " " + line_split[5]
                        success_imported_files.append(filename)
                        
                        '''
                        update_status(filename=image.name,
                                      status=image.status,
                                      message=line)
                        '''
                        
            imported_images = Imported_Images(images=success_imported_files, status="Success")
            test_name = imported_images.get_test_name()
            test_code = imported_images.get_test_code()
            image_urls = imported_images.get_omero_urls()
            IMG_INFO = pd.concat([image_urls, test_code], axis=1).rename_axis(None)

            #Generate .csv file in the corresponding folder
            csv_file_name = os.path.splitext(file_added.split("/")[-1])
            logger.info(csv_file_name)
            try:
                if test_name == "Eye Morphology":
                    target = "Z:/EYE-MORPHOLOGY/KOMP/images-omero"
                    IMG_INFO.to_csv(f"{target}/{csv_file_name}.csv")

                if test_name == "Gross Pathology":
                    target = "Z:/GrossPathology/KOMP/images-omero"
                    IMG_INFO.to_csv(f"{target}/{csv_file_name}.csv")

                if test_name == "ERG":
                    target = "Z:/ERG-V2/KOMP/images-omero"
                    IMG_INFO.to_csv(f"{target}/{csv_file_name}.csv")

                else:
                    logger.error(f"Invalid test found: {test_name}")

            except Exception as err:
                logger.error(err)

            #IMG_INFO.to_csv(f"/Users/chent/Desktop/KOMP_Project/OMERO_TO_LIMS/KOMP-Import/{csv_file_name}.csv")

    def on_modified(self, event):
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)

    def on_deleted(self, event):
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)

    def on_moved(self, event):
        print(event.src_path, event.event_type)
        logger.info(event.src_path + " " + event.event_type)


class Imported_Images():
    
    TEST = {
        "fundus2": "Eye Morphology",
        "path": "Gross Pathology",
        "fundus": "ERG"
    }


    procedureDefVersionKey = {
        "Gross Pathology": 230,
        "Eye Morphology": 231,
        "ERG": 254
    }


    def __init__(self, images, status) -> None:
        self.images = images
        self.status = status

    
    def get_omero_urls(self) -> pd.DataFrame:
        """
        Function to get omero urls
        :return: Metadata of images, e.g. testcode, animalid etc
        :rtype: pd.DataFrame
        """

        urls = []
        for file in self.images:
            base_url = "https://omeroweb.jax.org/webgateway/img_detail/"
            conn_to_omero = ezomero.connect(user="chent",
                                            password="Ql4nc,tzjzsblj!",
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
                
                #logger.info(f"Image ids for {file} is {im_filter_ids}")

                for image_id in im_filter_ids:
                    url = base_url + str(image_id)
                    urls.append(url)
                    print(url)
                    logger.info(f"Image url is {url}")

        conn_to_omero.close()
        IMG_URL = pd.DataFrame(urls, columns=["Filename"])
        return IMG_URL
    

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
            test = self.TEST[file.split("_")[0]]
            logger.debug(f"Test of image {file} is {test}")
            procedureDefkey = self.procedureDefVersionKey[test]
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
    

    def get_test_name(self) -> str:

        img_types = []
        for file in self.images:
            if "fundus2" in file:
                type = self.TEST["fundus2"]
                img_types.append(type)

            if "fundus" in file:
                type = self.TEST["fundus"]
                img_types.append(type)

            if "path" in file:
                type = self.TEST["path"]
                img_types.append(type)

            else:
                logger.error(f"{file} is not a komp file")
                return
            
        def all_same(items):
            return all(x == items[0] for x in items)
        
        assert all_same(img_types)
        return img_types[0]
        

    
def update_status(filename:str, 
                  status: str, 
                  message:str):
    
    conn = mysql.connect(host=db_server, user=db_username, password=db_password, database="komp")

    def if_exist():
        conn = mysql.connect(host=db_server, user=db_username, password=db_password, database="komp")
        query = f"""SELECT COUNT(1) AS COUNT FROM komp.OMEROImportStatus WHERE Filename = {filename};"""
        c = conn.cursor(dictionary=True)
        c.execute(query)
        count = c.fetchall()["COUNT"]
        if count > 0:
            return utils.RECORD_EXIST
        else:
            return -1

    if if_exist() == utils.RECORD_EXIST:
        logger.info(f"{filename} is komp file")
        logger.info("Inserting.......")
        insert_stmt = f"""INSERT INTO komp.OMEROImportStatus (ImportStatus, Message) VALUES({status}, {message}) 
                    WHERE Filename = {filename};"""
        cursor = conn.cursor()
        cursor.execute(insert_stmt)
        conn.commit()
        conn.close()

    else:
        logger.warning(f"{filename} is not a komp file")
        return 


def main():
    
    src_path = "Y:/"
    event_handler = MonitorFolder()
    observer = Observer()
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




if __name__ == "__main__":

    username = utils.db_username
    password = utils.password

    db_server = utils.db_server
    db_username = utils.db_username
    db_password = utils.db_password

    job_name = 'OMERO_Import'
    logging_dest = os.path.join(os.getcwd(), "logs")
    date = datetime.now().strftime("%B-%d-%Y")
    logging_filename = logging_dest + "/" + f'{date}.log'
    logger = utils.createLogHandler(logging_filename)
    logger.info('Logger has been created')
    
    main()
