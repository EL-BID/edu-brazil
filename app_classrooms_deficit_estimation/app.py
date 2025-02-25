import json
import time
import dash
from dash import dcc, html, Input, Output, dash_table, State
from dash.exceptions import PreventUpdate
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
import geopandas as gpd
import urbanpy as up
import h3
from shapely.geometry import Polygon
import dash_leaflet as dl

INITIAL_MUNICIPALITY = None
MIN_HEX_SIZE_AT_STATE_LEVEL = 6

# Load and preprocess the data
para_muni = gpd.read_file("data/para_muni.geojson")

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
    "hex", "geometry"
]

hex_gdf = pd.concat([
    gpd.read_parquet("data/25022025_dashboard_hexs_part1.parquet", columns=required_columns),
    gpd.read_parquet("data/25022025_dashboard_hexs_part2.parquet", columns=required_columns),
    gpd.read_parquet("data/25022025_dashboard_hexs_part3.parquet", columns=required_columns)
])

# Replace "pop_3_months_3_years" with  "pop_INF_CRE"
hex_gdf = hex_gdf.rename(columns={
    "pop_3_months_3_years_adj": "pop_INF_CRE",
    "pop_4_5_years_adj": "pop_INF_PRE",
    "pop_6_10_years_adj": "pop_FUND_AI",
    "pop_11_14_years_adj": "pop_FUND_AF",
    "pop_15_17_years_adj": "pop_MED",
})

education_levels = ["INF_CRE", "INF_PRE", "FUND_AI", "FUND_AF", "MED"]
education_levels_labels = {
    "INF_CRE": "Educação Infantil Creche",
    "INF_PRE": "Educação Infantil Pré-Escola",
    "FUND_AI": "Ensino Fundamental Anos Iniciais",
    "FUND_AF": "Ensino Fundamental Anos Finais",
    "MED": "Ensino Médio",
}
education_levels_short_labels = {
    "INF_CRE": "Creche",
    "INF_PRE": "Pré-Escola",
    "FUND_AI": "Fund. Anos Iniciais",
    "FUND_AF": "Fund. Anos Finais",
    "MED": "Ensino Médio",
    "index": "",
}

# Note to avoid merging empty columns names, we will use variable length empty strings e.g. " ", "  ", "   ", etc.
COLUMN_LABELS = {
    "#": ["", "#"],
    "short_address": [" ", "Endereço"],
    "city_state": ["  ", "Cidade"],
    "QT_SALAS_NECESARIAS_EXTRA_TOTAL": ["Número de Novas Salas Necessárias", "Total"],
    'QT_SALAS_NECESARIAS_EXTRA_INF_CRE': ["Número de Novas Salas Necessárias", "Creche"],
    'QT_SALAS_NECESARIAS_EXTRA_INF_PRE': ["Número de Novas Salas Necessárias", "Pré-Escola"],
    'QT_SALAS_NECESARIAS_EXTRA_FUND_AI': ["Número de Novas Salas Necessárias", "Fund.\nAnos Iniciais"],
    'QT_SALAS_NECESARIAS_EXTRA_FUND_AF': ["Número de Novas Salas Necessárias", "Fund.\nAnos Finais"],
    'QT_SALAS_NECESARIAS_EXTRA_MED': ["Número de Novas Salas Necessárias", "Ensino Médio"],
}

#  Here's a table that combines the resolution, average hexagon area in km², a relatable analogy, and a simple comparative description:

# | **Resolution** | **Area (km²)** | **Analogy**                            | **Comparative Description**                                         |
# |----------------|----------------|----------------------------------------|---------------------------------------------------------------------|
# | 5              | 252.90         | Size of a small town                   | Covers a large area with very broad details.                        |
# | 6              | 36.13          | Size of a neighborhood                 | Covers a moderate area with general details, similar to a few city blocks. |
# | 7              | 5.16           | Size of a small city block             | Covers a smaller area with more detail, like a small community or park.     |
# | 8              | 0.74           | Size of a large shopping mall          | Covers a very specific area with high detail, suitable for local analyses.  |

# This table should help users quickly understand the implications of choosing different resolutions by relating each option to familiar concepts and providing a concise description of the coverage and detail level.

H3HEX_RESOLUTIONS = {
    5: {
        'area': 2.56,
        'analogy': 'Área de um bairro pequeno',
        'description': 'Adequado para análises em nível de bairro ou pequenas áreas urbanas.'
    },
    6: {
        'area': 0.65,
        'analogy': 'Área de um quarteirão',
        'description': 'Adequado para análises em nível de quarteirão ou áreas urbanas médias.'
    },
    7: {
        'area': 0.16,
        'analogy': 'Área de um conjunto de edifícios',
        'description': 'Adequado para análises em nível de conjunto de edifícios ou áreas urbanas densas.'
    },
    8: {
        'area': 0.04,
        'analogy': 'Área de um edifício grande',
        'description': 'Adequado para análises em nível de edifício ou áreas urbanas muito densas.'
    }
}
# Slider marks with resolution, analogy, and description
slider_marks = {
    5: '~252.9 km² (Cidade pequena)',
    6: '~36.13 km² (Bairro)',
    7: '~5.16 km² (Zona de bairro)',
    8: {
        'label': '~0.74 km² (Vizinhança)', 
        # Force the label to be in a single line
        'style': {'white-space': 'nowrap'}
    }
}


def calculate_table_data(name_muni=None):

    if name_muni and "name_muni" in hex_gdf.columns:
        print("Selected municipality:", name_muni)
        filtered_hexs = hex_gdf[hex_gdf["name_muni"] == name_muni]
    else:
        print("No municipality selected")
        filtered_hexs = hex_gdf.copy()
    
    print("1. Filtered hexs shape", filtered_hexs.shape)
        
    # Calculate defaults for the table
    main_table = []

    ### NEW VARIABLES WITH ESTIMATED POP & STUDENTS IN PRIVATE SCHOOL ### 

    # A - population on each level 
    pop_per_level = filtered_hexs[[f'pop_{level}' for level in education_levels]].sum().round(0).values.tolist()
    main_table.append(pop_per_level)

    # A1 - % population outside of school
    pop_not_in_school_per_level = []
    for level in education_levels:
        pop_not_in_school = 1 - (filtered_hexs[f"QT_MAT_{level}"].sum() / filtered_hexs[f'pop_{level}'].sum())
        pop_not_in_school *= 100
        pop_not_in_school_per_level.append(pop_not_in_school)
    main_table.append(pop_not_in_school_per_level)
    
    # A2 - % students in private schoools
    students_in_private_per_level = []
    for level in education_levels:
        # students_private_schools = 1 - (filtered_hexs[f"PRIVATE_QT_MAT_{level}"].sum() / filtered_hexs[f"QT_MAT_{level}"].sum())
        students_private_schools = filtered_hexs[f"PRIVATE_QT_MAT_{level}"].sum() / filtered_hexs[f"pop_{level}"].sum()
        students_private_schools *= 100
        students_in_private_per_level.append(students_private_schools)
    main_table.append(students_in_private_per_level)

    # B - Total # of students in the public system (CALCULATED)
    students_in_public_per_level = []
    for i, level in enumerate(education_levels):
        students_in_public_edu = pop_per_level[i] * (1 - (pop_not_in_school_per_level[i]/100) - (students_in_private_per_level[i]/100))
        students_in_public_per_level.append(students_in_public_edu)
    main_table.append(students_in_public_per_level)

    # # C - Total # of students in the public system (CENSO)
    # students_public = []
    # for i, level in enumerate(education_levels):
    #     students_public_value = filtered_hexs[f"QT_MAT_{level}"].sum() - filtered_hexs[f"PRIVATE_QT_MAT_{level}"].sum()
    #     students_public.append(students_public_value)
    # main_table.append(students_public)

    ### NEW VARIABLES WITH ESTIMATED POP & STUDENTS IN PRIVATE SCHOOL ### 

    # total number of students on each level
    # main_table.append(filtered_hexs[[f'QT_MAT_{level}' for level in education_levels]].sum().values.tolist())

    # percentage of students in integral time (Tempo Integral)
    main_table.append([100 * (filtered_hexs[f"QT_MAT_{level}_INT"].sum() / filtered_hexs[f"QT_MAT_{level}"].sum()) for level in education_levels])
    # percentage of students in nocturnal time (Tempo Noturno)
    main_table.append([
        100 * ((filtered_hexs["QT_MAT_BAS_N"] * filtered_hexs[f"QT_MAT_{level}_PROP"]).sum() / filtered_hexs[f"QT_MAT_{level}"].sum())
        if level not in ["INF_CRE", "INF_PRE", "FUND_AI"] else 0 
        for level in education_levels 
    ])
    # total number of places available
    total_places = []

    # Row indexes
    TOTAL_STUDENTS  = 3
    PCT_STUDENTS_INT = 4
    PCT_STUDENTS_NOC = 5
    for i, level in enumerate(education_levels):
        # total number of students * (1 + percentage of students in integral time) * (1 - percentage of students in nocturnal time)
        num_cadeiras = main_table[TOTAL_STUDENTS][i] * (1 + main_table[PCT_STUDENTS_INT][i] / 100) * (1 - main_table[PCT_STUDENTS_NOC][i] / 100)
        total_places.append(num_cadeiras)
    main_table.append(total_places)

    main_table = pd.DataFrame(
        data=main_table, 
        columns=education_levels, 
        index=[
            "População Estimada",
            "Porcentagem da População fora da Escola (%)",
            "Porcentagem de Alunos em Escolas Privadas (%)",
            "Número Total de Alunos em Escolas Publicas",
            # "Número Total de Alunos Matriculados Escola Publica (CENSO)",
            # "Número Total de Alunos Matriculados",
            "Porcentagem de Alunos em Tempo Integral (%)", 
            "Porcentagem de Alunos em Período Noturno (%)", 
            "Número Total de Vagas Necessárias",
        ]
    ) 

    # Calculate the number of classrooms needed based on the user defined number of chairs per classroom

    # Number of chairs per classroom 
    # Source: https://normativasconselhos.mec.gov.br/normativa/pdf/CEE-PA_RESOLUC387C383O20001.201020REGULAMENTAC387C383O20EDUC.20BAS.20atualizada20em2001.06.2015_0.pdf
    # Creche/Daycare (0 to 1 years) - 8 students per classroom (NOT CONSIDERED)
    # Creche/Daycare (1 to 3 years) - 15 students per classroom
    # Pré-Escola/Pre-Kindergarten (4 to 5 years) - 25 students per classroom
    # Anos Iniciais do Ensino Fundamental/Elementary School (6 to 10 years) - 35 students per classroom
    # Anos Finais do Ensino Fundamental/Middle School (11 to 14 years) - 40 students per classroom
    # Ensino Médio/High School (15 to 17 years) - 40 students per classroom

    num_chairs = [15, 25, 35, 40, 40]
    main_table.loc["Número Total de Vagas por Sala"] = num_chairs

    # Number of classrooms needed in total
    main_table.loc["Número de Salas Necessárias"] = np.ceil(main_table.loc["Número Total de Vagas Necessárias"] / num_chairs)

    # Actual number of classrooms
    main_table.loc["Número de Salas Existentes"] = [np.ceil((filtered_hexs["QT_SALAS_UTILIZADAS"] * filtered_hexs[f"QT_MAT_{level}_PROP"]).sum()) for level in education_levels]

    # Number of classrooms needed in each level
    main_table.loc["Número de Novas Salas Necessárias"] = np.ceil(
        np.maximum(main_table.loc["Número de Salas Necessárias"] - main_table.loc["Número de Salas Existentes"], 0)
    )

    main_table.reset_index(inplace=True)

    # Fix column names with education_levels_short_labels
    main_table.columns = [education_levels_short_labels[col] for col in main_table.columns]

    return main_table.round(2)


def calculate_extra_salas(name_muni, selected_variables, rows, hex_res):

    # Visualize the results for the selected municipality
    if name_muni and "name_muni" in hex_gdf.columns:
        muni_hexagons = hex_gdf[hex_gdf["name_muni"] == name_muni]
    else:
        muni_hexagons = hex_gdf.copy()
        print("muni_hexagons", muni_hexagons.shape)
        # muni_hexagons = gpd.GeoDataFrame(hex_gdf.drop(columns=["geometry"]).values, geometry=hex_gdf.geometry, crs="EPSG:4326")

    # Calculate the number of classrooms needed based on the user defined variables
    main_table = pd.DataFrame(rows)
    
    # Set old columns names
    if len(main_table.columns) == 6:
        main_table.columns = ["index"] + education_levels
    if len(main_table.columns) == 7:
        main_table.columns = ["index"] + education_levels + ["editable"]

    main_table.set_index(main_table.columns[0], inplace=True)
    main_table.loc[:, education_levels] = main_table[education_levels].astype(float).values

    print("Recalculating the number of classrooms needed based on the user defined variables on the table ... ", end="")
    for level in education_levels:
        # Calculate the proportion of students in each hexagon
        prop_mat = muni_hexagons[f"QT_MAT_{level}"] / muni_hexagons[f"QT_MAT_{level}"].sum() 
        # Calculate the total number of students in each hexagon
        total_qt_alumnos = prop_mat * main_table.loc["Número Total de Alunos em Escolas Publicas", level] 
        # Calculate the total number of chairs needed in each hexagon
        qt_cadeiras = total_qt_alumnos * (1 + main_table.loc["Porcentagem de Alunos em Tempo Integral (%)", level] / 100) * (1 - main_table.loc["Porcentagem de Alunos em Período Noturno (%)", level] / 100) 
        # Calculate the number of classrooms needed in each hexagon
        muni_hexagons.loc[:, f"QT_SALAS_NECESARIAS_TOTAL_{level}"] = qt_cadeiras / main_table.loc["Número Total de Vagas por Sala", level] 
        # Calculate the actual number of classrooms in each hexagon
        muni_hexagons.loc[:, f"QT_SALAS_ACTUALES_{level}"] = (
            muni_hexagons["QT_SALAS_UTILIZADAS"] * muni_hexagons[f"QT_MAT_{level}_PROP"]
        )
        # Calculate the number of extra classrooms needed in each hexagon
        muni_hexagons.loc[:, f"QT_SALAS_NECESARIAS_EXTRA_{level}"] = np.ceil(
            np.maximum(
                muni_hexagons[f"QT_SALAS_NECESARIAS_TOTAL_{level}"]
                - muni_hexagons[f"QT_SALAS_ACTUALES_{level}"],
                0,
            )
        )
    print("Done")


    print("SELECTED VARIABLES", selected_variables)
    if isinstance(selected_variables, str):
        selected_variables = [selected_variables]

    print("CALCULATING THE SUM OF THE SELECTED VARIABLES")
    print("muni_hexagons.shape", muni_hexagons.shape)
    muni_hexagons.loc[:, "SalasNecessariasAcum"] = muni_hexagons[selected_variables].sum(axis=1)
    muni_hexagons = muni_hexagons.dropna(subset=["SalasNecessariasAcum"])
    print("dropna > muni_hexagons.shape", muni_hexagons.shape)
    muni_hexagons = muni_hexagons[muni_hexagons["SalasNecessariasAcum"] > 0]
    print("> 0 -muni_hexagons.shape", muni_hexagons.shape)
    print("Done")

    # Change the hexagon resolution based on the user input (hex_res)

    # Check the current resolution of the hexagons
    current_hex_res = h3.h3_get_resolution(muni_hexagons.hex.iloc[0])
    
    print(f"Current hexagon resolution: {current_hex_res}")

    if hex_res != current_hex_res:
        print(f"Rescaling the hexagons to resolution {hex_res} ... ", end="")

        # muni_hexagons = up.geom.resolution_downsampling(
        #     muni_hexagons,
        #     "hex",
        #     hex_res,
        #     {f"QT_SALAS_NECESARIAS_EXTRA_{level}": "sum" for level in education_levels} | {"SalasNecessariasAcum": "sum"},
        # )
        agg = {f"QT_SALAS_NECESARIAS_EXTRA_{level}": "sum" for level in education_levels} | {"SalasNecessariasAcum": "sum"}

        coarse_hex_col = "hex_{}".format(hex_res)
        muni_hexagons[coarse_hex_col] = muni_hexagons["hex"].apply(
            lambda x: h3.h3_to_parent(x, hex_res)
        )
        dfc = muni_hexagons.groupby([coarse_hex_col]).agg(agg).reset_index()
        gdfc_geometry = dfc[coarse_hex_col].apply(lambda x: Polygon(h3.h3_to_geo_boundary(x, geo_json=True)))
        
        muni_hexagons_coarse = gpd.GeoDataFrame(dfc, geometry=gdfc_geometry, crs="EPSG:4326")
        print("Done")

        return muni_hexagons_coarse

    
    print("COLUMNS IN HEXAGON DATAFRAME", muni_hexagons.columns)

    if 'hex' in muni_hexagons.columns:
        # Replace 'hex' to f"hex_{hex_res}"
        muni_hexagons.rename(columns={"hex": f"hex_{hex_res}"}, inplace=True)

        return muni_hexagons

initial_table_data = calculate_table_data(INITIAL_MUNICIPALITY)

user_defined_rows = [1,2,4,5,7,9]
calculated_rows = [0,3,6,8,10]

# Valor por default en portugues es "Valor padrão"
# Create tooltips for user-defined rows

def calculate_tooltips(table_data):
    return [
        {column: {'value': f"*Valor padrão:* {round(row[column], 2) if isinstance(row[column], float) else row[column]}", 'type': 'markdown'} 
        for column in table_data.columns} if index in user_defined_rows 
        else {column: {'value': "Valor calculado", 'type': 'markdown'} for column in table_data.columns}
        for index, row in table_data.iterrows() 
    ]
initial_tooltips = calculate_tooltips(initial_table_data)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

server = app.server

# Layout

app_header = dbc.Row(
    [
        dbc.Col(
            [
                html.Br(),
                html.H2("Dashboard | Gestão de Expansão Escolar: Análise de Necessidades de Salas de Aula"),
                html.Br(),
                dbc.Alert(
                    dcc.Markdown('''
                        Este é um painel de controle educacional que permite visualizar e projetar a necessidade de novas salas de aula em diferentes níveis de ensino, com base na capacidade atual e na demanda existente para um município ou região selecionada.  
                        
                        **Como usar o painel: Passo a passo para gestores públicos de educação**  
                        
                        1. **Selecione o estado:** No primeiro menu suspenso, escolha o estado que deseja analisar.
                        1. **Selecione o município:** No segundo menu suspenso, escolha o município dentro do estado selecionado para visualizar os dados específicos da região.
                        1. **Veja os dados iniciais:** A tabela será preenchida automaticamente com os dados iniciais, mostrando o número de salas de aula necessárias para cada nível de ensino com base na demanda e capacidade atual.
                        1. **Edite os dados, se necessário:** Caso deseje personalizar os cenários, você pode editar os valores das células verdes na tabela, como número de matrículas, percentual de alunos em período integral e noturno, capacidade máxima por sala, entre outros. As células azuis não são editáveis. 
                        1. **Redefina os valores:** Se precisar voltar aos valores originais, clique no botão "Resetar Tabela" para restaurar os dados iniciais.
                        1. **Selecione os níveis de ensino:** No menu suspenso "Selecione os níveis de ensino para analisar", escolha os níveis de ensino que deseja exibir no mapa.
                        1. **Ajuste o tamanho dos hexágonos:** Use o controle deslizante "Tamanho do Hexágono" para ajustar o nível de detalhe da análise no mapa. Hexágonos menores mostram mais detalhes; hexágonos maiores simplificam a visualização.
                        1. **Visualize o mapa:** O "Mapa de Salas Necessárias", com hexágonos, exibirá as áreas do município onde há maior necessidade de salas de aula, com base nas variáveis selecionadas e no nível de detalhe configurado.
                        
                        **Divirta-se explorando o painel e planeje de forma eficiente a expansão da infraestrutura educacional!**

                        **Revise o método de cálculo no [link]([TODO: Add link to PDF on github])**
                    '''),
                    id="alert-fade",
                    dismissable=True,
                    is_open=True,
                    color="primary",
                    # Add a bottom margin
                    style={"margin-bottom": "20px"},
                ),
            ]
        )
    ]
)

app_control_panel = [
    html.Br(),
    # State and municipality dropdowns
    dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Dropdown(
                            id="state-dropdown",
                            options=[
                                {"label": "Pará", "value": "PA"},
                                {"label": "Acre", "value": "AC"},
                                {"label": "Amazonas", "value": "AM"},
                                # TODO: Add more options for other states
                            ],
                            value="PA",
                            disabled=True,
                            style={"margin-bottom": "20px"},
                        ),
                        dcc.Dropdown(
                            id="municipality-dropdown",
                            options=[
                                {"label": muni, "value": muni}
                                for muni in para_muni["name_muni"].unique()
                            ],
                            value=INITIAL_MUNICIPALITY,
                            placeholder="Selecione um município",
                        ),
                    ],
                    width=12,
                ),
            ],
            style={"margin-bottom": "20px"},
        ),
    # Editable Table with the calculated values
    dbc.Row(
        [
            dbc.Col(
                [
                    dcc.Loading(
                        dash_table.DataTable(
                            id="computed-table",
                            columns=[
                                {"name": i, "id": i, "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)} 
                                if i != "index" else {"name": "", "id": i} 
                                for i in initial_table_data.columns
                            ],
                            tooltip_data=initial_tooltips,
                            data=[
                                {**row, **{'editable': index in calculated_rows}} for index, row in enumerate(initial_table_data.to_dict("records"))
                            ],
                            editable=True,
                            fixed_columns={'headers': True, 'data': 1},
                            # css=[{'selector': 'table', 'rule': 'table-layout: fixed'}],
                            # style_cell={
                            #     'width': '{}%'.format(len(initial_table_data.columns)),
                            #     'textOverflow': 'ellipsis',
                            #     'overflow': 'hidden'
                            # },
                            style_table={
                                'overflowX': 'auto', 
                                'minWidth': '100%'
                            },
                            style_data={
                                # 'whiteSpace': 'normal',
                                # 'height': 'auto',
                                'color': 'black',
                                'backgroundColor': 'white',
                            },
                            style_header={
                                'backgroundColor': 'rgb(210, 210, 210)',
                                'color': 'black',
                                'fontWeight': 'bold',
                            },
                            style_cell_conditional=[
                                {'if': {'column_id': 'index'}, 'width': '10%'},
                            ] + [
                                {'if': {'column_id': col}, 'width': '8%'} 
                                for col in initial_table_data.columns if col != "index"
                            ],
                            style_data_conditional=[
                                {
                                    'if': {'row_index': user_defined_rows, 'column_type': 'numeric'},
                                    'backgroundColor': 'rgb(230, 255, 230)',
                                },
                                {
                                    'if': {'row_index': calculated_rows, 'column_type': 'numeric'},
                                    'backgroundColor': 'rgb(230, 230, 255)',
                                    'fontWeight': 'bold'
                                }
                            ],
                        ),
                        type="circle",
                    ),
                    dbc.Button("Resetar Tabela", id="reset-table-button", color="primary", className="mr-1 mt-2 align-self-end"),
                ],
                width=12,
                style={"margin-bottom": "20px"},
            ),
        ]
    ),    
    # Report settings
    dbc.Row(
        [
            dbc.Col(
                [
                    html.H2("Configurações"),
                    html.Hr(),
                    html.H3("Selecione os níveis de ensino para analisar"),
                    dcc.Markdown(("- Selecione os níveis de ensino que deseja visualizar no mapa.\n"
                                  "- Os hexágonos no mapa mostrarão o número de **novas** salas necessárias para todos os níveis de ensino selecionados.\n"
                                  "- O relatório será gerado com base nos níveis de ensino selecionados.")),
                    dcc.Dropdown(
                        id="education-level-dropdown",
                        options=[
                            {"label": education_levels_labels[level], "value": f"QT_SALAS_NECESARIAS_EXTRA_{level}"}
                            for level in education_levels
                        ],
                        value=f"QT_SALAS_NECESARIAS_EXTRA_{education_levels[0]}",
                        multi=True,
                        placeholder="Select variables to visualize",
                    ),
                    # Add an slider to change the hexagon size
                    html.Hr(),
                    html.H3("Tamanho do Hexágono"),
                    dcc.Markdown("""
                    O tamanho do hexágono determina o nível de detalhe na análise:  
                    
                    - Hexágonos maiores (~252,9 km²) oferecem uma visão ampla, ideal para tendências em nível de cidade;
                    - Hexágonos médios (~36,13 km² a ~5,16 km²) são adequados para análises em nível de bairro;
                    - Hexágonos menores (~0,74 km²) proporcionam detalhes precisos e localizados para identificar áreas críticas. 
                    
                    Escolha hexágonos maiores para tendências macro e menores para análises detalhadas e específicas.
                    """),
                    dcc.Slider(
                        id="hexagon-size-slider",
                        min=5,
                        max=8,
                        step=1,
                        value=7,
                        marks=slider_marks,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Hr(),

                    # dcc.Store(id='map-data-store'),

                    # html.H3("Mapa de Salas Necessárias"),
                    # dcc.Loading(
                    #     dcc.Graph(id="map-graph"),
                    #     type="circle",
                    # ),
                    # html.Hr(),
                    # html.H3("Configurações do Relatório"),



                    # dcc.Markdown((
                    #     "Para identificar onde expandir ou construir novas escolas, ajuste o intervalo de análise para o **número de novas salas necessárias**.\n"
                    #     "Dessa maneira o relatório irá **filtrar as áreas no mapa** com base o número de novas salas selecionado.\n"
                    #     "#### Ajuste o intervalo de análise:\n"
                    #     "- **Controle Deslizante:** Arraste as extremidades do controle deslizante abaixo do gráfico para definir o intervalo desejado de novas salas dos hexágonos a serem destacados.\n"
                    #     "- **Barras:** Mostram a quantidade de hexágonos que precisam de **novas** salas dentro do intervalo selecionado."
                    # )),


                    # dcc.Graph(
                    #     id="histogram-graph", 
                    #     style={"width": "100%", "margin-bottom": "0px"},
                    # ),
                    # html.Div(
                    #     dcc.RangeSlider(
                    #         id="value-range-slider",
                    #         min=0,  # Adjust based on your data
                    #         max=100,  # Adjust based on your data
                    #         step=1,
                    #         value=[10, 25],  # Initial range
                    #             # marks={
                    #             #     i: {
                    #             #         "label": str(i), 
                    #             #         "style": {"font-size": "1.2em"},
                    #             #     } for i in range(0, 101, 5)
                    #             # },
                    #             tooltip={"placement": "bottom"},
                    #     ),
                    #     style={"width": "100%", "margin-top": "0px", "margin-left": "10px", "margin-right": "0px"}
                    # ),
                    # html.Div(id="hexagons-in-selected-range"),
                    # dcc.Markdown((
                    #     "- Este mapa mostra os hexágonos que têm um número de **novas** salas necessárias dentro do intervalo selecionado.\n"
                    #     "- Os hexágonos são filtrados com base no intervalo selecionado ao lado."
                    # )),
                    # dcc.Graph(id="filtered-map-graph"),

                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    # Add a histogram and a range slider
                                    dcc.Markdown((
                                        "#### Ajuste o intervalo de análise:\n"
                                        "- **Controle Deslizante:** Arraste as extremidades do controle deslizante abaixo do gráfico para definir o intervalo desejado de novas salas dos hexágonos a serem destacados.\n"
                                        "- **Barras:** Mostram a quantidade de hexágonos que precisam de **novas** salas dentro do intervalo selecionado."
                                    )),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dcc.Markdown(("#### Mapa de Hexágonos Selecionados:\n"
                                                    "- Este mapa mostra os hexágonos que têm um número de **novas** salas necessárias dentro do intervalo selecionado.\n"
                                                    "- Os hexágonos são filtrados com base no intervalo selecionado ao lado.")),
                                ],
                                width=6,
                            )
                        ]
                    ),
                    dbc.Row([
                        dbc.Col(
                            html.Div([
                                dcc.Graph(id="histogram-graph", style={"width": "100%", "margin-bottom": "0px"}),
                                html.Div(dcc.RangeSlider(
                                    id="value-range-slider",
                                    min=0,  # Adjust based on your data
                                    max=100,  # Adjust based on your data
                                    step=1,
                                    value=[10, 25],  # Initial range
                                    # marks={
                                    #     i: {
                                    #         "label": str(i), 
                                    #         "style": {"font-size": "1.2em"},
                                    #     } for i in range(0, 101, 5)
                                    # },
                                    tooltip={"placement": "bottom"},
                                ),
                                style={"width": "100%", "margin-top": "0px", "margin-left": "10px", "margin-right": "0px"}
                                ),
                                dcc.Markdown(
                                    "Número de Novas Salas Necessárias", 
                                    # Center the text horizontally
                                    style={"width": "100%", "display": "inline-block", "text-align": "center"})
                            ], style={"width": "100%", "display": "inline-block"}
                        ), width=6),
                        dbc.Col(dcc.Graph(id="filtered-map-graph"), width=6),
                        html.Div(id="hexagons-in-selected-range"),
                    ]),

                    html.Hr(),
                    # Center the button
                    html.Div(
                        dbc.Button(
                            "Gerar Relatório",
                            id="create-report-button", 
                            color="primary", 
                            className="mr-1 mt-2 align-self-center justify-content-center"
                        ),
                        className="d-flex justify-content-center"
                    ),
                    html.Br(),
                ], 
                width=12)
            ]
        ),
]

# app_report = [
#     dcc.Store(id='report-page-store'),
#     dbc.Row(
#         [
#             dbc.Col(
#                 [
#                     html.Br(),
#                     html.Div(id="report-container"),
#                     html.Br(),
#                     dcc.Loading(html.Div(id="report-body-container")),
#                     html.Br(),
#                     html.Div(id="report-footer-container", children=[
#                         dbc.Pagination(id="report-pagination", max_value=1),
#                         html.Br(),
#                         dbc.Button("Imprimir Relatório", id="print-pdf-button", color="primary", className="mr-1 mt-2 align-self-center justify-content-center"),
#                     ]),
#                     html.Br(),
#                 ],
#                 width=12,
#             ),
#         ]
#     )
# ]

app_report = [
    dbc.Row(
        [
            dbc.Col(
                [
                    # html.H2("Relatório de Análise"),
                    html.Br(),
                    html.Div(id="report-container"),
                    html.Br(),
                    html.Div(id="dummy-body-container"),
                ],
                width=12,
            ),
        ]
    )
]






tabs = dbc.Tabs(
    [
        dbc.Tab(app_control_panel, label="Configurações", tab_id="tab-1"),
        dbc.Tab(app_report, label="Relatório", tab_id="tab-2"),
    ],
    id="tabs",
    active_tab="tab-1",
)

app.layout = dbc.Container([
        dcc.Location(id='url', refresh=False),
        app_header,
        tabs
])

# Callbacks
@app.callback(
    Output("computed-table", "data", allow_duplicate=True), 
    Output("computed-table", "tooltip_data"),
    Input("municipality-dropdown", "value"),
    prevent_initial_call='initial_duplicate'
)
def calculate_table(selected_municipality):
    print("--------------------------------")
    print("calculate_table callback called")
    print("selected_municipality", selected_municipality)
    print("--------------------------------")

    table_data = calculate_table_data(selected_municipality)
    tooltips = calculate_tooltips(table_data)
    
    return table_data.to_dict("records"), tooltips

@app.callback(
    Output('computed-table', 'data', allow_duplicate=True),
    Input('computed-table', 'data_timestamp'),
    State('computed-table', 'data'),
    prevent_initial_call=True,
    )
def update_columns(timestamp, rows):
    
    main_table = pd.DataFrame(rows)
    main_table.set_index(main_table.columns[0], inplace=True)
     
    main_table = main_table[[education_levels_short_labels[level] for level in education_levels]].astype(float)

    # Calculate the number of students in public schools using:
    # - Estimated population
    # - Percentage of population not in the basic education system
    # - Percentage of students in private schools
    # Formula: Total students in public = Estimated population * (1 - % pop not in education - % students in private)
    main_table.loc["Número Total de Alunos em Escolas Publicas"] = main_table.loc["População Estimada"] * \
        (1 - main_table.loc["Porcentagem da População fora da Escola (%)"] / 100
           - main_table.loc["Porcentagem de Alunos em Escolas Privadas (%)"] / 100)
    
    # Calculate the number of 'seats' needed in each level using:
    # - Total number of students in public schools
    # - Percentage of students in integral time
    # - Percentage of students in nocturnal time
    # Formula: Total number of seats = Total number of students * (1 + % students in integral time) * (1 - % students in nocturnal time)
    main_table.loc["Número Total de Vagas Necessárias"] = main_table.loc["Número Total de Alunos em Escolas Publicas"] * \
        (1 + main_table.loc["Porcentagem de Alunos em Tempo Integral (%)"] / 100) * \
        (1 - main_table.loc["Porcentagem de Alunos em Período Noturno (%)"] / 100)

    # Calculate the number of classrooms needed based on the user defined number of chairs per classroom

    # Number of classrooms needed in total
    main_table.loc["Número de Salas Necessárias"] = np.ceil(main_table.loc["Número Total de Vagas Necessárias"] / main_table.loc["Número Total de Vagas por Sala"])

    # Number of classrooms needed in each level
    main_table.loc["Número de Novas Salas Necessárias"] = np.ceil(
        np.maximum(main_table.loc["Número de Salas Necessárias"] - main_table.loc["Número de Salas Existentes"], 0)
    )

    main_table.reset_index(inplace=True)

    return main_table.to_dict("records")

# Reset the table to the initial values
@app.callback(
    Output("computed-table", "data", allow_duplicate=True),
    Input("reset-table-button", "n_clicks"),
    State("municipality-dropdown", "value"),
    prevent_initial_call=True,
)
def reset_table(n_clicks, selected_municipality):
    return calculate_table_data(selected_municipality).to_dict("records")


# Constraint hexagon res to be 5 if no municipality is selected
@app.callback(
    Output("hexagon-size-slider", "value"),
    Input("municipality-dropdown", "value"),
    State("hexagon-size-slider", "value")
)
def constraint_hexagon_res(selected_municipality, hex_res):
    return MIN_HEX_SIZE_AT_STATE_LEVEL if not selected_municipality else hex_res

# @app.callback(
#     [
#         Output("map-graph", "figure"), 
#         Output("map-data-store", "data")
#     ], 
#     [
#         Input("municipality-dropdown", "value"),
#         Input("education-level-dropdown", "value"),
#         Input('hexagon-size-slider', 'value'),
#         Input('computed-table', 'data_timestamp'),
#         Input("value-range-slider", "value"),
#         State('computed-table', 'data')
#     ]
# )
# def update_map(selected_municipality, selected_variables, hex_size, timestamp, value_range, rows):
#     print("CALLBACK TRIGGERED")
#     print("--------------------------------")
#     print("selected_municipality", selected_municipality)
#     print("hex_size", hex_size)
#     print("--------------------------------")
#     if not selected_municipality and hex_size > MIN_HEX_SIZE_AT_STATE_LEVEL:
#         # If no municipality is selected and the hexagon resolution is less than 5, don't update the map
#         # raise PreventUpdate
#         hex_size = MIN_HEX_SIZE_AT_STATE_LEVEL
        
#     # Process the data 
#     print("update_map > before calculate_extra_salas > rows", rows)
#     print("update_map > before calculate_extra_salas > hex_gdf.shape", hex_gdf.shape)
    
#     muni_hexagons = calculate_extra_salas(selected_municipality, selected_variables, rows, hex_size)
#     print("update_map > calculate_extra_salas done > muni_hexagons.shape", muni_hexagons.shape)

#     # Create the map figure
#     muni_hexagons["hover_name"] = "Novas Salas Necessárias" # Hover title
#     map_figure = px.choropleth_map(
#         muni_hexagons,
#         geojson=muni_hexagons.geometry.__geo_interface__,
#         locations=muni_hexagons.index,
#         color="SalasNecessariasAcum",
#         color_continuous_scale="RdYlGn_r",
#         opacity=0.5,
#         hover_name="hover_name",
#         hover_data={f"QT_SALAS_NECESARIAS_EXTRA_{level}": True for level in education_levels} | {"SalasNecessariasAcum": False},
#         mapbox_style="carto-positron",
#         labels={f"QT_SALAS_NECESARIAS_EXTRA_{level}": education_levels_labels[level] for level in education_levels} | {"SalasNecessariasAcum": "Novas Salas Necessárias"},
#         zoom=8 if selected_municipality else 4,
#         center={
#             "lat": muni_hexagons.geometry.centroid.y.mean(),
#             "lon": muni_hexagons.geometry.centroid.x.mean(),
#         },
#     )
#     # Set makerlinewidth to 0 to remove the white border around the hexagons
#     map_figure.update_traces(marker=dict(line_width=0))

#     return map_figure, muni_hexagons.drop(columns=["geometry"]).to_json(date_format='iso', orient='split')

# @app.callback(
#     [
#         Output("histogram-graph", "figure"), 
#         Output("value-range-slider", "min"), 
#         Output("value-range-slider", "max"),
#         Output("value-range-slider", "marks"),
#     ],
#     [
#         Input("map-data-store", "data"),
#         Input("value-range-slider", "value"),
#         State("municipality-dropdown", "value"),
#         Input("hexagon-size-slider", "value"),
#     ],
#     prevent_initial_call=True
# )
# def update_histogram_and_slider(jsonified_data, value_range, selected_municipality, hex_size):
#     if not selected_municipality and hex_size > MIN_HEX_SIZE_AT_STATE_LEVEL:
#         # raise PreventUpdate
#         hex_size = MIN_HEX_SIZE_AT_STATE_LEVEL
    
#     if jsonified_data is None:
#         raise PreventUpdate
    
#     # Load the DataFrame from JSON
#     df = pd.read_json(jsonified_data, orient='split')

#     # Update the range slider min and max based on the DataFrame
#     min_value = 0 # df["SalasNecessariasAcum"].min()
#     max_value = df["SalasNecessariasAcum"].max()
#     print("--------------------------------")
#     print("SalasNecessariasAcum MAX VALUE ", max_value)
#     print("--------------------------------")
#     print("df SHAPE", df.shape)
#     print("--------------------------------")
#     print("df.info()", df.info())
#     print("--------------------------------")
#     print('df["SalasNecessariasAcum"].describe()', df["SalasNecessariasAcum"].describe())
#     print("--------------------------------")


#     marks_step = max_value // 10 if max_value > 10 else 1
#     marks = {
#         i: {
#             "label": str(i), 
#             "style": {"font-size": "1.2em"},
#         } for i in range(0, max_value + 1, marks_step)
#     }

#     # Create the histogram figure
#     print("DF shape", df.shape)
#     print("DF", df)
#     histogram_figure = px.histogram(    
#         df,
#         x="SalasNecessariasAcum",
#         nbins=50,
#         title=None,
#         # labels={"SalasNecessariasAcum": "Novas Salas Necessárias", "count": "Número de Hexágonos"},
#         labels={"count": "Número de Hexágonos"},
#         # Set opacity to 50%
#         opacity=0.5,
#     )
#     print("RANGE", value_range)
#     print("DF shape", df[df["SalasNecessariasAcum"].between(value_range[0], value_range[1])].shape)
#     highlighted_histogram_figure = px.histogram(    
#         df[df["SalasNecessariasAcum"].between(value_range[0], value_range[1])],
#         x="SalasNecessariasAcum",
#         nbins=50,
#         # title="Histograma de Salas Necessárias",
#         # labels={"SalasNecessariasAcum": "Salas Necessárias Extra"},
#         # Set opacity to 50%
#         # opacity=0.5,
#     )

#     # Add a trace of a histogram to show the selected range
#     histogram_figure.add_trace(
#         highlighted_histogram_figure.data[0]
#     )
#     # The histogram should be on top of the original histogram not stacked
#     histogram_figure.update_layout(
#         barmode='overlay',
#         margin=dict(l=0, r=15, b=0, t=0),
#         xaxis=dict(range=[min_value, max_value])
#     )

#     # Turn of the axis titles
#     histogram_figure.update_yaxes(title="Número de Hexágonos", showticklabels=True)                                         
#     histogram_figure.update_xaxes(
#         # title="Novas Salas Necessárias", 
#         title=None,
#         showticklabels=False,
#         tickmode="array",
#         tickvals=list(marks.keys()),
#     )
    
#     return histogram_figure, min_value, max_value, marks

@app.callback(
    [
        Output("filtered-map-graph", "figure"),
        Output("histogram-graph", "figure"), 
        Output("value-range-slider", "min"), 
        Output("value-range-slider", "max"),
        Output("value-range-slider", "marks"),
        Output("hexagons-in-selected-range", "children"),
    ],
    [
        State("municipality-dropdown", "value"),
        Input('computed-table', 'data'),
        Input("education-level-dropdown", "value"),
        Input("hexagon-size-slider", "value"),
        Input("value-range-slider", "value"),
    ],
    # prevent_initial_call=True
)
def update_filtered_map(
    selected_municipality,
    computed_table_data,
    selected_education_levels,
    hex_size, 
    value_range, 
):
    if not selected_municipality and hex_size > MIN_HEX_SIZE_AT_STATE_LEVEL:
        # If no municipality is selected and the hexagon resolution is less than 5, don't update the map
        raise PreventUpdate
        # hex_size = MIN_HEX_SIZE_AT_STATE_LEVEL

    print("Process data ...", end="")
        
    # Process the data 
    print("update_map > before calculate_extra_salas > computed_table_data", computed_table_data)
    print("update_map > before calculate_extra_salas > hex_gdf.shape", hex_gdf.shape)
    selected_hexagons = calculate_extra_salas(
        selected_municipality, 
        selected_education_levels, 
        computed_table_data, 
        hex_size
    )
    print("update_map > calculate_extra_salas done > selected_hexagons.shape", selected_hexagons.shape)
    print("type(selected_hexagons)", type(selected_hexagons))

    print("Done Process data")

    ### HISTOGRAM #########################################################

    print("Process histogram ...", end="")

    # Update the range slider min and max based on the selected hexagons
    min_value = 0 # df["SalasNecessariasAcum"].min()
    max_value = selected_hexagons["SalasNecessariasAcum"].max()
    # print("--------------------------------")
    # print("SalasNecessariasAcum MAX VALUE ", max_value)
    # print("--------------------------------")
    # print("selected_hexagons SHAPE", selected_hexagons.shape)
    # print("--------------------------------")
    # print("selected_hexagons.info()", selected_hexagons.info())
    # print("--------------------------------")
    # print('selected_hexagons["SalasNecessariasAcum"].describe()', selected_hexagons["SalasNecessariasAcum"].describe())
    # print("--------------------------------")

    marks_step = max_value // 10 if max_value > 10 else 1
    marks = {
        i: {
            "label": str(i), 
            "style": {"font-size": "1.2em"},
        } for i in range(0, int(max_value) + 1, int(marks_step))
    }

    # Create the histogram figure
    print("selected_hexagons SHAPE", selected_hexagons.shape)
    print("selected_hexagons", selected_hexagons)
    histogram_figure = px.histogram(    
        selected_hexagons,
        x="SalasNecessariasAcum",
        nbins=50,
        title=None,
        # labels={"SalasNecessariasAcum": "Novas Salas Necessárias", "count": "Número de Hexágonos"},
        labels={"count": "Número de Hexágonos"},
        # Set opacity to 50%
        opacity=0.5,
    )
    highlighted_histogram_figure = px.histogram(    
        selected_hexagons[selected_hexagons["SalasNecessariasAcum"].between(*value_range)],
        x="SalasNecessariasAcum",
        nbins=50,
    )

    # Add a trace of a histogram to show the selected range
    histogram_figure.add_trace(
        highlighted_histogram_figure.data[0]
    )
    # The histogram should be on top of the original histogram not stacked
    histogram_figure.update_layout(
        barmode='overlay',
        margin=dict(l=0, r=15, b=0, t=0),
        xaxis=dict(range=[min_value, max_value])
    )

    # Turn of the axis titles
    histogram_figure.update_yaxes(title="Número de Hexágonos", showticklabels=True)                                         
    histogram_figure.update_xaxes(
        # title="Novas Salas Necessárias", 
        title=None,
        showticklabels=False,
        tickmode="array",
        tickvals=list(marks.keys()),
    )

    print("Done Process histogram")

    ### MAP #################################################################

    print("Process map ...", end="")

    # Filter the DataFrame based on the range slider values
    if value_range is not None:
        print(f"Filtering the DataFrame based on the range slider values: {value_range}")
        selected_hexagons_filtered = selected_hexagons[selected_hexagons["SalasNecessariasAcum"].between(*value_range)]
    else:
        selected_hexagons_filtered = selected_hexagons

    # Create the map figure
    print("##### hex_size:", hex_size)
    print("##### selected_hexagons.columns:", selected_hexagons.columns)
    selected_hexagons_filtered["hover_name"] = "Novas Salas Necessárias" # Hover title
    filtered_map_figure = px.choropleth_map(
        selected_hexagons_filtered,
        geojson=selected_hexagons_filtered.geometry.__geo_interface__,
        locations=selected_hexagons_filtered.index,
        color="SalasNecessariasAcum",
        color_continuous_scale="RdYlGn_r",
        range_color=[0, max_value],
        opacity=0.5,
        hover_name="hover_name",
        hover_data={f"QT_SALAS_NECESARIAS_EXTRA_{level}": True for level in education_levels} | {"SalasNecessariasAcum": False, f"hex_{hex_size}": False},
        map_style="carto-positron",
        labels={f"QT_SALAS_NECESARIAS_EXTRA_{level}": education_levels_labels[level] for level in education_levels} | {"SalasNecessariasAcum": "Novas Salas Necessárias"},
        zoom=10 if selected_municipality else 6,
        center={
            "lat": selected_hexagons.geometry.centroid.y.mean(),
            "lon": selected_hexagons.geometry.centroid.x.mean(),
        }
    )
    # Set makerlinewidth to 0 to remove the white border around the hexagons
    filtered_map_figure.update_traces(marker=dict(line_width=0))

    # Remove margins
    filtered_map_figure.update_layout(margin=dict(l=0, r=0, t=0, b=0))

    print("Done Process map")

    # Show number of hexagons in the selected range
    hexagons_in_selected_range = dcc.Markdown(f"#### {len(selected_hexagons_filtered)} Hexágonos selecionados precisam de entre {value_range[0]} e {value_range[1]} novas salas")

    return filtered_map_figure, histogram_figure, int(min_value), int(max_value), marks, hexagons_in_selected_range

# callback for showing a spinner within dbc.Button()
app.clientside_callback(
    """
    function (click) {
        return [""" + json.dumps(dbc.Spinner(size='sm').to_plotly_json()) + """, " Gerando Relatório ..."]
    }
    """,
    Output("create-report-button", "children"),
    Input("create-report-button", "n_clicks"),
    prevent_initial_call=True
)

@app.callback(
    [
        Output("create-report-button", "children", allow_duplicate=True),
        Output("report-container", "children"),
        Output("tabs", "active_tab"),
    ],
    [
        Input("create-report-button", "n_clicks"),
        State("hexagon-size-slider", "value"),
        State("education-level-dropdown", "value"),
        State('computed-table', 'data'),
        State('computed-table', 'tooltip_data'),
        # State("map-data-store", "data"), 
        State("filtered-map-graph", "figure"),
        State("value-range-slider", "value"),
        # State("map-graph", "figure"),
        State("municipality-dropdown", "value"),
        State("state-dropdown", "value")
    ],
    prevent_initial_call=True
)
def create_report(
        n_clicks, 
        hex_size, 
        selected_education_levels, 
        computed_table_data, 
        table_tooltips, 
        figure_data, 
        value_range, 
        # map_figure, 
        selected_municipality, 
        selected_state
    ):
    if n_clicks is None:
        raise PreventUpdate

    if selected_municipality is None and hex_size > MIN_HEX_SIZE_AT_STATE_LEVEL:
        raise PreventUpdate

    if figure_data is None:
        raise PreventUpdate    
    
    if isinstance(selected_education_levels, str):
        selected_education_levels = [selected_education_levels]

    # Load the DataFrame from the figure data
    cleaned_features = [{
        "type": "Feature",
        "geometry": feature['geometry'],
        "properties": {}
    } for feature in figure_data['data'][0]['geojson']['features']]
    filtered_df = gpd.GeoDataFrame.from_features(cleaned_features)

    # # Parse the index
    # raw_index = figure_data['data'][0]['locations']
    # if isinstance(raw_index, list):
    #     index = pd.Index(raw_index)
    # elif isinstance(raw_index, dict):
    #     index = pd.Index(raw_index['_inputArray'].values())
    # else:
    #     print("ERROR: raw_index type not recognized")
    #     index = pd.Index(range(len(filtered_df)))
    # print("filtered_df", filtered_df)
    # print("index", index)
    # filtered_df.index = index

    columns = [*[f"QT_SALAS_NECESARIAS_EXTRA_{level}"  for level in education_levels], "SalasNecessariasAcum", f"hex_{hex_size}"]
    filtered_df[columns] = figure_data['data'][0]['customdata']

    # INPUT TABLE
    input_table = dash_table.DataTable(
        id="report-table",
        columns=[
            {
                "name": i, 
                "id": i, 
                "type": "numeric", 
                "format": Format(precision=0, scheme=Scheme.fixed)
            } if i != "index" else {
                "name": i, 
                "id": i
            } for i in initial_table_data.columns
        ],
        tooltip_data=table_tooltips,
        data=computed_table_data,
        editable=False, # Disable editing in the report
        style_data={
            'color': 'black',
            'backgroundColor': 'white',
        },
        style_header={
            'backgroundColor': 'rgb(210, 210, 210)',
            'color': 'black',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': user_defined_rows, 'column_type': 'numeric'},
                'backgroundColor': 'rgb(230, 255, 230)',
            },
            {
                'if': {'row_index': calculated_rows, 'column_type': 'numeric'},
                'backgroundColor': 'rgb(230, 230, 255)',
                'fontWeight': 'bold'
            }
        ],
    )

    # Create a data table with the selected hexagons
    def generate_hexagon_table(df):

        # Columns

        # Id do Hexagono
        # Endereço / localização
        # Numero de salas hoje (total)
        # # salas necessária (total)
        # # salas necessária (Creche)
        # # salas necessária (Pré-escola)
        # # salas necessária (Fundamental)
        # # salas necessária (Ensino Médio)

        # Use h3 library to get a pair of lat, lon coordinates using the hexagon index
        hexagon_latlon_coords = df[f"hex_{hex_size}"].apply(lambda x: h3.h3_to_geo(x))
        # Use requests library to query the Nominatim API to get the address based on the lat, lon coordinates
        import requests
        
        def nominatim_reverse_geocode(coordinate):
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                "format": "json",
                "lat": coordinate[0],
                "lon": coordinate[1],
                # Pass the user agent to avoid the 429 error
                "email": "claudio@autodash.org"
            }
            response = requests.get(url, params=params)
            # Sleep for 1 second to avoid the rate limit
            time.sleep(0.1)
            return response.json()

        # Get the address for each hexagon
        hexagon_addresses = hexagon_latlon_coords.apply(nominatim_reverse_geocode)
        # print("HEXAGON ADDREESS EXAMPLE", hexagon_addresses.iloc[0])
        # "road": "Travessa S 1",
        # "suburb": "Campina de Icoaraci",
        # "city_district": "Icoaraci",
        # "city": "Belém",
        # "municipality": "Região Geográfica Imediata de Belém",
        # "state_district": "Região Geográfica Intermediária de Belém",
        # "state": "Pará",

        def build_short_address(address):
            road = address.get("road", "")
            suburb = address.get("suburb", "")

            if road and suburb:
                return f"{road}, {suburb}"
            elif road:
                return road
            elif suburb:
                return suburb
            else:
                return "Endereço não encontrado"
            
        def build_city_state(address):
            city = address.get("city", "")
            state = address.get("state", "")

            if city and state:
                return f"{city}, {state}"
            elif city:
                return city
            elif state:
                return state
            else:
                return "Não encontrados"

        # Extract the address from the JSON response
        hexagon_short_address = hexagon_addresses.apply(lambda x: build_short_address(x["address"]))
        hexagon_city_state = hexagon_addresses.apply(lambda x: build_city_state(x["address"]))

        # Add the address column to the DataFrame
        df["short_address"] = hexagon_short_address
        df["city_state"] = hexagon_city_state

        # Calculate the total number of classrooms needed
        df["QT_SALAS_NECESARIAS_EXTRA_TOTAL"] = df[[f"QT_SALAS_NECESARIAS_EXTRA_{level}" for level in education_levels]].sum(axis=1)
        # Show the hexagons with the highest number of classrooms needed first
        df = df.sort_values("QT_SALAS_NECESARIAS_EXTRA_TOTAL", ascending=False)

        # Create a numerical index for the hexagons (1, 2, 3, ...)
        df["#"] = list(range(1, len(df) + 1))

        # Replace the hexagon column names
        # Extend a dict with another dict: {**dict1, **dict2}
        column_labels = {**COLUMN_LABELS, **{f"hex_{hex_size}": ["    ", "Id do Hexágono"]}}

        return dash_table.DataTable(
            id="hexagon-table",
            columns=[
                {"name": label, "id": col} for col, label in column_labels.items()
            ],
            data=df[column_labels.keys()].to_dict("records"),
            merge_duplicate_headers=True,
            fixed_columns={'headers': True, 'data': 1},
            style_table={'overflowX': 'auto', 'minWidth': '100%'},
            style_cell={
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "maxWidth": 0,
            },
            style_cell_conditional=[
                {'if': {'column_id': '#'},
                'width': '3%',
                'textAlign': 'center'},
                {'if': {'column_id': 'short_address'},
                'width': '30%',
                'textAlign': 'left'},
                {'if': {'column_id': 'city_state'},
                'width': '10%',
                'textAlign': 'left'}
            ],
            tooltip_data=[
                {
                    column: {"value": str(value), "type": "markdown"}
                    for column, value in row.items()
                }
                for row in df.to_dict("records")
            ],
            tooltip_duration=None,
            style_data={
                "color": "black",
                "backgroundColor": "white",
            },
            style_header={
                "backgroundColor": "rgb(210, 210, 210)",
                "color": "black",
                "fontWeight": "bold",
                "textAlign": "center",
                # LINES BLACK
                "border": "1px solid black"
            },
        )
    
    # Create a maps with the selected hexagons
    def generate_hexagon_maps(df, hex_size, selected_education_levels):     
        # Iterate over the selected hexagons
        hexagon_detail_list = []

        print("df cols", df.columns)

        df = df.sort_values("QT_SALAS_NECESARIAS_EXTRA_TOTAL", ascending=False)
        # Create a numerical index for the hexagons (1, 2, 3, ...)
        df["#"] = list(range(1, len(df) + 1))

        for index, row in df.iterrows():

            # Create a map for each hexagon
            current_hexagon = df.loc[[index]]
            xmin, ymin, xmax, ymax = current_hexagon.total_bounds
            max_bound = max(abs(xmax - xmin), abs(ymax - ymin)) * 111
            zoom = 13.5 - np.log(max_bound)

            # Process polygon to plot only the exterior lines
            import shapely
            current_hexagon.geometry = current_hexagon.geometry.exterior
            lats = []
            lons = []
            for feature in current_hexagon.geometry.values:
                if isinstance(feature, shapely.geometry.linestring.LineString):
                    linestrings = [feature]
                elif isinstance(feature, shapely.geometry.multilinestring.MultiLineString):
                    linestrings = feature.geoms
                else:
                    continue
                for linestring in linestrings:
                    x, y = linestring.xy
                    lats = np.append(lats, y)
                    lons = np.append(lons, x)
                    # lats = np.append(lats, None)
                    # lons = np.append(lons, None)

            print("positions", list(zip(lats, lons)))

            # hexagon_map = px.line_map(
            #     lat=lats,
            #     lon=lons,
            #     # color=["red"] * len(lats),
            #     color_discrete_sequence=["red"],
            #     # mapbox_style='open-street-map',
            #     zoom=zoom,
            #     center={
            #         "lat": row.geometry.centroid.y,
            #         "lon": row.geometry.centroid.x,
            #     },
            # )
            # # Remove the legend
            # hexagon_map.update_layout(showlegend=False)

            # hexagon_map = dl.Map([
            #     dl.TileLayer(),
            #     dl.Polyline(positions=[list(zip(lats, lons))])
            # ], center=[row.geometry.centroid.x, row.geometry.centroid.y], zoom=zoom, 
            #     # style={'height': '50vh'}
            # )

            center = h3.h3_to_geo(row[f"hex_{hex_size}"])
            print("CENTER", center)

            # eventHandlers = dict(
            #     click=assign("function(e, ctx){console.log(`You clicked at ${e.latlng}.`)}"),
            # )

            hexagon_map = dl.Map([
                dl.TileLayer(
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
                    subdomains='abcd',
                    maxZoom=20,
                    minZoom=0,
                ),
                dl.Polyline(positions=list(zip(lats, lons)), color="red"),
                dl.ScaleControl(position="bottomleft")
            ], 
                center=center,
                zoom=zoom,
                 style={"height": "500px", "width": "100%"}
            )

            # Create a data table with the hexagon details
            # print("ROW INFO", row)
            row_df = row.to_frame().reset_index()
            row_df.columns = ["Variável", "Valor"]
            print("ROW DF", row_df)

            selected_columns = [f"QT_SALAS_NECESARIAS_EXTRA_{level}" for level in education_levels+["TOTAL"]] + ["short_address", "city_state"]
            filtered_row_df = row_df.loc[row_df["Variável"].isin(selected_columns)]

            column_labels = {**COLUMN_LABELS, **{f"hex_{hex_size}": ["", "Id do Hexágono"]}}
            column_labels_simplified = {key: value[1] for key, value in column_labels.items()}
            
            ordered_index = [value for key, value in column_labels_simplified.items() if key in filtered_row_df["Variável"].unique()]

            filtered_row_df["Variável"] = filtered_row_df["Variável"].map(column_labels_simplified)

            filtered_row_df = filtered_row_df.set_index("Variável")
            
            filtered_row_df = filtered_row_df.loc[ordered_index]


            print(filtered_row_df)

            location_info = dcc.Markdown(f"""                            
            ### Localização
            **Endereço**: {filtered_row_df.loc["Endereço", "Valor"]}  
            **Cidade**: {filtered_row_df.loc["Cidade", "Valor"]}
            """)

            table_rows = []
            print("filtered_row_df ocls", filtered_row_df.columns)
            for i, trow in filtered_row_df.iloc[2:].iterrows():
                # Check if the education level is in the selected levels
                if i in [COLUMN_LABELS[level][1] for level in selected_education_levels]:
                    
                    table_rows.append(html.Tr([html.Td(dbc.Badge(i, color="warning", className="me-1")), html.Td(dbc.Badge(trow.values[0], color="warning", className="me-1"))]))
                else:
                    table_rows.append(html.Tr([html.Td(i), html.Td(trow.values[0])]))

            table_body = [html.Tbody(table_rows)]

            table = dbc.Table(table_body, bordered=True)

            # Create a card with the hexagon map and the actual and necessary classrooms
            hexagon_details_card = dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            "#: ",
                            # Open the h3geo.org website with the hexagon index on a new tab https://h3geo.org/#hex={row.values[0]}
                            html.A(row["#"], href=f"https://h3geo.org/#hex={row.values[0]}", target="_blank"),
                        ]
                    ),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    # dbc.Col(dcc.Graph(figure=hexagon_map)),
                                    dbc.Col(html.Div([
                                        hexagon_map,
                                        dcc.Interval(id="resize-trigger", interval=500, n_intervals=0)  # Runs once on page load
                                        ])),
                                    dbc.Col([
                                        dbc.Row([location_info]),
                                        dbc.Row([
                                            dcc.Markdown("### Número de Novas Salas Necessárias"),
                                            table
                                        ]),
                                    ]),
                                ]
                            ),
                        ]
                    ),
                ],
                style={"margin-bottom": "20px"}
            )

            hexagon_detail_list.append(hexagon_details_card)

        return html.Div(hexagon_detail_list)
    
    # Generate report components
    if selected_municipality is None:
        regiao_selectionada_text = selected_state.upper()
    else:
        regiao_selectionada_text = f"{selected_municipality.capitalize()}, {selected_state.upper()}"

    report_components = [
        html.H3("Relatório de Demanda de Salas"),

        print("selected_education_levels", selected_education_levels),
        dcc.Markdown(f'''
        
        - **Região selecionada**: {regiao_selectionada_text}
        - **Níveis de Ensino Selecionados**: {", ".join([COLUMN_LABELS[level][1] for level in selected_education_levels])}
        - **Tamanho do hexágono selecionado**: 
            - **Área**: {H3HEX_RESOLUTIONS[hex_size]['area']} km²
            - **Descrição**: {H3HEX_RESOLUTIONS[hex_size]['analogy']}. {H3HEX_RESOLUTIONS[hex_size]['description']}
        - **Salas necessárias**:
            - **Mínimo**: {value_range[0]}
            - **Máximo**: {value_range[1]}
        
        '''),

        html.Hr(),
        html.H4("Entradas do Usuário"),
        input_table,
        html.Hr(),
        html.H4("Visão Geral do Hexágono"),
        dcc.Graph(figure=figure_data, className="mb-10"),
        html.Br(),
        html.Br(),
        html.Br(),
        html.H4("Detalhes do Hexágono"),
        html.H5("Salas Necessárias por Nível"),
        generate_hexagon_table(filtered_df),
        html.Br(),
        html.H4("Salas Necessárias por Hexágono"),
        generate_hexagon_maps(filtered_df, hex_size, selected_education_levels),
        html.Br(),
        dbc.Button("Imprimir Relatório", id="print-pdf-button", color="primary", className="mr-1 mt-2 align-self-center justify-content-center"),
    ]

    return "Gerar Relatório", report_components, "tab-2"

app.clientside_callback(
    """
    function(n_clicks) {
        
        window.print();
        
        return "Imprimir Relatório"
    }
    """,
    Output("print-pdf-button", "children"),
    Input('print-pdf-button', 'n_clicks'),
    prevent_initial_call=True
)

# Clientside callback to trigger the resize event
app.clientside_callback(
    """function(n) { if(n > 0) { setTimeout(() => window.dispatchEvent(new Event('resize')), 300); } return n; }""",
    dash.Output("resize-trigger", "n_intervals"),
    dash.Input("resize-trigger", "n_intervals")
)


if __name__ == "__main__":
    app.run(debug=True)
