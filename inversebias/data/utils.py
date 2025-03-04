import pandas as pd
from numpy.dtypes import Int64DType, ObjectDType
from inversebias.config import settings, SOURCE_TO_URL, SUBJECTS
from pandera import DataFrameModel


def create_dtype(df: pd.DataFrame) -> dict:
    type_mapper = {
        "object": "TEXT",
        "int64": "INTEGER",
        "float64": "REAL",
        "bool": "INTEGER",
        "datetime64[ns]": "TEXT",
    }
    d = dict(df.dtypes)
    dtype = {key: type_mapper.get(str(d[key]), "TEXT") for key in d.keys()}
    return dtype


def read_text_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as file:
        content = file.read()
    return content


def empty_dataframe_from_model(Model: DataFrameModel) -> pd.DataFrame:
    schema = Model.to_schema()
    return pd.DataFrame(columns=schema.dtypes.keys()).astype(
        {col: str(dtype) for col, dtype in schema.dtypes.items()}
    )


def groupby_mode(df: pd.DataFrame, group_cols, value_col) -> pd.DataFrame:
    # Define a function to calculate mode
    def mode_func(x):
        mode_result = x.mode()

        if mode_result.empty:
            return "N/A"
        pcts = x.value_counts(normalize=True)
        if pcts.max() < settings.analysis.bias_threshold:
            return "N/A"
        return mode_result.iloc[0]

    # Group by the specified columns and apply the mode function
    return df.groupby(group_cols)[value_col].agg(mode_func).reset_index()
