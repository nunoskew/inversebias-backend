import pandas as pd
from numpy.dtypes import Int64DType, ObjectDType
from inversebias.config import settings, SOURCE_TO_URL, SUBJECTS
from pandera import DataFrameModel
from sqlalchemy.types import Text, Integer, Float, Boolean, DateTime


def create_dtype(df: pd.DataFrame) -> dict:
    """
    Create SQLAlchemy column types based on DataFrame dtypes.
    This works with both SQLite and PostgreSQL.
    """
    type_mapper = {
        "object": Text,
        "int64": Integer,
        "float64": Float,
        "bool": Boolean,
        "datetime64[ns]": DateTime,
    }
    d = dict(df.dtypes)
    dtype = {key: type_mapper.get(str(d[key]), Text) for key in d.keys()}
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
    # Define a function to calcula-te mode
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
