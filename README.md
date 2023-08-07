 # KOMP Images Import

## Description

This project is intend to import pictures taken from lab to Omero and LIMS. It contains the following features:

- Real-time file structure moniroting
- Trace, catch run-time errors and report to developer on time


## Prerequisite
- `Python 3.9 +`
- `Git`
- `MySQL `
- `pip`

## Installation

To install the app, `cd ` to your work directory, then create a virtual environment in Python 3.9+, If you would like to use `venv` like I do, run the following command

```
python3 -m venv .env/yourenvname
```

you can use `conda` or whatever you like to set up. 
Now, activate the virtual environment you just created use the following command:

```
. .env/yourenvname/bin/activate
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
python /path/to/your/directory/import_to_omero.py
```


