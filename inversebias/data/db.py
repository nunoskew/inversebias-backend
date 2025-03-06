import functools
import pandas as pd
import os
import time
from inversebias.data.utils import create_dtype
from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlite3 import connect
from inversebias.config import settings


class InverseBiasEngine:
    _instance = None
    _engine = None
    _last_modified = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InverseBiasEngine, cls).__new__(cls)
            cls._create_engine()
        return cls._instance

    @classmethod
    def _create_engine(cls):
        # Extract the file path from the URI
        db_path = settings.database.uri.replace("sqlite:///", "")
        # Update the last modified time
        try:
            cls._last_modified = os.path.getmtime(db_path)
        except OSError:
            cls._last_modified = 0

        # Create the engine
        cls._engine = create_engine(
            settings.database.uri,
            echo=settings.database.echo,
            pool_size=settings.database.pool_size,
            # These options help with database file changes
            connect_args={"check_same_thread": False},
        )

    @property
    def engine(self) -> Engine:
        # Check if the database file has been modified
        db_path = settings.database.uri.replace("sqlite:///", "")
        try:
            current_mtime = os.path.getmtime(db_path)
            if current_mtime > self._last_modified:
                # Database file has changed, recreate the engine
                self._engine.dispose()
                self.__class__._create_engine()
        except OSError:
            # File doesn't exist yet, will be created on first access
            pass
        return self._engine


def get_table(table_name, return_if_not_exists=False):
    engine = InverseBiasEngine().engine

    if not table_exists(table_name):
        if return_if_not_exists:
            return pd.DataFrame()
        raise ValueError(f"Invalid table name: '{table_name}'")

    query = text(f"SELECT * FROM {table_name}")
    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    return df


def upload_to_table(primary_key="url", table_name=None, verbose=False, upload=True):
    """
    Decorator that uploads the function's return value to a database table.

    Args:
        primary_key (str): The primary key for the table.
        table_name (str, optional): The name of the table. If None, it will be inferred.
        verbose (bool, optional): Whether to print verbose output.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if kwargs.get("upload", False):
                actual_table_name = table_name
                table_upload(
                    df=result,
                    primary_key=primary_key,
                    table_name=actual_table_name,
                    verbose=kwargs.get("verbose", verbose),
                )
            return result

        return wrapper

    return decorator


def table_exists(table_name: str) -> bool:
    engine = InverseBiasEngine().engine
    return table_name in inspect(engine).get_table_names()


def sql_append_df(df: pd.DataFrame, table_name: str, dtype: dict | None = None):
    # Extract just the filename from the database URI
    db_path = settings.database.uri.replace("sqlite:///", "")

    with connect(db_path) as conn:
        df.to_sql(
            table_name,
            conn,
            if_exists="append",
            index=False,
            dtype=dtype,
        )


def sql_replace_df(df: pd.DataFrame, table_name: str, primary_key: str):
    dtype = create_dtype(df)
    dtype[primary_key] += " PRIMARY KEY"

    # Extract just the filename from the database URI
    db_path = settings.database.uri.replace("sqlite:///", "")

    with connect(db_path) as conn:
        df.to_sql(
            table_name,
            conn,
            if_exists="replace",
            index=False,
            dtype=dtype,
        )


def table_upload(df: pd.DataFrame, table_name: str, primary_key: str, verbose=False):
    dtype = None
    if table_exists(table_name=table_name):
        table = get_table(table_name)
        df = df.loc[~df[primary_key].isin(table[primary_key])]
        if df.empty:
            return
    else:
        dtype = create_dtype(df)
        dtype[primary_key] += " PRIMARY KEY"
    sql_append_df(
        df=df.drop_duplicates(subset=primary_key), table_name=table_name, dtype=dtype
    )
    if verbose:
        print(f"Uploaded {len(df)} rows to the {table_name} table in the database.")
