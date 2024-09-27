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

# Load and preprocess the data
try:
    para_muni = gpd.read_file("../outputs/para_muni.geojson")
except Exception as e:
    para_muni = gpd.read_file("data/para_muni.geojson")

try: 
    hex_gdf = gpd.read_parquet("../outputs/180724_dashboard_hexs.parquet")
except Exception as e:
    # Downloaded from https://drive.usercontent.google.com/download?id=1U4bFDfcix7UKhCBBRQIgNFEQCFB9uG6P&export=download&confirm=t&uuid=03d5160f-48e9-42bb-be45-eed6fd03bcd3&at=AN_67v1mOk0aVdyLv31zU65ZAELh%3A1727433519136
    hex_gdf = gpd.read_parquet("data/180724_dashboard_hexs.parquet")

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
    "MED": "Médio",
    "index": "index",
}

COLUMN_LABELS = {
    "#": "#",
    "short_address": "Endereço",
    "city_state": "Cidade",
    "QT_SALAS_NECESARIAS_EXTRA_TOTAL": "Total",
    'QT_SALAS_NECESARIAS_EXTRA_INF_CRE': "Creche",
    'QT_SALAS_NECESARIAS_EXTRA_INF_PRE': "Pré-Escola",
    'QT_SALAS_NECESARIAS_EXTRA_FUND_AI': "Fund.\nAnos Iniciais",
    'QT_SALAS_NECESARIAS_EXTRA_FUND_AF': "Fund.\nAnos Finais",
    'QT_SALAS_NECESARIAS_EXTRA_MED': "Ensino Médio",
}

#  Here’s a table that combines the resolution, average hexagon area in km², a relatable analogy, and a simple comparative description:

# | **Resolution** | **Area (km²)** | **Analogy**                            | **Comparative Description**                                         |
# |----------------|----------------|----------------------------------------|---------------------------------------------------------------------|
# | 5              | 252.90         | Size of a small town                   | Covers a large area with very broad details.                        |
# | 6              | 36.13          | Size of a neighborhood                 | Covers a moderate area with general details, similar to a few city blocks. |
# | 7              | 5.16           | Size of a small city block             | Covers a smaller area with more detail, like a small community or park.     |
# | 8              | 0.74           | Size of a large shopping mall          | Covers a very specific area with high detail, suitable for local analyses.  |

# This table should help users quickly understand the implications of choosing different resolutions by relating each option to familiar concepts and providing a concise description of the coverage and detail level.

H3HEX_RESOLUTIONS = {
    5: {"area": 252.90, "analogy": "Size of a small town", "description": "Covers a large area with multiple districts."},
    6: {"area": 36.13, "analogy": "Size of a district", "description": "Covers a moderate area usually with a few neighborhoods."},
    7: {"area": 5.16, "analogy": "Size of a zone", "description": "Covers a smaller area containing one or two neighborhoods at most."},
    8: {"area": 0.74, "analogy": "Size of a neighborhood", "description": "Covers a very specific area with a few blocks, suitable for local analyses."},
}
# Slider marks with resolution, analogy, and description
slider_marks = {
    5: '~252.9 km² (Town size)',
    6: '~36.13 km² (District size)',
    7: '~5.16 km² (District Zone size)',
    8: {
        'label': '~0.74 km² (Neighborhood size)', 
        # Force the label to be in a single line
        'style': {'white-space': 'nowrap'}
    }
}


def calculate_table_data(name_muni):

    if "name_muni" in hex_gdf.columns:
        belem_hexs = hex_gdf[hex_gdf["name_muni"] == name_muni]
    else:
        PreventUpdate
        
    # Calculate defaults for the table
    main_table = []
    # total number of students on each level
    main_table.append(belem_hexs[[f'QT_MAT_{level}' for level in education_levels]].sum().values.tolist())
    # percentage of students in integral time (Tempo Integral)
    main_table.append([belem_hexs[f"QT_MAT_{level}_INT"].sum() / belem_hexs[f"QT_MAT_{level}"].sum() for level in education_levels])
    # percentage of students in nocturnal time (Tempo Noturno)
    main_table.append([
        (belem_hexs["QT_MAT_BAS_N"] * belem_hexs[f"QT_MAT_{level}_PROP"]).sum() / belem_hexs[f"QT_MAT_{level}"].sum()
        if level not in ["INF_CRE", "INF_PRE", "FUND_AI"] else 0 
        for level in education_levels 
    ])
    # total number of places available
    total_places = []
    for i, level in enumerate(education_levels):
        # total number of students * (1 + percentage of students in integral time) * (1 - percentage of students in nocturnal time
        num_cadeiras = main_table[0][i] * (1 + main_table[1][i]) * (1 - main_table[2][i])
        total_places.append(num_cadeiras)
    main_table.append(total_places)

    main_table = pd.DataFrame(main_table, columns=education_levels, index=["Total Alunos Atualmente", "Integral (%)", "Nocturno (%)", "Total de Crianças"]) 

    # Calculate the number of classrooms needed based on the user defined number of chairs per classroom

    # Number of chairs per classroom
    num_chairs = 30
    main_table.loc["Total de Crianças por Sala"] = num_chairs

    # Number of classrooms needed in total
    main_table.loc["Num. Salas Necessárias"] = np.ceil(main_table.loc["Total de Crianças"] / num_chairs)

    # Actual number of classrooms
    main_table.loc["Num. Salas Atuais"] = [np.ceil((belem_hexs["QT_SALAS_UTILIZADAS"] * belem_hexs[f"QT_MAT_{level}_PROP"]).sum()) for level in education_levels]

    # Number of classrooms needed in each level
    main_table.loc["Num. Salas Novas"] = np.ceil(
        np.maximum(main_table.loc["Num. Salas Necessárias"] - main_table.loc["Num. Salas Atuais"], 0)
    )

    main_table.reset_index(inplace=True)

    # Fix column names with education_levels_short_labels
    main_table.columns = [education_levels_short_labels[col] for col in main_table.columns]

    return main_table

def calculate_extra_salas(name_muni, selected_variables, rows, hex_res):

    # Visualize the results for the selected municipality
    muni_hexagons = hex_gdf[hex_gdf["name_muni"] == name_muni]

    # Calculate the number of classrooms needed based on the user defined variables
    main_table = pd.DataFrame(rows)
    
    # Set old columns names
    if len(main_table.columns) == 6:
        main_table.columns = ["index"] + education_levels
    if len(main_table.columns) == 7:
        main_table.columns = ["index"] + education_levels + ["editable"]

    main_table.set_index("index", inplace=True)
    main_table.loc[:, education_levels] = main_table[education_levels].astype(float).values

    print("Recalculating the number of classrooms needed based on the user defined variables on the table ... ", end="")
    for level in education_levels:
        prop_mat = muni_hexagons[f"QT_MAT_{level}"] / muni_hexagons[f"QT_MAT_{level}"].sum() # proportion of students in each hexagon
        total_qt_alumnos = prop_mat * main_table.loc["Total Alunos Atualmente", level] # number of students in each hexagon
        qt_cadeiras = total_qt_alumnos * (1 + main_table.loc["Integral (%)", level]) * (1 - main_table.loc["Nocturno (%)", level]) # number of chairs needed in each hexagon
        muni_hexagons.loc[:, f"QT_SALAS_NECESARIAS_TOTAL_{level}"] = qt_cadeiras / main_table.loc["Total de Crianças por Sala", level] # number of classrooms needed in each hexagon
        muni_hexagons.loc[:, f"QT_SALAS_ACTUALES_{level}"] = (
            muni_hexagons["QT_SALAS_UTILIZADAS"] * muni_hexagons[f"QT_MAT_{level}_PROP"]
        )
        muni_hexagons.loc[:, f"QT_SALAS_NECESARIAS_EXTRA_{level}"] = np.ceil(
            np.maximum(
                muni_hexagons[f"QT_SALAS_NECESARIAS_TOTAL_{level}"]
                - muni_hexagons[f"QT_SALAS_ACTUALES_{level}"],
                0,
            )
        )
    print("Done")

    if isinstance(selected_variables, str):
        selected_variables = [selected_variables]

    muni_hexagons.loc[:, "SalasNecessariasAcum"] = muni_hexagons[selected_variables].sum(axis=1)
    muni_hexagons = muni_hexagons.dropna(subset=["SalasNecessariasAcum"])
    muni_hexagons = muni_hexagons[muni_hexagons["SalasNecessariasAcum"] > 0]

    # Change the hexagon resolution based on the user input (hex_res)

    # Check the current resolution of the hexagons
    current_hex_res = h3.h3_get_resolution(muni_hexagons.hex.iloc[0])
    
    print(f"Current hexagon resolution: {current_hex_res}")

    if hex_res != current_hex_res:
        print(f"Rescaling the hexagons to resolution {hex_res} ... ", end="")
        muni_hexagons = up.geom.resolution_downsampling(
            muni_hexagons,
            "hex",
            hex_res,
            {f"QT_SALAS_NECESARIAS_EXTRA_{level}": "sum" for level in education_levels} | {"SalasNecessariasAcum": "sum"},
        )

    print("COLUMNS IN HEXAGON DATAFRAME", muni_hexagons.columns)
    if 'hex' in muni_hexagons.columns:
        # Replace 'hex' to f"hex_{hex_res}"
        muni_hexagons.rename(columns={"hex": f"hex_{hex_res}"}, inplace=True)

    return muni_hexagons

initial_table_data = calculate_table_data("Belém")

user_defined_rows = [0,1,2,4,6]
calculated_rows = [3,5,7]

# Valor por default en portugues es "Valor padrão"
# Create tooltips for user-defined rows
tooltips = [
    {column: {'value': f"*Valor padrão:* {row[column]}", 'type': 'markdown'} for column in initial_table_data.columns}
    if index in user_defined_rows 
    else {column: {'value': "Valor calculado", 'type': 'markdown'} for column in initial_table_data.columns}
    for index, row in initial_table_data.iterrows() 
]

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server

# Layout
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        # Title in portuguese
                        html.H1("Dashboard de Educação"),
                        dbc.Alert(
                            dcc.Markdown('''
                                Este é um painel de controle de educação que permite visualizar as salas de aula necessárias em diferentes níveis de ensino para um município selecionado. 

                                Para usar o painel, siga estas etapas:  
                                         
                                1. Selecione um estado no primeiro menu suspenso.  
                                2. Selecione um município no segundo menu suspenso.  
                                3. A tabela exibirá os dados iniciais sobre o número de salas de aula necessárias em cada nível de ensino.  
                                4. Você pode editar os valores na tabela, se desejar.  
                                5. Clique no botão "Reset Table" para redefinir a tabela para os valores iniciais.  
                                6. No "Mapa de Salas Necessárias", selecione as variáveis que deseja visualizar no menu suspenso "Select variables to visualize".  
                                7. Use o controle deslizante "Tamanho do Hexágono" para ajustar o tamanho dos hexágonos no "Mapa de Salas Necessárias".  
                                8. O "Mapa de Salas Necessárias" mostrará as salas de aula necessárias para as variáveis selecionadas no município escolhido.  

                                Divirta-se explorando o painel de controle de educação!
                            '''),
                            id="alert-fade",
                            dismissable=True,
                            is_open=True,
                            color="primary",
                            # Add a bottom margin
                            style={"margin-bottom": "20px"},
                        ),
                        dcc.Dropdown(
                            id="state-dropdown",
                            options=[
                                {"label": "Pará", "value": "PA"},
                                {"label": "Acre", "value": "AC"},
                                {"label": "Amazonas", "value": "AM"},
                                # Add more options for other states
                            ],
                            value="PA",
                            disabled=True,
                            # Add bottom margin to the dropdown
                            style={"margin-bottom": "20px"},
                        ),
                        dcc.Dropdown(
                            id="municipality-dropdown",
                            options=[
                                {"label": muni, "value": muni}
                                for muni in para_muni["name_muni"].unique()
                            ],
                            value="Belém",
                            placeholder="Selecione um município",
                        ),
                    ],
                    width=12,
                ),
            ],
            style={"margin-bottom": "20px"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dash_table.DataTable(
                            id="computed-table",
                            columns=[{"name": i, "id": i, "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)} if i != "index" else {"name": i, "id": i} for i in initial_table_data.columns],
                            tooltip_data=tooltips,
                            data=[
                                {**row, **{'editable': False}} if index in calculated_rows else {**row, **{'editable': True}}
                                for index, row in enumerate(initial_table_data.to_dict("records"))
                            ],
                            editable=True,
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
                        ),
                        # Add a button to reset the table to the initial values
                        dbc.Button("Reset Table", id="reset-table-button", color="primary", className="mr-1 mt-2 align-self-end"),
                    ],
                    width=12,
                    style={"margin-bottom": "20px"},
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("Mapa de Salas Necessárias"),
                        html.Hr(),
                        html.H3("Selecione os níveis de ensino para analisar"),
                        dcc.Markdown(("- Selecione os níveis de ensino que deseja visualizar no mapa.\n"
                                      "- Os hexágonos no mapa mostrarão o número de salas necessárias extra para todos os níveis de ensino selecionados.\n"
                                      "- O relatório será gerado com base nos níveis de ensino selecionados.")),
                        dcc.Dropdown(
                            id="map-variable-dropdown",
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

                        dcc.Store(id='map-data-store'),
                        dcc.Graph(id="map-graph"),
                        html.Hr(),

                        html.H3("Configurações do Reporte"),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        # Add a histogram and a range slider
                                        dcc.Markdown(("#### Selecione um intervalo de salas necessárias extra para filtrar as áreas no mapa:\n"
                                                    "- Arraste as extremidades do controle deslizante para ajustar o intervalo.\n"
                                                    "- As barras mostram a quantidade de hexágonos que têm um número de salas necessárias extra dentro do intervalo selecionado.")),
                                        dcc.Graph(id="histogram-graph"),
                                        html.Br(),
                                        dcc.RangeSlider(
                                            id="value-range-slider",
                                            min=0,  # Adjust based on your data
                                            max=100,  # Adjust based on your data
                                            step=1,
                                            value=[10, 25],  # Initial range
                                            marks={
                                                i: {
                                                    "label": str(i), 
                                                    "style": {"font-size": "1.2em"},
                                                } for i in range(0, 101, 5)
                                            },
                                            tooltip={"placement": "bottom"},
                                        ),
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        dcc.Markdown(("#### Mapa com Hexágonos Selecionados:\n"
                                                      "- Este mapa mostra os hexágonos que têm um número de salas necessárias extra dentro do intervalo selecionado.\n"
                                                      "- Os hexágonos são filtrados com base no intervalo selecionado no histograma.")),
                                        dcc.Graph(id="filtered-map-graph"),
                                    ],
                                    width=6,
                                )
                            ]
                        ),
                        html.Hr(),
                        # Center the button
                        html.Div(
                            dbc.Button("Create Report", id="create-report-button", color="primary", className="mr-1 mt-2 align-self-center justify-content-center"),
                            className="d-flex justify-content-center"
                        ),
                        html.Hr(),
                        html.Div(id="report-container"),
    


                    ], 
                    width=12)
            ]
        ),
    ]
)

# Callbacks
@app.callback(
    Output("computed-table", "data"),
    Input("municipality-dropdown", "value"),
)
def calculate_table(selected_municipality):
    if not selected_municipality:
        return None
    
    table_data = calculate_table_data(selected_municipality)
    
    return table_data.to_dict("records")

@app.callback(
    Output('computed-table', 'data', allow_duplicate=True),
    Input('computed-table', 'data_timestamp'),
    State('computed-table', 'data'),
    prevent_initial_call=True,
    )
def update_columns(timestamp, rows):
    
    main_table = pd.DataFrame(rows)
    main_table.set_index("index", inplace=True)
     
    main_table = main_table[[education_levels_short_labels[level] for level in education_levels]].astype(float)

    main_table.loc["Total de Crianças"] = main_table.loc["Total Alunos Atualmente"] * (1 + main_table.loc["Integral (%)"]) * (1 - main_table.loc["Nocturno (%)"])

    # Calculate the number of classrooms needed based on the user defined number of chairs per classroom

    # Number of classrooms needed in total
    main_table.loc["Num. Salas Necessárias"] = np.ceil(main_table.loc["Total de Crianças"] / main_table.loc["Total de Crianças por Sala"])

    # Number of classrooms needed in each level
    main_table.loc["Num. Salas Necessárias Extra"] = np.ceil(
        np.maximum(main_table.loc["Num. Salas Necessárias"] - main_table.loc["Num. Salas Atuais"], 0)
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
    if not selected_municipality:
        return None

    return calculate_table_data(selected_municipality).to_dict("records")

@app.callback(
        [Output("map-graph", "figure"), Output("map-data-store", "data")], 
        Input("municipality-dropdown", "value"),
        Input("map-variable-dropdown", "value"),
        Input('hexagon-size-slider', 'value'),
        Input('computed-table', 'data_timestamp'),
        Input("value-range-slider", "value"),
        State('computed-table', 'data'))
def update_map(selected_municipality, selected_variables, hex_res, timestamp, value_range, rows):
    if not selected_municipality:
        print("No municipality selected")
        return px.choropleth_mapbox(
            hex_gdf,
            geojson=hex_gdf.geometry.__geo_interface__,
            locations=hex_gdf.index,
            color="QT_SALAS_UTILIZADAS",  # You can change this to any other column
            color_continuous_scale="RdYlGn",
            mapbox_style="carto-positron",
            zoom=8,
            center={
                "lat": hex_gdf.geometry.centroid.y.mean(),
                "lon": hex_gdf.geometry.centroid.x.mean(),
            },
        ), None
    
    # Process the data 
    muni_hexagons = calculate_extra_salas(selected_municipality, selected_variables, rows, hex_res)

    # Create the map figure
    muni_hexagons["hover_name"] = "Salas Necessárias Extra" # Hover title
    map_figure = px.choropleth_mapbox(
        muni_hexagons,
        geojson=muni_hexagons.geometry.__geo_interface__,
        locations=muni_hexagons.index,
        color="SalasNecessariasAcum",  # You can change this to any other column
        color_continuous_scale="RdYlGn_r",
        opacity=0.5,
        hover_name="hover_name",
        hover_data={f"QT_SALAS_NECESARIAS_EXTRA_{level}": True for level in education_levels} | {"SalasNecessariasAcum": False},
        # hover_data={var : True for var in selected_variables},
        mapbox_style="carto-positron",
        labels={f"QT_SALAS_NECESARIAS_EXTRA_{level}": education_levels_labels[level] for level in education_levels} | {"SalasNecessariasAcum": "Salas Necessárias Extra"},
        # labels={var: education_levels_labels[var] for var in selected_variables} | {"SalasNecessariasAcum": "Salas Necessárias Extra"},
        zoom=8,
        center={
            "lat": muni_hexagons.geometry.centroid.y.mean(),
            "lon": muni_hexagons.geometry.centroid.x.mean(),
        },
    )
    # Set makerlinewidth to 0 to remove the white border around the hexagons
    map_figure.update_traces(marker=dict(line_width=0))

    # Store the DataFrame as JSON in the hidden div    
    return map_figure, muni_hexagons.drop(columns=["geometry"]).to_json(date_format='iso', orient='split')

@app.callback(
    [Output("histogram-graph", "figure"), Output("value-range-slider", "min"), Output("value-range-slider", "max")],
    [
        Input("map-data-store", "data"),
        Input("value-range-slider", "value"),
    ],
)
def update_histogram_and_slider(jsonified_data, value_range):
    if jsonified_data is None:
        raise PreventUpdate
    
    # Load the DataFrame from JSON
    df = pd.read_json(jsonified_data, orient='split')

    # Update the range slider min and max based on the DataFrame
    min_value = 0 # df["SalasNecessariasAcum"].min()
    max_value = df["SalasNecessariasAcum"].max()

    # Create the histogram figure
    print("DF shape", df.shape)
    histogram_figure = px.histogram(    
        df,
        x="SalasNecessariasAcum",
        nbins=50,
        title=None,
        labels={"SalasNecessariasAcum": "Salas Necessárias Extra", "count": "Número de Hexágonos"},
        # Set opacity to 50%
        opacity=0.5,
    )
    print("RANGE", value_range)
    print("DF shape", df[df["SalasNecessariasAcum"].between(value_range[0], value_range[1])].shape)
    highlighted_histogram_figure = px.histogram(    
        df[df["SalasNecessariasAcum"].between(value_range[0], value_range[1])],
        x="SalasNecessariasAcum",
        nbins=50,
        # title="Histograma de Salas Necessárias",
        # labels={"SalasNecessariasAcum": "Salas Necessárias Extra"},
        # Set opacity to 50%
        # opacity=0.5,
    )

    # Add a trace of a histogram to show the selected range
    histogram_figure.add_trace(
        highlighted_histogram_figure.data[0]
    )
    # The histogram should be on top of the original histogram not stacked
    histogram_figure.update_layout(
        barmode='overlay',
        margin=dict(l=25, r=25, b=0, t=0)
    )

    # Turn of the axis titles
    histogram_figure.update_yaxes(title="Número de Hexágonos", showticklabels=True)                                         
    histogram_figure.update_xaxes(title="Salas Necessárias Extra", showticklabels=True)
    
    
    return histogram_figure, min_value, max_value


@app.callback(
    Output("filtered-map-graph", "figure"),
    Input("histogram-graph", "figure"),
    [State("hexagon-size-slider", "value"),
     State("map-data-store", "data"),
     State("value-range-slider", "value")]
)
def update_filtered_map(hist_map, hex_size, jsonified_data, value_range):
    # Load the DataFrame from JSON
    muni_hexagons = pd.read_json(jsonified_data, orient='split')

    # Use h3 library to get the hexagon polygons and create a GeoDataFrame
    print("Creating a GeoDataFrame with the hexagon polygons ... ", end="")
    print("HEX SIZE", hex_size)
    print("HEX COLUMN", muni_hexagons.columns[0])
    muni_hexagons["geometry"] = muni_hexagons[f"hex_{hex_size}"].map(lambda x: Polygon(h3.h3_to_geo_boundary(x, geo_json=True)))
    print("Done")
    print("Creating a GeoDataFrame with the hexagon polygons ... ", end="")
    muni_hexagons = gpd.GeoDataFrame(muni_hexagons, geometry="geometry")
    print("Done")

    # Filter the DataFrame based on the range slider values
    print(f"Filtering the DataFrame based on the range slider values: {value_range}")
    filtered_df = muni_hexagons[(muni_hexagons["SalasNecessariasAcum"] >= value_range[0]) & (muni_hexagons["SalasNecessariasAcum"] <= value_range[1])]

    # MAP WITH SELECTED HEXAGONS
    # Create the map figure
    filtered_df["hover_name"] = "Salas Necessárias Extra" # Hover title
    filtered_map_figure = px.choropleth_mapbox(
        filtered_df,
        geojson=filtered_df.geometry.__geo_interface__,
        locations=filtered_df.index,
        color="SalasNecessariasAcum",  # You can change this to any other column
        color_continuous_scale="RdYlGn_r",
        opacity=0.5,
        hover_name="hover_name",
        hover_data={f"QT_SALAS_NECESARIAS_EXTRA_{level}": True for level in education_levels} | {"SalasNecessariasAcum": False},
        # hover_data={var : True for var in selected_variables},
        mapbox_style="carto-positron",
        labels={f"QT_SALAS_NECESARIAS_EXTRA_{level}": education_levels_labels[level] for level in education_levels} | {"SalasNecessariasAcum": "Salas Necessárias Extra"},
        # labels={var: education_levels_labels[var] for var in selected_variables} | {"SalasNecessariasAcum": "Salas Necessárias Extra"},
        zoom=8,
        center={
            "lat": filtered_df.geometry.centroid.y.mean(),
            "lon": filtered_df.geometry.centroid.x.mean(),
        },
    )
    # Set makerlinewidth to 0 to remove the white border around the hexagons
    filtered_map_figure.update_traces(marker=dict(line_width=0))

    # Remove margins
    filtered_map_figure.update_layout(margin=dict(l=0, r=0, t=0, b=0))

    return filtered_map_figure



@app.callback(
    Output("report-container", "children"),
    Input("create-report-button", "n_clicks"),
    [State("hexagon-size-slider", "value"),
     State("map-variable-dropdown", "value"),
     State('computed-table', 'data'),
     State("map-data-store", "data"),
     State("value-range-slider", "value"),
     State("map-graph", "figure"),
     State("municipality-dropdown", "value"),
     State("state-dropdown", "value")
     ]
)
def create_report(n_clicks, hex_size, selected_education_levels, computed_table_data, jsonified_data, value_range, map_figure, selected_municipality, selected_state):
    if n_clicks is None:
        raise PreventUpdate
    
    if isinstance(selected_education_levels, str):
        selected_education_levels = [selected_education_levels]

    # Load the DataFrame from JSON
    muni_hexagons = pd.read_json(jsonified_data, orient='split')

    # Use h3 library to get the hexagon polygons and create a GeoDataFrame
    print("Creating a GeoDataFrame with the hexagon polygons ... ", end="")
    print("HEX SIZE", hex_size)
    print("HEX COLUMN", muni_hexagons.columns[0])
    muni_hexagons["geometry"] = muni_hexagons[f"hex_{hex_size}"].map(lambda x: Polygon(h3.h3_to_geo_boundary(x, geo_json=True)))
    print("Done")
    print("Creating a GeoDataFrame with the hexagon polygons ... ", end="")
    muni_hexagons = gpd.GeoDataFrame(muni_hexagons, geometry="geometry")
    print("Done")

    # Filter the DataFrame based on the range slider values
    print(f"Filtering the DataFrame based on the range slider values: {value_range}")
    filtered_df = muni_hexagons[(muni_hexagons["SalasNecessariasAcum"] >= value_range[0]) & (muni_hexagons["SalasNecessariasAcum"] <= value_range[1])]

    # INPUT TABLE
    input_table = dash_table.DataTable(
        id="report-table",
        columns=[
            {
                "name": i, 
                "id": i, 
                "type": "numeric", 
                "format": Format(precision=2, scheme=Scheme.fixed)
            } if i != "index" else {
                "name": i, 
                "id": i
            } for i in initial_table_data.columns
        ],
        tooltip_data=tooltips,
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

    # MAP WITH SELECTED HEXAGONS
    # Create the map figure
    filtered_df["hover_name"] = "Salas Necessárias Extra" # Hover title
    map_figure = px.choropleth_mapbox(
        filtered_df,
        geojson=filtered_df.geometry.__geo_interface__,
        locations=filtered_df.index,
        color="SalasNecessariasAcum",  # You can change this to any other column
        color_continuous_scale="RdYlGn_r",
        opacity=0.5,
        hover_name="hover_name",
        hover_data={f"QT_SALAS_NECESARIAS_EXTRA_{level}": True for level in education_levels} | {"SalasNecessariasAcum": False},
        # hover_data={var : True for var in selected_variables},
        mapbox_style="carto-positron",
        labels={f"QT_SALAS_NECESARIAS_EXTRA_{level}": education_levels_labels[level] for level in education_levels} | {"SalasNecessariasAcum": "Salas Necessárias Extra"},
        # labels={var: education_levels_labels[var] for var in selected_variables} | {"SalasNecessariasAcum": "Salas Necessárias Extra"},
        zoom=8,
        center={
            "lat": filtered_df.geometry.centroid.y.mean(),
            "lon": filtered_df.geometry.centroid.x.mean(),
        },
    )
    # Set makerlinewidth to 0 to remove the white border around the hexagons
    map_figure.update_traces(marker=dict(line_width=0))

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
        import time
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
        print("HEXAGON ADDREESS EXAMPLE", hexagon_addresses.iloc[0])
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
        column_labels = {**COLUMN_LABELS, **{f"hex_{hex_size}": "Id do Hexágono"}}

        return dash_table.DataTable(
            id="hexagon-table",
            columns=[
                {"name": label, "id": col} for col, label in column_labels.items()
            ],
            data=df[column_labels.keys()].to_dict("records"),
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
            },
        )

    # Create a map with the selected hexagons
    def generate_hexagon_maps(df):
        # Iterate over the selected hexagons
        hexagon_detail_list = []

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
                    lats = np.append(lats, None)
                    lons = np.append(lons, None)

            hexagon_map = px.line_mapbox(
                lat=lats,
                lon=lons,
                # color=["red"] * len(lats),
                color_discrete_sequence=["red"],
                mapbox_style='open-street-map',
                zoom=zoom,
                center={
                    "lat": row.geometry.centroid.y,
                    "lon": row.geometry.centroid.x,
                },
            )
            # Remove the legend
            hexagon_map.update_layout(showlegend=False)

            # Create a data table with the hexagon details
            # print("ROW INFO", row)
            row_df = row.to_frame().reset_index()
            row_df.columns = ["Variável", "Valor"]
            # print("ROW DF", row_df)

            selected_columns = [f"QT_SALAS_NECESARIAS_EXTRA_{level}" for level in education_levels+["TOTAL"]] + ["short_address", "city_state"]
            filtered_row_df = row_df.loc[row_df["Variável"].isin(selected_columns)]

            column_labels = {**COLUMN_LABELS, **{f"hex_{hex_size}": "Id do Hexágono"}}
            

            ordered_index = [value for key, value in column_labels.items() if key in filtered_row_df["Variável"].unique()]

            filtered_row_df["Variável"] = filtered_row_df["Variável"].map(column_labels)

            filtered_row_df = filtered_row_df.set_index("Variável")
            
            filtered_row_df = filtered_row_df.loc[ordered_index]
            

            # row_info_dashtable = dash_table.DataTable(
            #     data=row_df.to_dict("records"),
            #     columns=[
            #         {"name": "Variable", "id": "VariableLabel"},
            #         {"name": "Value", "id": "Value"},
            #     ],
            #     style_data={
            #         'color': 'black',
            #         'backgroundColor': 'white',
            #     },
            #     style_header={
            #         'backgroundColor': 'rgb(210, 210, 210)',
            #         'color': 'black',
            #         'fontWeight': 'bold'
            #     },
            #     # Make the first column with the same style as the header
            #     style_cell_conditional=[
            #         {
            #             'if': {'column_id': 'Variable'},
            #             'fontWeight': 'bold',
            #             'backgroundColor': 'rgb(210, 210, 210)',
            #             'color': 'black',
            #         }
            #     ]
            # )

            # row_info_table_as_markdown = dcc.Markdown(filtered_row_df.to_markdown())

            table_header = [
                html.Thead(html.Tr([html.Th("Variável"), html.Th("Valor")]))
            ]

            rows = []
            for i, row in filtered_row_df.iterrows():
                # Check if the education level is in the selected levels
                if i in [COLUMN_LABELS[level] for level in selected_education_levels]:
                    
                    rows.append(html.Tr([html.Td(dbc.Badge(i, color="warning", className="me-1")), html.Td(dbc.Badge(row.values[0], color="warning", className="me-1"))]))
                else:
                    rows.append(html.Tr([html.Td(i), html.Td(row.values[0])]))

            table_body = [html.Tbody(rows)]

            table = dbc.Table(table_header + table_body, bordered=True)

            # Create a card with the hexagon map and the actual and necessary classrooms
            hexagon_details_card = dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            "Id do Hexágono: ",
                            # Open the h3geo.org website with the hexagon index on a new tab https://h3geo.org/#hex={row.values[0]}
                            html.A(row.values[0], href=f"https://h3geo.org/#hex={row.values[0]}", target="_blank"),
                        ]
                    ),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Graph(figure=hexagon_map)),
                                    dbc.Col(table),
                                    # dbc.Col([row_info_table_as_markdown]),
                                    # dbc.Col(html.Div(row_info_dashtable)),
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

    print("filtered_df.columns", filtered_df.columns)

    report_components = [
        
        html.H3("Relatório de Demanda de Salas"),

        print("selected_education_levels", selected_education_levels),
        dcc.Markdown(f'''
        
        - **Região selecionada**: {selected_municipality.capitalize()}, {selected_state.upper()}
        - **Níveis de Ensino Selecionados**: {", ".join([COLUMN_LABELS[level] for level in selected_education_levels])}
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
        dcc.Graph(figure=map_figure),
        html.H4("Detalhes do Hexágono"),
        html.H5("Salas Necessárias por Nível"),
        generate_hexagon_table(filtered_df),
        html.Br(),
        html.H4("Salas Necessárias por Hexágono"),
        generate_hexagon_maps(filtered_df),
    ]

    return report_components

if __name__ == "__main__":
    app.run(debug=True)
