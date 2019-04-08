# -*- coding: utf-8 -*-
#
# Copyright Veracode Inc., 2014

import boto3
from   jsonschema import validate
from   jsonschema.exceptions import ValidationError
import logging
import os

from   deployer.exceptions import MissingConfigurationParameterException
from   deployer import s3


logger = logging.getLogger(os.path.basename('deployer'))


def bootstrap(config):
    """
    Configure the existing account for subsequent deployer runs.
    Create S3 buckets & folders, upload artifacts required by
    infrastructure to them.

    Args:
        config: dictionary containing all variable settings required
                to run terraform with

    Returns:
        config dict.
    """
    config['project_config'] = config.get('project_config',
                                          s3.get_bucket_name(config, 'data'))
    config['tf_state_bucket'] = config.get('tf_state_bucket',
                                           s3.get_bucket_name(config,'tfstate'))

    logmsg = "{}: Creating S3 project bucket: {}"
    logger.debug(logmsg.format(__name__, config['project_config']))
    s3.create_bucket(config['project_config'])

    logmsg = "{}: Creating S3 project bucket: {}"
    logger.debug(logmsg.format(__name__, config['tf_state_bucket']))
    s3.create_bucket(config['tf_state_bucket'])

    upload_staged_artifacts(config)
    return config


def upload_staged_artifacts(config):
    """
    Upload artifacts specified in config file to S3 bucket location.

    Args:
        config: dictionary containing all variable settings required
                to run terraform with

    Returns:
        True on success

    Raises:
         ValueError exception on failure.
    """
    schema = {
        "type": "object",
        "project_config":   { "type": "string"},
        "staged_artifacts": { "type": "object"},
        "required": ["project_config", "staged_artifacts"]
    }
    try:
        validate(config, schema)
    except ValidationError as e:
        msg = "{}: Configuration missing key fields. {}".format(__name__,
                                                                e.message)
        logger.error(msg)
        raise MissingConfigurationParameterException(msg)

    logmsg = "{}: Uploading staged artifacts to {}"
    logger.debug(logmsg.format(__name__, config['project_config']))

    s3resource = boto3.resource('s3')
    bucket_name = config['project_config']

    for bucket_key in config['staged_artifacts'].keys():
        source_file = os.path.abspath(config['staged_artifacts'][bucket_key])
        bucket_file = s3resource.Object(bucket_name, bucket_key)

        if not os.path.isfile(source_file):
            msg = "File {} does not exist".format(source_file)
            logger.critical(msg)
            raise SystemExit(msg)

        try:
            bucket_file.upload_file(source_file)
            log_msg = "Uploaded {} to {}/{}"
            logger.debug(log_msg.format(source_file,
                                        bucket_name,
                                        bucket_key))
        except ValueError as v:
            log_msg = "Error uploading {} to {}/{}: {}".format(source_file,
                                                               bucket_name,
                                                               bucket_key,
                                                               v.args[0])
            logger.critical(log_msg)
            raise ValueError(log_msg)

    return True
