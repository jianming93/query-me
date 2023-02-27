import sys

import pandas as pd

def construct_payload_for_gpt3(query_string, dfs_w_metas):
    query_start_string = "SELECT"
    # Initialise prompt string that indicates what type of database it is
    prompt_string = "### SQLite tables, with their properties:\n#"
    # Extract all database and their column names
    for df_tuple in dfs_w_metas:
        records = df_tuple[-1]
        df = pd.DataFrame(records)
        table_name = df_tuple[0]
        df_columns = tuple(df.columns.tolist())
        table_string = f"\n# {table_name}{df_columns}"
        prompt_string += table_string
    # Add in the the query string indicated by the user
    prompt_string += f"\n#\n### A query to {query_string}"
    # Add in the start token to begin generation of query
    prompt_string += f"\n{query_start_string}"
    return prompt_string, query_start_string


def table_type(df_column):
    # Note - this only works with Pandas >= 1.0.0
    if sys.version_info < (3, 0):  # Pandas 1.0.0 does not support Python 2
        return 'any'

    if isinstance(df_column.dtype, pd.DatetimeTZDtype):
        return 'datetime',
    elif (isinstance(df_column.dtype, pd.StringDtype) or
            isinstance(df_column.dtype, pd.BooleanDtype) or
            isinstance(df_column.dtype, pd.CategoricalDtype) or
            isinstance(df_column.dtype, pd.PeriodDtype)):
        return 'text'
    elif (isinstance(df_column.dtype, pd.SparseDtype) or
            isinstance(df_column.dtype, pd.IntervalDtype) or
            isinstance(df_column.dtype, pd.Int8Dtype) or
            isinstance(df_column.dtype, pd.Int16Dtype) or
            isinstance(df_column.dtype, pd.Int32Dtype) or
            isinstance(df_column.dtype, pd.Int64Dtype)):
        return 'numeric'
    else:
        return 'any'