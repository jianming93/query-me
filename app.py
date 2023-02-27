
import os
import base64
import io
import json
import requests
from pathlib import Path

from dotenv import load_dotenv
import pandas as pd
import dash
from dash import html, dcc, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from sqlalchemy import create_engine
import openai

from utils import construct_payload_for_gpt3, table_type

ALLOWED_FILETYPES = ("csv")
# Load env
load_dotenv()
# Configure openai
openai.api_key = os.getenv("OPENAI_API_KEY")

### Components ###
# Navbar
navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Img(
                            src="assets/favicon.ico",
                            height="35px",
                        ),
                        style={"padding-right": 0}
                    ),
                    dbc.Col(
                        dbc.NavbarBrand(
                            "Query Me",
                            id="text-app-name",
                            className="ms-2"
                        ),
                        style={"padding-left": 0}
                    )
                ]
            ),
        ]
    ),
    color="primary",
    dark=True,
)
# Upload sub header
upload_sub_header = html.Div(
    "Upload CSV files to perform queries on",
    id="text-upload-sub-header"
)
# Upload area
upload_area = dcc.Upload(
    html.Div(
        [
            "Drag and Drop or ",
            html.A("Select Files"),
        ]
    ),
    id="upload-csv-files",
    style={
        'width': '100%',
        'height': '60px',
        'lineHeight': '60px',
        'borderWidth': '1px',
        'borderStyle': 'dashed',
        'borderRadius': '5px',
        'textAlign': 'center',
    },
    # Allow multiple files to be uploaded
    multiple=True
)
# CSV Viewer
csv_viewer_sub_header = html.Div(
    "Navigate and view CSV data",
    id="text-csv-viewer-sub-header"
)
csv_viewer_name_sub_header = html.Div(
    "Table Name:",
    id="text-csv-viewer-filename-sub-header"
)
csv_viewer_button_group_nav = dbc.ButtonGroup(
    [
        dbc.Button(
            "Previous",
            id="button-csv-viewer-previous"
        ),
        dbc.Button(
            "Next",
            id="button-csv-viewer-next"
        ),
    ],
    id="buttongroup-csv-viewer",
    style={
        "float": "right"
    }
)
csv_viewer_table = html.Div(
    dash_table.DataTable(
        id="table-csv-viewer",
        page_current=0,
        page_size=10,
        filter_action="native",
        sort_action="native",
    ),
    className="dbc dbc-row-selectable"
)

# Text area query
query_sub_header = html.Div(
    "Enter the desired query you wish to perform on your data",
    id="text-query-sub-header"
)
query_text_area = dbc.Textarea(
    placeholder="Please enter your query here",
    id="textarea-query",
    rows=5
)
query_submit_button = dbc.Button(
    "Submit",
    id="button-query-submit",
    style={
        "float": "right"
    },
    color="success"
)
query_form = dbc.Form(
    [
        query_sub_header,
        html.Br(),
        query_text_area,
        html.Br(),
        query_submit_button
    ],
    id="form-query"
)
# Results container
results_container = dbc.Container(
    [
        html.Div(
            "Query Results",
            id="text-query-results-sub-header"
        ),
        dbc.Spinner(
            html.Div(
                dash_table.DataTable(
                    id="table-query-results",
                    page_current=0,
                    page_size=10,
                    filter_action="native",
                    sort_action="native",
                ),
                className="dbc dbc-row-selectable"
            ),
            color="info"
        ),
        html.Br(),
        html.Div(
            id="download-results-container",
            children=[
                dbc.Button(
                    "Download",
                    id="button-download-results"
                ),
                dcc.Download(id="download-results-csv")
            ],
            style={
                "float": "right"
            },
        )
    ]
)
# Invalid file toast
invalid_file_toast = dbc.Toast(
    f"Invalid filetype was uploaded! Please only upload the following file types: {ALLOWED_FILETYPES}",
    id="toast-invalid-file",
    header="An error has occured!",
    color="danger",
    header_class_name="bg-danger text-white",
    is_open=False,
    dismissable=True,
    duration=5000,
    style={
        "position": "fixed",
        "bottom": 20,
        "right": 10,
    }
)
# SQL Query error toast
sql_error_toast = dbc.Toast(
    "Generation of the results has encountered an issue! Please try a different "
    "text query input and also make sure the tables are successfully uploaded!",
    id="toast-sql-error",
    header="An error has occured!",
    color="danger",
    header_class_name="bg-danger text-white",
    is_open=False,
    dismissable=True,
    duration=5000,
    style={
        "position": "fixed",
        "bottom": 20,
        "right": 10,
    }
)
# Download error toast
download_error_toast = dbc.Toast(
    "Please check if results was successfully generated before clicking the 'Download' button!",
    id="toast-download-error",
    header="An error has occured!",
    color="danger",
    header_class_name="bg-danger text-white",
    is_open=False,
    dismissable=True,
    duration=5000,
    style={
        "position": "fixed",
        "bottom": 20,
        "right": 10,
    }
)
### Layout ###
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = dash.Dash(title="Query Me", update_title=None, external_stylesheets=[dbc.themes.DARKLY, dbc.icons.BOOTSTRAP, dbc_css])
app.layout = dbc.Container(
    [
        dcc.Store(
            id="store-memory-app",
            storage_type="memory",
            data={
                "dfs": []
            }
        ),
        dcc.Store(
            id="store-current-index",
            storage_type="memory",
            data={
                "current_index": 0
            }
        ),
        dcc.Store(
            id="store-results-df",
            storage_type="memory",
            data={
                "results": None
            }
        ),
        navbar,
        dbc.Container(
            [
                dbc.Row(
                    upload_sub_header
                ),
                html.Br(),
                dbc.Row(
                    upload_area
                )
            ],
            class_name="pt-5 pb-5"
        ),
        dbc.Container(
            [
                dbc.Row(
                    csv_viewer_sub_header
                ),
                html.Br(),
                dbc.Row(
                    [
                        dbc.Col(
                            csv_viewer_name_sub_header,
                            width=8
                        ),
                        dbc.Col(
                            csv_viewer_button_group_nav,
                            width=4,
                        )
                    ]
                ),
                html.Br(),
                dbc.Row(
                    dbc.Spinner(
                        csv_viewer_table,
                        color="info"
                    )
                ),
                html.Br(),
                dbc.Row(
                    query_form,
                ),
                dbc.Row(
                    results_container
                ),
                html.Br()
            ]
        ),
        invalid_file_toast,
        sql_error_toast,
        download_error_toast,
    ],
    fluid=True,
    class_name="p-0"
)

### Callbacks ###
# Upload Files callback
@app.callback(
    [
        Output("store-memory-app", "data"),
        Output("toast-invalid-file", "is_open")
    ],
    [
        Input("upload-csv-files", "contents"),
    ],
    [
        State("upload-csv-files", "filename"),
        State("upload-csv-files", "last_modified")
    ],
)
def store_upload_files(list_of_contents, list_of_filenames, list_of_dates):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    memory_dict = {
        "dfs": [], "results": None
    }
    for i in range(len(list_of_contents)):
        content = list_of_contents[i]
        filename = list_of_filenames[i]
        filename_wo_ext = Path(filename).stem
        file_date = list_of_dates[i]
        content_type, content_string = content.split(",")
        if "csv" not in content_type:
            return {"dfs": [], "results": None}, True
        # Read into pandas
        decoded_content_string = base64.b64decode(content_string)
        df = pd.read_csv(
            io.StringIO(
                decoded_content_string.decode('utf-8')
            )
        )
        # Store in cache
        memory_dict["dfs"].append((filename_wo_ext, filename, file_date, df.to_dict("records")))
    return memory_dict, False


# Display file callback
@app.callback(
    [
        Output("table-csv-viewer", "columns"),
        Output("table-csv-viewer", "data"),
        Output("text-csv-viewer-filename-sub-header", "children"),
        Output("store-current-index", "data")
    ],
    [
        Input("store-memory-app", "data"),
        Input("button-csv-viewer-previous", "n_clicks"),
        Input("button-csv-viewer-next", "n_clicks")
    ],
    [
        State("store-current-index", "data")
    ]
)
def display_upload_files(dfs_store_data, previous_n_clicks, next_n_clicks, current_index_store_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    if len(dfs_store_data["dfs"]) == 0:
        return None, "Table Name:", {"current_index": 0}
    triggered_ctx = ctx.triggered[0]['prop_id'].split('.')[0]
    if "previous" in triggered_ctx:
        if current_index_store_data["current_index"] - 1 < 0:
            index_to_retrieve = len(dfs_store_data["dfs"]) - 1
        else:
            index_to_retrieve = current_index_store_data["current_index"] - 1
    elif "next" in triggered_ctx:
        if current_index_store_data["current_index"] + 1 >= len(dfs_store_data["dfs"]):
            index_to_retrieve = 0
        else:
            index_to_retrieve = current_index_store_data["current_index"] + 1
    else:
        index_to_retrieve = 0
    current_index_store_data["current_index"] = index_to_retrieve
    # Dataframe is stored at the last index of the tuple
    df = pd.DataFrame.from_records(dfs_store_data["dfs"][index_to_retrieve][-1])
    return (
        [{'name': i, 'id': i, 'type': table_type(df[i])} for i in df.columns],
        dfs_store_data["dfs"][index_to_retrieve][-1],
        "Table Name: {}".format(dfs_store_data["dfs"][index_to_retrieve][0]),
        current_index_store_data
    )


# Query model callback
@app.callback(
    [
        Output("table-query-results", "columns"),
        Output("table-query-results", "data"),
        Output("store-results-df", "data"),
        Output("toast-sql-error", "is_open"),
    ],
    [
        Input("button-query-submit", "n_clicks"),
    ],
    [
        State("store-memory-app", "data"),
        State("textarea-query", "value")
    ]
)
def send_for_query(query_n_clicks, current_data_store, query_string):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    try:
        if query_n_clicks:
            # Construct openai payload string
            prompt_string, sql_query_start_string = construct_payload_for_gpt3(query_string, current_data_store['dfs'])
            # Send payload to openai to get sql query string
            response = openai.Completion.create(
                model="code-davinci-002",
                prompt=prompt_string,
                temperature=0,
                max_tokens=150,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stop=["#", ";"]
            )
            sql_query_string = response["choices"][0]["text"]
            # Anything before </code> will be the code. Sometimes extra content will be generated after that
            sql_query_string = sql_query_string.split("</code>")[0]
            # Remove \n. Remove trailling space after that
            sql_query_string = sql_query_string.replace("\n", " ").rstrip()
            # Extract the column names used for the query
            column_names = sql_query_string.split("FROM")[0].strip().split(", ")
            # If query has joins, column names will include the table name. Remove all table names for final output
            column_names = [column_name.split(".")[-1] for column_name in column_names]
            # Combine generated text with query start string
            sql_query_string = sql_query_start_string + sql_query_string
            # Save dataframes to in memory database
            engine = create_engine("sqlite:///:memory:", echo=False)
            # Run sql query
            for df_tuple in current_data_store['dfs']:
                df = pd.DataFrame(df_tuple[-1])
                df.to_sql(df_tuple[0], con=engine)
            results = []
            with engine.connect() as connection:
                raw_results = connection.execute(sql_query_string)
                for row in raw_results:
                    results.append(row)
            engine.dispose()
            # Convert to pandas dataframe
            results_df = pd.DataFrame(results, columns=column_names)
            # Generate table to return
            results_df_records = results_df.to_dict("records")
            return (
                [{'name': i, 'id': i, 'type': table_type(results_df[i])} for i in results_df.columns],
                results_df_records,
                {"results": results_df.to_dict("records")},
                False
            )
    except Exception as err:
        return (
            [],
            [],
            {"results": None},
            True
        )

# Download results Callback
@app.callback(
    [
        Output("download-results-csv", "data"),
        Output("toast-download-error", "is_open")
    ],
    [
        Input("button-download-results", "n_clicks"),
    ],
    [
        State("table-csv-viewer", "data"),
        State("store-results-df", "data")
    ]
)
def download_results(n_clicks, results_table_contents, results_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    try:
        results_df = pd.DataFrame(results_data["results"])
        if results_df:
            return (
                dcc.send_data_frame(results_df.to_csv, "results.csv"),
                False
            )
        else:
            return (
                None,
                True
            )
    except Exception as err:
        return (
            None,
            True
        )

if __name__ == "__main__":
    app.run_server(
        host="0.0.0.0",
        port="8050",
        debug=True
    )