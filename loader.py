import csv
import io
import time
from typing import Tuple, List, Optional, IO, Iterable

import boto3

ATHENA_POLL_INTERVAL = 1  # In seconds
ATHENA_STATE_SUCCEEDED = {'SUCCEEDED'}
ATHENA_STATE_WAIT = {'QUEUED', 'RUNNING'}
ATHENA_STATE_ERROR = {'FAILED', 'CANCELLED'}


def _split_s3_path(s3_path: str) -> Tuple[str, str]:
    """
    Split an S3 URI (i.e. "s3://bucket/path/to/key") to a bucket and a key
    :param s3_path: fully qualified S3 URI of a key in a bucket
    :return: bucket and key
    """
    path_parts=s3_path.replace('s3://','').split('/')
    bucket=path_parts.pop(0)
    key="/".join(path_parts)
    return bucket, key


def _line_reader(handle: IO) -> Iterable[dict]:
    """
    Read a file-like object line by line, yielding rows (will strip linefeeds)
    :param handle: a file-like object
    """
    for line in handle:
        yield {'row': line.rstrip('\n')}


class AthenaError(Exception):
    """
    Represents an error returned from Athena
    """
    pass


class Inventory(object):

    def __init__(self, output_location: str, athena_database: str = 'default', athena_table: str = 'inventory'):
        self.athena_database = athena_database
        self.athena_table = athena_table
        self.output_location = output_location
        self.athena = boto3.client('athena')
        self.s3 = boto3.client('s3')

    def _prepare(self, query: str, **kwargs) -> str:
        return query.format(query, table_name=self.athena_table, **kwargs)

    def _load_response(self, data_uri: str) -> List[dict]:
        bucket, key = _split_s3_path(data_uri)
        obj = self.s3.get_object(Bucket=bucket, Key=key)
        body = obj.get('Body').read().decode('utf-8')
        body_handle = io.StringIO(body)
        if key.endswith('.csv'):
            return list(csv.DictReader(body_handle))
        else:
            return list(_line_reader(body_handle))

    def _get_results(self, execution_id: str) -> Tuple[bool, Optional[List[dict]]]:
        exec_status = self.athena.get_query_execution(
            QueryExecutionId=execution_id)
        state = exec_status.get('QueryExecution').get('Status').get('State')
        if {state} & ATHENA_STATE_SUCCEEDED:
            result_uri = exec_status.get('QueryExecution').get('ResultConfiguration').get('OutputLocation')
            return True, self._load_response(result_uri)
        elif {state} & ATHENA_STATE_WAIT:
            return False, None
        elif {state} & ATHENA_STATE_ERROR:
            reason = exec_status.get('QueryExecution').get('Status').get('StateChangeReason')
            raise AthenaError(f'Athena Query Status: {state}, reason: {reason}')
        raise AthenaError(f'Athena Query Status Unknown: {state}')

    def query(self, query: str, **kwargs) -> List[dict]:
        """
        IMPORTANT: THIS METHOD DOES NOT SANITIZE INPUT - IT IS UP TO THE USER TO PROTECT AGAINST SQL INJECTIONS

        Run a query against Athena. Will poll for results, parse them, and return an array of dicts as response.
        Use {table_name} as placeholder that will be replaced with the actual table name.
        kwargs will be interpolated as well.

        :param query: query string to be executed
        :return: a list of dictionaries, representing the result table
        """
        query = self._prepare(query, **kwargs)
        start_response = self.athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': self.athena_database},
            ResultConfiguration={'OutputLocation': self.output_location})
        execution_id = start_response.get('QueryExecutionId')
        while True:
            time.sleep(ATHENA_POLL_INTERVAL)
            ready, data = self._get_results(execution_id)
            if ready:
                return data
