# %%
# import libraries
import pandas as pd
import sqlite3
from pathlib import Path

# %%
# get path for data
base_dir = Path(__file__).resolve().parents[3]
data_dir = base_dir / "TBA_project_backup" / "train_delay.db"

# %%
# establish SQL connection to database and load into dataframe
con = sqlite3.connect(data_dir)
df = pd.read_sql_query("SELECT * from train_delay", con)

# %%
# inspect database
df.shape
df.info()
df.head(5)
df["delay_in_min"].describe()
# df["train_type"].value_counts()

# %%
# check data
df_filtered = df[(df["train_name"] == "ICE 920")]
df_filtered

# %%

