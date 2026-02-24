#!/bin/bash
liquibase validate --changelog-file all_changes.yaml --url "${NEO4j_URL}" --username "${NEO4j_USER}" --password "${NEO4j_PASS}"
if [ $? != 0 ]
then
  >&2 echo "ERROR: The previous step failed. Check logs for details! Exiting..."
  exit 1
fi
liquibase update --changelog-file all_changes.yaml --url "${NEO4j_URL}" --username "${NEO4j_USER}" --password "${NEO4j_PASS}"
