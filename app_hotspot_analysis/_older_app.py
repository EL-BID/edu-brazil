import geopandas as gpd
import os
import numpy as np
import pandas as pd
import pydeck as pdk
import app.dash_app as dash_app
from app.dash_app import dcc, html
import dash_deck
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from app.options import *

external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash_app.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
)
app.title = "School Capacity & Accessibility in Pará, Brazil"
server = app.server

mapbox_api_token = os.getenv("MAPBOX_API_KEY")

PYDECK_VIEWSTATE = pdk.ViewState(
    latitude=-12.1, longitude=-77, zoom=10, bearing=0, pitch=45
)

# Load Data
hexs = gpd.read_parquet(
    "outputs/20240129_para_hexs_with_accessibility_capacity_vars.parquet"
)
schools = gpd.read_parquet("outputs/20240129_para_schools_final.parquet")

data_dict = {"hex": hexs, "zone": hexs}

# Static layers
schools_layer = pdk.Layer(
    "GeoJsonLayer",
    data=schools,
    pickable=True,
    get_fill_color=[255, 0, 0],
)

h3_hexagons_layer = pdk.Layer(
    "H3HexagonLayer",
    data=hexs,
    get_hexagon="hex",
    pickable=True,
    stroked=False,
    material=True,
    filled=True,
    extruded=True,
    elevation_scale=0.2,
    opacity=0.2,
    get_elevation="poblacion_2020",
    get_fill_color="[255 - income_pc, 255, income_pc]",
    # get_fill_color=[255, 255, 255, 0],
)

header = dbc.Row(
    [
        dbc.Col(
            html.A(
                html.H3("School Analysis in Pará, Brazil"),
                target="_parent",
                href="https://github.com/EL-BID/edu-brazil",
            )
        )
    ]
)

controls = dbc.Row(
    dbc.Col(
        [
            dbc.Card(
                [
                    dbc.Label("Unidad de análisis:"),
                    dcc.Dropdown(
                        id="spatial_unit_selector",
                        options=["hex", "zone"],
                        value="hex",
                        placeholder="Selecciona la unidad de análisis ...",
                    ),
                ]
            ),
            dbc.Card(
                [
                    dbc.Label("Variable (color):"),
                    dcc.Dropdown(
                        id="var_selector",
                        options={
                            key: key for key, value in capacity_var_labels.items()
                        },
                        value=[*capacity_var_labels.keys()][0],
                        placeholder="Selecciona la variable que deseas ver ...",
                    ),
                ]
            ),
            dbc.Card(
                [
                    dbc.Label("Filtro de categorías (color):"),
                    dcc.Dropdown(
                        id="dur_selector",
                        multi=True,
                        placeholder="Selecciona una categoría ...",
                    ),
                ]
            ),
            dbc.Card(
                [
                    dbc.Label("Población (altura):"),
                    dcc.Dropdown(
                        id="pop_selector",
                        options={key: key for key, value in access_var_labels.items()},
                        value=[*access_var_labels.keys()][0],
                        placeholder="Selecciona la población que deseas ver ...",
                    ),
                ]
            ),
            dbc.Card(
                [
                    dbc.Label("Filtro de población:"),
                    dcc.Graph(id="count_graph", config=dict(displayModeBar=False)),
                    dcc.RangeSlider(
                        id="pop_slider",
                        min=0,
                        step=100,
                        value=[0, 10000],
                        updatemode="drag",
                        marks=None,
                        tooltip={"always_visible": True, "placement": "bottom"},
                    ),
                ]
            ),
            dbc.Card(
                [
                    dbc.Label("Opacidad:"),
                    dcc.Slider(
                        id="opacity_slider",
                        min=0,
                        max=1,
                        value=0.2,
                        step=0.05,
                        updatemode="drag",
                        marks=None,
                        tooltip={"always_visible": False, "placement": "bottom"},
                    ),
                ]
            ),
            dbc.Card(
                [
                    dbc.Label("Elevación:"),
                    dcc.Slider(
                        id="elevation_slider",
                        min=0,
                        max=1,
                        value=0.2,
                        step=0.05,
                        updatemode="drag",
                        marks=None,
                        tooltip={"always_visible": False, "placement": "bottom"},
                    ),
                ]
            ),
            dbc.Card(
                [
                    dbc.Label("Capas de información:"),
                    dcc.Checklist(
                        id="layers_selector",
                        options=[
                            {"label": "Hexagons", "value": "spatial_unit"},
                            {"label": "Schools", "value": "schools"},
                        ],
                        value=["spatial_unit", "schools"],
                        labelClassName="checklistLabel",
                    ),
                ]
            ),
        ]
    )
)

# footer = dbc.Row(
#     dbc.Col(
#         [
#             html.A(
#                 html.Img(src=app.get_asset_url("images/logo.svg"), width="250px"),
#                 target="_parent",
#                 href="https://observatoriodelima.org",
#             ),
#         ],
#         style={"text-align": "center"},
#     )
# )

sidebar = dbc.Container([html.Hr(), header, controls, html.Hr()], id="sidebar")

content = html.Div(
    [
        html.Div(id="map_legend", className="options-panel top-right"),
        # html.Div(id="map-div"),
    ],
    id="content",
)

app.layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(sidebar, lg=3, md=4, sm=12),  # Column for user controls
                dbc.Col(content, lg=9, md=8, sm=12),  # Column for map content
            ],
        ),
    ]
)


def create_html_tooltip(variables):
    tooltip = "<b>HEX info</b>:<br>"
    for var, label in variables.items():
        tooltip += "<b>" + label + "</b>: {" + var + "} <br>"
    tooltip = (
        "<b>POI info</b>:<br>{info}<br>---------------------------------<br>" + tooltip
    )

    return tooltip


# html_tooltip = create_html_tooltip(variables_label)


def create_categorical_legend(dataframe, column, color_columns, order, label):
    cat_colors = dataframe[[column] + color_columns].drop_duplicates().dropna()
    cat_colors.index = cat_colors[column]
    cat_colors = cat_colors.loc[order]

    # Format color columns as rgb(255, 255, 255) string
    formatted_color_string = "rgb("
    formatted_color_string += cat_colors[color_columns[0]].astype(str)
    formatted_color_string += ","
    formatted_color_string += cat_colors[color_columns[1]].astype(str)
    formatted_color_string += ","
    formatted_color_string += cat_colors[color_columns[2]].astype(str)
    formatted_color_string += ")"

    bar_width = 100 / formatted_color_string.shape[0]
    marks_width = int(100 / formatted_color_string.shape[0])

    color_bar = [
        html.Div(
            className="legend", style={"background": value, "width": f"{bar_width}%"}
        )
        for _, value in formatted_color_string.items()
    ]

    marks_val = cat_colors.index.str.extract(pat="([0-9]+)")[0]
    marks_val = marks_val.values.tolist()
    number_marks = [
        html.Div(
            className="legend", children=[f"{mark}"], style={"width": f"{marks_width}%"}
        )
        for mark in marks_val
    ]

    legend = [
        html.Strong(label),
        html.Div(className="layout", children=color_bar),
        html.Div(className="layout", children=number_marks),
    ]

    return legend


# @app.callback(
#     [Output("dur_selector", "options"), Output("dur_selector", "value")],
#     [Input("var_selector", "value")],
# )
# def update_cat_options(selected_var):
#     vals = sorted(hexs[selected_var].dropna().unique().tolist())
#     opts = [{"label": i, "value": i} for i in vals]

#     return opts, vals


@app.callback(
    [
        Output("map-div", "children")
        #  , Output("map_legend", "children")
    ],
    [
        Input("spatial_unit_selector", "value"),
        Input("var_selector", "value"),
        Input("dur_selector", "value"),
        Input("pop_selector", "value"),
        Input("pop_slider", "value"),
        Input("opacity_slider", "value"),
        Input("elevation_slider", "value"),
        Input("layers_selector", "value"),
    ],
)
def update_map(
    selected_spatial_unit,
    selected_var,
    dur_selector,
    selected_pop,
    pop_range,
    opacity_value,
    elevation_value,
    selected_layers,
):
    # selected_columns = [
    #     f"{selected_var}",
    #     f"{selected_var}",
    # ]

    # df = data_dict[selected_spatial_unit]

    # dur_filter = df[selected_columns[1]].isin(dur_selector)
    # pop_filter = df[selected_pop].between(pop_range[0], pop_range[1])

    # filtered_df = df[(dur_filter & pop_filter)]

    # if selected_spatial_unit == "hex":
    layer = pdk.Layer(
        "H3HexagonLayer",
        hexs,
        get_hexagon="hex",
        id="h3hex-layer",
        pickable=True,
        stroked=False,
        material=True,
        filled=True,
        extruded=True,
        # elevation_scale=elevation_value,
        # opacity=opacity_value,
        # get_elevation=selected_pop,
        # get_fill_color=selected_columns[-3:],
        get_line_color=[255, 255, 255],
        line_width_min_pixels=0,
    )
    # else:
    #     layer = pdk.Layer(
    #         "PolygonLayer",
    #         filtered_df.round(2),
    #         get_polygon="shell",
    #         id="poly-layer",
    #         pickable=True,
    #         stroked=False,
    #         material=True,
    #         filled=True,
    #         extruded=True,
    #         elevation_scale=elevation_value,
    #         opacity=opacity_value,
    #         get_elevation=selected_pop,
    #         get_fill_color=selected_columns[-3:],
    #         get_line_color=[255, 255, 255],
    #         line_width_min_pixels=0,
    #     )

    # tooltip = {"html": html_tooltip}

    # layers_dict = {
    #     "schools": schools_layer,
    #     "spatial_unit": layer,
    # }

    r = pdk.Deck(
        layers=[layer],  # [layers_dict[sel_layer] for sel_layer in selected_layers],
        initial_view_state=PYDECK_VIEWSTATE,
        map_style="light",
    )

    deck_component = dash_deck.DeckGL(
        r.to_json(),
        id="deck-gl",
        mapboxKey=mapbox_api_token,
        # tooltip=tooltip,
        style={"width": "100%"},
    )

    # order = sorted(hexs[selected_columns[1]].dropna().unique().tolist())

    # if "dur" in selected_var:
    #     label = "Duración del viaje (en minutos)"
    # else:
    #     label = "Indicador de acceso a servicio"

    # map_legend = create_categorical_legend(
    #     dataframe=hexs,
    #     column=selected_columns[1],
    #     color_columns=selected_columns[-3:],
    #     order=order,
    #     label=label,
    # )

    return [deck_component]  # , map_legend


# Selectors -> count graph
# @app.callback(
#     Output("count_graph", "figure"),
#     [Input("pop_selector", "value"), Input("pop_slider", "value")],
# )
# def make_count_figure(selected_pop, pop_range):
#     hist, bins_edges = np.histogram(hexs[selected_pop], bins=25)

#     colors = []
#     for i in bins_edges:
#         if pop_range[0] <= i <= pop_range[1]:
#             colors.append("rgb(123, 199, 255)")
#         else:
#             colors.append("rgba(123, 199, 255, 0.2)")

#     data = [
#         dict(
#             type="bar",
#             x=bins_edges,
#             y=hist,
#             name="Distribución de la población",
#             marker=dict(color=colors),
#         ),
#     ]
#     layout = dict(
#         margin=dict(l=20, r=20, t=0, b=5),
#         height=100,
#         yaxis=dict(showticklabels=False, visible=False),
#         xaxis=dict(showticklabels=False, visible=False),
#     )
#     figure = dict(data=data, layout=layout)

#     return figure


# @app.callback(
#     Output("pop_slider", "max"),
#     [Input("spatial_unit_selector", "value"), Input("pop_selector", "value")],
# )
# def update_pop_slider(selected_spatial_unit, selected_pop):
#     max_ = data_dict[selected_spatial_unit][selected_pop].max()
#     return max_


if __name__ == "__main__":
    if "HEROKU_ENV" in os.environ:
        # Add Google Analytics
        app.scripts.append_script(
            {
                "external_url": "https://www.googletagmanager.com/gtag/js?id=UA-165263494-1"
            }
        )
        app.run_server(debug=False)
    else:
        app.run(debug=True)
