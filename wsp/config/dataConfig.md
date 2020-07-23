
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
