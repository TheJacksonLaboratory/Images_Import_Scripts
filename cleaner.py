import os
import shutil

def rm_imported_images():
    os.chdir(r"\\jax.org\jax\phenotype\OMERO\KOMP\ImagesToBeImportedIntoOmero")
    for filename in os.listdir():
        file_path = os.path.join(os.getcwd(), filename)
        
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


rm_imported_images()