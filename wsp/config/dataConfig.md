
# WINTER Database Configuration

A guide to using json config files with the `ObsWriter.py` python module to design the database used by the WINTER project.

## What is json?

First, a quick introduction to the `.json` file format. JSON stands for Javascript Object Notation, probably referring to how in javascript objects are formatted in a very similar way. JSON files can be written and read by a variety of programming languages, making them useful for sharing data between programs.

## How does it work?

JSON files are collections of key/value pairs, much like python dictionaries. Keys are always stings, while the values are allowed to take a variety of other forms, including further key/value pairs, strings, boolean values, arrays(lists), numbers, or null. Keys and Values are separated by the `:` symbol, and the key value pairs are separated by `,` symbols. For the purposes of this project, you can mostly imagine json files to be like python dictionaries.

## JSON in the WINTER DB config file

For the configuration of the WINTER database, we use a three level json file, with the first level representing the names of tables in a database, the second representing the names of the columns in each table, and the third representing the configuration of the columns themselves.

```javascript
{
  "Observation":{
    "obsHistID": {"type": "Integer", "primaryKey": true},
    "fieldID": {"type": "Integer"},
    "filter": {"type": "Text"},
    "night": {"type": "Integer"},
    "visitTime": {"type": "Real"},
    "visitExpTime": {"type": "Real"},
    "airmass": {"type": "Real"},
    "filtSkyBright": {"type": "Real"},
    "fiveSigmaDepth": {"type": "Real"},
    "dist2Moon": {"type": "Real"},
    "progID": {"type": "Integer", "altNames": ["propID"]},
    "subprogram": {"type": "Text"},
    "pathToFits": {"type": "Text"}
  },
  "Field":{
    "fieldID": {"type": "Integer", "primaryKey": true},
    "rightAscension": {"type": "Real", "altNames": ["fieldRA"]},
    "declination": {"type": "Real", "altNames": ["fieldDec"]}
  },
  "Night":{
    "nightID": {"type": "Integer", "primaryKey": true, "altNames": ["night"]},
    "avgTemp": {"type": "Real", "default": 273},
    "moonPhase": {"type": "Real"}
  }
}
```
Defining a new table is as easy as creating a new entry in the first level of the config file. The key should be a string, which names the table, and then the value is another javascript object, or python dictionary-like set of key value pairs, defining the columns in the table. The column names should also be strings mapped to dictionary-like objects.

To define the properties of each column we have a mapping of keys to values for supported properties of columns. `"type"` refers to the data type of the data belonging in that column, and should be included in the definition of every column. Other fields are optional, including `"primaryKey"`, which is mapped to a boolean value `true` or `false`. If this key value is not included in the definition, the code which reads the config file assumes that the column will not be a PRIMARY KEY.

In the future I may add support for other SQL column features, like increment, etc. (especially if requested).

Other optional features include the `"altNames"` field, and `"default"` field. `altNames` maps to a list of alternative names for the data which should be stored under a particular column. When `ObsWriter` prepares the data received from the telescope for archiving in the database, it first looks for data with the same name as the column, and if it cannot find anything for this value, will look for data with the names given in `altNames`. If it finds no data under the original column name nor under any of the provided altNames, it will check for a `"default"` value for the column. Otherwise it will record that field as `None` in python, which eventually is translated to `null` in the database(75% sure of this).
