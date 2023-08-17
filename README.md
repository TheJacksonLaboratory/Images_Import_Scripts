 # KOMP Images Import

## Description

This project is intend to import pictures taken from lab to Omero and LIMS. This project is made up by 2 parts: `transform-to_omero`, which generates the omero submission form and drop it along with images into the drop box,  and `import_to_lims`, which creates and drops the desired .csv file to the folder, which will be later collected by technicians. It contains the following features:

- Real-time file structure moniroting
- Trace, catch run-time errors and report to developer on time
- More pending implementations


## Prerequisite
- `Python 3.9 +`
- `Git`
- `MySQL `
- `pip`
- `conda`

Also, before you start installing and running the program, make sure you have the configuration file named `config.yml` in the following format:

```
database:
 name: database name(schema)
 user: database username
 password: database password
 host: host of the database

user:
  username: omero username
  password: omero password

app:
  log_path1: path/to/dir/of/your/log/of/transform-to_omero.py
  log_path2: path/to/dir/of/your/log/of/import_to_lims.py
  submission_form_name: submission_form_name.xlsx
  group_owner: yourgroupowner
  wk_group: yourgroup

  Eye:
    OD: "Right eye"
    OS: "Left Eye"
    OU: "Both"

  TEST:
    fundus2: Eye Morphology
    path: Gross Pathology
    fundus: ERG
    Slit: Eye Morphology

  procedureDefVersionKey:
    Gross Pathology: 230
    Eye Morphology: 231
    ERG: 254
```

## Installation

Now, in order to install the app, `cd ` to your work directory, then create a virtual environment in Python 3.9+. Normally I would suggest to use `venv`, but since this requires `ezomero` package and it has a conflicting bug when installing using `venv` or `pyenv`, be sure to only use `conda` to avoid it. 
```
conda creates -n yourenvname
```

Now, activate the virtual environment you just created use the following command:

```
conda activate yourenvname
```
Make sure you have `git` installed on your computer, use this command to pull the repository to your end:

```
git clone https://github.com/TheJacksonLaboratory/OMERO_Import_Strategy.git
```

Then use this command to install the dependency for the project:

```
pip install -r requirements.txt
```
Now everything is setup, you should be ready to this the app. 

## Usage

For now, running the app is simply like running any python script, open the terminal/command prompt, type the following command:

```
python /path/to/your/directory/transform_to_omero.py
python /path/to/your/directory/ import_to_lims.py
```
That's it, you can customize the run of the app by creating a bash/shell script or Batchfile script. 


