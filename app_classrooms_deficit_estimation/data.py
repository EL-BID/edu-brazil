import pandas as pd

# Read only required columns to save memory
required_columns = [
    "name_muni",
    "pop_3_months_3_years_adj", # INF_CRE
    "pop_4_5_years_adj", # INF_PRE
    "pop_6_10_years_adj", # FUND_AI
    "pop_11_14_years_adj", # FUND_AF
    "pop_15_17_years_adj", # MED
    "QT_MAT_INF_CRE", "QT_MAT_INF_PRE", "QT_MAT_FUND_AI", "QT_MAT_FUND_AF", "QT_MAT_MED",
    "QT_MAT_INF_CRE_INT", "QT_MAT_INF_PRE_INT", "QT_MAT_FUND_AI_INT", "QT_MAT_FUND_AF_INT", "QT_MAT_MED_INT",
    "QT_MAT_INF_CRE_PROP", "QT_MAT_INF_PRE_PROP", "QT_MAT_FUND_AI_PROP", "QT_MAT_FUND_AF_PROP", "QT_MAT_MED_PROP",
    "QT_MAT_BAS_N",
    "QT_SALAS_UTILIZADAS",
    ## NEW PRIVATE SCHOOL VARIABLES ##
    "PRIVATE_QT_MAT_INF_CRE", "PRIVATE_QT_MAT_INF_PRE", "PRIVATE_QT_MAT_FUND_AF", "PRIVATE_QT_MAT_FUND_AI", "PRIVATE_QT_MAT_MED",
    ## NEW PRIVATE SCHOOL VARIABLES ##
    "hex", 
    # "geometry" # Do not include geometry to save memory (from ~200MB to ~15MB)
]

hex_df = pd.read_parquet("data/25022025_dashboard_hexs.parquet", columns=required_columns)
hex_df.to_parquet("data/25022025_dashboard_hexs_light.parquet")
