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
from jsonschema import ValidationError
from jsonschema.validators import validator_for



logger = logging.getLogger(__name__)

schema_directory = os.path.dirname(os.path.abspath(__file__))

too_schedule_config_path = os.path.join(schema_directory, "observing_request_schema.json")

with open(too_schedule_config_path, "rb") as f:
    too_db_schedule_config = json.load(f)

# Compile the validator ONCE at import time. jsonschema.validate() rebuilds
# (and re-checks) the whole validator on every call, which made per-row
# validation the dominant cost of loading a schedule file: ~2.5 s for a
# 79-row ToO, and the observing loop was validating the same file several
# times per cycle (2026-08-23). With a prebuilt validator the same
# validation is ~50x faster.
_validator_cls = validator_for(too_db_schedule_config)
_validator_cls.check_schema(too_db_schedule_config)
_schedule_validator = _validator_cls(too_db_schedule_config)


class RequestValidationError(Exception):
    pass

def validate_schedule_json(
    data: dict
):
    try:
        _schedule_validator.validate(data)
        # debug, not info: this fires once per ROW of every schedule load
        logger.debug("Successfully validated schema")
    except ValidationError as e:
        logger.error("Error with JSON schema validation, input data not formatted correctly.")
        logger.error(e)
        raise RequestValidationError(e)


def validate_schedule_df(
    df: pd.DataFrame
):
    # One json round-trip for the whole frame (this used to be TWO
    # Series.to_json calls per row). records-orientation also serializes
    # from the column dtypes, so e.g. an int64 obsHistID stays an int
    # instead of picking up a float upcast from mixed-dtype rows.
    for record in json.loads(df.to_json(orient="records")):
        validate_schedule_json(record)
        
        
"""
if __name__ == '__main__':
    import sqlalchemy as db
    
    schedule = os.path.join(schema_directory, 'scheduleFiles', 'nightly_20230519.db')
    
    

    ### if we were able to load and query the SQL db, check to make sure the schema are correct
    validate_schedule_df(df)
"""