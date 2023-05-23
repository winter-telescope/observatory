#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 23 12:47:43 2023

Lightweight adaptation of wintertoo schedule validation

Adapted from Robert Stein's wintertoo module

@author: nlourie
"""

import logging
import os
import pandas as pd
import json
from jsonschema import validate, ValidationError



logger = logging.getLogger(__name__)

schema_directory = os.path.dirname(os.path.abspath(__file__))

too_schedule_config_path = os.path.join(schema_directory, "observing_request_schema.json")

with open(too_schedule_config_path, "rb") as f:
    too_db_schedule_config = json.load(f)


class RequestValidationError(Exception):
    pass

def validate_schedule_json(
    data: dict
):
    try:
        validate(data, schema=too_db_schedule_config)
        logger.info("Successfully validated schema")
    except ValidationError as e:
        logger.error("Error with JSON schema validation, input data not formatted correctly.")
        logger.error(e)
        raise RequestValidationError(e)


def validate_schedule_df(
    df: pd.DataFrame
):
    for _, row in df.iterrows():
        json.loads(row.to_json())
        validate_schedule_json(json.loads(row.to_json()))
        
        
"""
if __name__ == '__main__':
    import sqlalchemy as db
    
    schedule = os.path.join(schema_directory, 'scheduleFiles', 'nightly_20230519.db')
    
    

    ### if we were able to load and query the SQL db, check to make sure the schema are correct
    validate_schedule_df(df)
"""