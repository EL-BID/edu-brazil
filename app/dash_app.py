import time
import geopandas as gpd
import pandas as pd
import pydeck as pdk
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_deck
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from dash import Dash, html, dcc, Output, Input, State, ctx, ALL
from matplotlib import colormaps as mcm
from options import *
from helper_colormaps import cmaps_options

CLUSTER_COLORS = mcolors.ListedColormap(
    ["yellowgreen", "gold", "orange", "red", "lightgray"],
    name="clusters_cmap",
)
mpl.colormaps.register(CLUSTER_COLORS)


# Create the colorbar legend
def create_continuous_colorbar(
    cmap,
    series: pd.Series,
):
    # Create figure
    fig, ax = plt.subplots(figsize=(6, 1), layout="constrained")
    norm = mcolors.Normalize(vmin=series.min(), vmax=series.max())
    cbar = fig.colorbar(
        mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=ax,
        orientation="horizontal",
    )
    cbar.ax.tick_params(labelsize=20, labelfontfamily="sans-serif")
    # Convert figure to image and encode it for html img.src attribute
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png", dpi=100, bbox_inches="tight")
    fig_data = base64.b64encode(img_buf.getbuffer()).decode("ascii")
    fig_bar_src = f"data:image/png;base64,{fig_data}"
    img_buf.close()

    return fig_bar_src


### DASHBOARD USER JOURNEY
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)

mapbox_api_token = "pk.eyJ1IjoiY2xhdWRpbzk3IiwiYSI6ImNqbzM2NmFtMjB0YnUzd3BvenZzN3QzN3YifQ.heZHwQTY8TWhuO0u2-BxxA"

# Read hexagons and school data with geopandas
start_time = time.time()
microregions = gpd.read_parquet("../outputs/para_micro_regions.parquets")
print(f"Read micro regions in {time.time() - start_time} seconds")

start_time = time.time()
hexagons = gpd.read_parquet(
    "../outputs/20240129_para_hexs_with_accessibility_capacity_vars.parquet"
)
print(hexagons.columns)
print(f"Read hexagons in {time.time() - start_time} seconds")

start_time = time.time()
schools = gpd.read_parquet("../outputs/20240129_para_schools_final.parquet")
print(f"Read schools in {time.time() - start_time} seconds")

data = {
    "microregions": microregions,
    "hex": hexagons,
    "schools": schools,
}

# Components
welcome_modal = html.Div(
    [
        dmc.Modal(
            title="Welcome to the Para's Schools Analysis Tool!",
            id="modal-simple",
            zIndex=10000,
            opened=True,
            children=[
                dcc.Markdown(
                    """
                    ##### How to use it ?
                                            
                    1. Select a Microregion by clicking on the map
                    2. Explore the available variables using the map controls on the right
                    3. Select and priotize the variables for defining the Capacity and Accessibility Indexes
                    4. Run the Hotspot Analysis and explore the results
                    5. Save your results by downloading a report
                                            
                    > This tool was developed by the IDB Education Division. For more information please [contact us](https://www.iadb.org/en/education).
                    """
                ),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button("Start!", id="modal-submit-button"),
                    ],
                    position="center",
                ),
            ],
        ),
    ]
)

## Sidebar
region_selector = dbc.AccordionItem(
    title="1. Select a Microregion",
    children="Click on the map to select your area of interest",
)

capacity_var_selector = dbc.AccordionItem(
    title="2. Select Capacity Variables",
    children=[
        html.Div(
            [
                dbc.Switch(
                    id={
                        "type": "layer-switch-capacity",
                        "index": i,
                    },
                    label=label,
                    value=False,
                ),
                dcc.Slider(
                    id={
                        "type": "layer-slider-capacity",
                        "index": i,
                    },
                    min=0,
                    max=100,
                    step=1,
                    value=50,
                    marks={
                        i: str(i)
                        for i in range(
                            0,
                            101,
                            10,
                        )
                    },
                ),
            ]
        )
        for i, (
            value,
            label,
        ) in enumerate(capacity_var_labels.items())
    ]
    + [
        dmc.Group(
            [
                # Add a separation line
                dmc.Divider(),
                dbc.Button(
                    "Create Capacity Index",
                    id="create-capacity-index-button",
                    color="primary",
                    className="mr-3",
                ),
            ],
            position="center",
        )
    ],
)

access_var_selector = dbc.AccordionItem(
    title="3. Select Accessibility Variables",
    style={"overflow": "scroll"},
    children=[
        html.Div(
            [
                dbc.Switch(
                    id={
                        "type": "layer-switch-access",
                        "index": i,
                    },
                    label=label,
                    value=False,
                ),
                dcc.Slider(
                    id={
                        "type": "layer-slider-access",
                        "index": i,
                    },
                    min=0,
                    max=100,
                    step=1,
                    value=50,
                    marks={
                        i: str(i)
                        for i in range(
                            0,
                            101,
                            10,
                        )
                    },
                ),
            ]
        )
        for i, (
            value,
            label,
        ) in enumerate(access_var_labels.items())
    ]
    + [
        dmc.Group(
            [
                # Add a separation line
                dmc.Divider(),
                dbc.Button(
                    "Create Accessibility Index",
                    id="create-access-index-button",
                    color="primary",
                    className="mr-3",
                ),
            ],
            position="center",
        )
    ],
)

hotspot_analysis = dbc.AccordionItem(
    title="4. Run HotSpot Analysis and Results",
    children=[
        dbc.Button(
            "Run Hotspot Analysis",
            id="run-hotspot-analysis-button",
            color="primary",
            className="mr-3",
        ),
    ],
)

download_results = dbc.AccordionItem(
    title="5. Download Results",
    children=[],
)

sidebar = dbc.Col(
    html.Div(
        [
            dbc.Card(
                [
                    dbc.CardHeader("Schools Gap Analysis Tool"),
                    dbc.CardBody(
                        [
                            dbc.Accordion(
                                [
                                    region_selector,
                                    capacity_var_selector,
                                    access_var_selector,
                                    hotspot_analysis,
                                    download_results,
                                ],
                                style={"overflow": "scroll"},
                            )
                        ]
                    ),
                ],
                className="mt-3",
            ),
        ],
    ),
    width=3,
    className="sidebar mt-3",
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
        "overflow-x": "hidden",
        "overflow-y": "scroll",
    },
)

## Main map
color_variable_picker = dbc.Card(
    id="color-variable-picker",
    className="mb-3",
    children=dbc.CardBody(
        [
            dbc.Label("Color Variable"),
            dmc.Select(
                id="color-variable-dropdown",
                data=[
                    {
                        "label": column_labels[var],
                        "value": var,
                        "group": group,
                    }
                    for group, var_list in color_variable_options
                    for var in var_list
                ],
                value="pop_6_14_years_adj",
            ),
            dmc.Select(
                id="color-palette-dropdown",
                label="Select Color Palette",
                placeholder="Select one",
                value="viridis",
                data=[
                    {"value": cmap, "label": cmap, "group": cmap_category}
                    for cmap_category, cmap_list in cmaps_options
                    for cmap in cmap_list
                ],
            ),
            html.Br(),
            html.Img(id="colorscale-legend", style={"width": "100%", "height": "5vh"}),
        ],
    ),
)

height_variable_picker = dbc.Card(
    id="height-variable-picker",
    className="mb3",
    children=dbc.CardBody(
        [
            dbc.Label("Height Variable"),
            dmc.Select(
                id="height-variable-dropdown",
                data=[
                    {"label": column_labels[column], "value": column, "group": group}
                    for group, var_list in height_variable_options
                    for column in var_list
                ],
                value="pop_6_14_years_adj",
            ),
            dbc.Label("Height Scale"),
            dcc.Slider(
                id="height-scale-slider",
                min=0,
                max=100,
                step=1,
                value=15,
                marks={i: str(i) for i in range(0, 101, 10)},
            ),
        ],
    ),
)

map_controls = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(color_variable_picker),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(height_variable_picker),
            ]
        ),
    ],
    style={
        "position": "absolute",
        "top": "10px",
        "right": "10px",
        "zIndex": "100",
        "backgroundColor": "rgba(255, 255, 255, 0)",
        "padding": "10px",
        "borderRadius": "0px",
        "boxShadow": "0px 0px 5px 0px rgba(0,0,0,0)",
    },
)

# Create the initial map with pydeck and dash_deck
adm_layer = pdk.Layer(
    "GeoJsonLayer",
    data=microregions,
    get_fill_color=[255, 255, 255, 0],
    get_line_color=[255, 255, 255],
    get_line_width=1000,
    pickable=True,
    auto_highlight=True,
    stroked=True,
    filled=True,
)

bbox = microregions.total_bounds.reshape(2, 2)
start_time = time.time()
initial_view_state = pdk.data_utils.compute_view(
    list(zip(schools.geometry.x, schools.geometry.y)), view_proportion=0.9
)
print(f"Computed view state in {time.time() - start_time} seconds")

r = pdk.Deck(
    layers=[adm_layer],
    initial_view_state=initial_view_state,
    map_provider="mapbox",
    map_style=pdk.map_styles.SATELLITE,
)

initial_map = dash_deck.DeckGL(
    r.to_json(),
    id="deck-gl",
    enableEvents=["click"],  # , 'hover', 'dragStart', 'dragEnd'] # True
    tooltip={"text": "{name_micro}, {name_state}"},
    mapboxKey=mapbox_api_token,
    style={
        "width": "100%",
        "height": "100vh",
        "position": "relative",
    },
)

main_map = dbc.Col(
    html.Div(id="map", children=initial_map),
    width=9,
    className="p-0",
    style={
        "margin-left": "18rem",
        "margin-right": "2rem",
        "padding": "2rem 1rem",
        "display": "inline-block",
    },
)

# Layout
app.layout = dbc.Container(
    [
        welcome_modal,
        dbc.Row(
            [
                sidebar,
                main_map,
            ]
        ),
    ],
    fluid=True,
)


# Callbacks
@app.callback(
    Output("modal-simple", "opened"),
    Input("modal-submit-button", "n_clicks"),
    State("modal-simple", "opened"),
    prevent_initial_call=True,
)
def modal_switch(nc1, opened):
    return not opened


import pandas as pd
import numpy as np
import matplotlib
import io
import base64

matplotlib.use("agg")


@app.callback(
    Output("map", "children"),
    # Output("colorscale-legend", "src", allow_duplicate=True),
    Input("deck-gl", "clickInfo"),
    # prevent_initial_call="initial_duplicate",  # True
)
def select_microregion(click):
    print("Selecting microregion ...")
    if click is not None:
        # Get the clicked microregion
        selected_code_micro = click["object"]["code_micro"]
        selected_microregion = data["microregions"][
            microregions["code_micro"] == selected_code_micro
        ]
        data["selected_microregion"] = selected_microregion
        hexagons_clipped = data["hex"].clip(selected_microregion)

        # Create the color column for the plot
        cmap = mcm.get_cmap("viridis")
        rgba_list = cmap(hexagons_clipped["pop_6_14_years_adj"])
        hexagons_clipped["color"] = [[int(c * 255) for c in rgba] for rgba in rgba_list]

        color_variable_picker.children.children[3].src = create_continuous_colorbar(
            cmap, hexagons_clipped["pop_6_14_years_adj"]
        )

        schools_clipped = data["schools"].clip(selected_microregion)

        # Update the map view to center on the selected microregion
        view_state = pdk.data_utils.compute_view(
            list(zip(schools_clipped.geometry.x, schools_clipped.geometry.y)),
            view_proportion=0.9,
        )
        # Change pitch and bearing to get a better view
        view_state.pitch = 45
        view_state.bearing = 0

        # Create the map with pydeck and dash_deck
        adm_layer = pdk.Layer(
            "GeoJsonLayer",
            data=selected_microregion,
            get_line_color=[255, 0, 0],
            get_line_width=500,
            pickable=False,
            stroked=True,
            filled=False,
        )

        map_layer = pdk.Layer(
            "H3HexagonLayer",
            data=hexagons_clipped,
            get_hexagon="hex",
            get_fill_color="color",
            get_line_color=[0, 0, 0],
            get_elevation="pop_6_14_years_adj",
            elevation_scale=20,
            elevation_range=[0, 1000],
            extruded=True,
            pickable=True,
            auto_highlight=True,
            coverage=1,
        )

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=schools_clipped,
            get_position="geometry.coordinates",
            get_color=[255, 0, 0],
            get_radius=100,
            pickable=True,
            auto_highlight=True,
        )

        r = pdk.Deck(
            layers=[adm_layer, map_layer, scatter_layer],
            initial_view_state=view_state,
            map_provider="mapbox",
            map_style=pdk.map_styles.SATELLITE,
        )

        map = dash_deck.DeckGL(
            r.to_json(),
            id="deck-gl",
            enableEvents=["click"],  # , 'hover', 'dragStart', 'dragEnd']
            # enableEvents=True,
            tooltip=True,
            mapboxKey=mapbox_api_token,
            style={
                "width": "100%",
                "height": "100vh",
                "position": "relative",
            },
        )
        # Return the updated layers
        return [map, map_controls]

    # Return the original layers if no microregion is selected
    return initial_map


@app.callback(
    Output("deck-gl", "data"),
    Output("colorscale-legend", "src", allow_duplicate=True),
    Input("color-variable-dropdown", "value"),
    Input("color-palette-dropdown", "value"),
    Input("height-variable-dropdown", "value"),
    Input("height-scale-slider", "value"),
    prevent_initial_call=True,
)
def update_hex_layer_color(
    color_variable, color_palette, height_variable, height_scale
):
    # Update the map layers based on the user's selections
    print("Updating color layer", color_variable, color_palette)
    print("Data selected microregion", data["selected_microregion"]["name_micro"])
    print("Data hex", data["hex"].columns)
    if color_variable and color_palette and data["selected_microregion"] is not None:
        selected_microregion = data["selected_microregion"]
        hexagons_clipped = data["hex"].clip(selected_microregion.iloc[0].geometry)
        print("Hexagons clipped", hexagons_clipped.shape)
        print("Hexagons clipped columns", hexagons_clipped.columns)

        print("Creating colorscale ...")
        cmap = mcm.get_cmap(color_palette)
        rgba_list = cmap(hexagons_clipped[color_variable])
        print("RGBA list", rgba_list)
        hexagons_clipped["color"] = [[int(c * 255) for c in rgba] for rgba in rgba_list]
        print("Color column created")

        print("Plotting ...")
        fig, ax = plt.subplots(figsize=(6, 1), layout="constrained")
        norm = mcolors.Normalize(
            vmin=hexagons_clipped[color_variable].min(),
            vmax=hexagons_clipped[color_variable].max(),
        )
        fig.colorbar(
            mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
            cax=ax,
            orientation="horizontal",
            label=column_labels[color_variable],
        )
        # Create an image from the plot
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format="png", dpi=150, bbox_inches="tight")
        # Embed the result in the html output.
        fig_data = base64.b64encode(img_buf.getbuffer()).decode("ascii")
        fig_bar_src = f"data:image/png;base64,{fig_data}"
        img_buf.close()

        print("Colorscale created")

        schools_clipped = data["schools"].clip(selected_microregion)

        # Update the map view to center on the selected microregion
        view_state = pdk.data_utils.compute_view(
            list(zip(schools_clipped.geometry.x, schools_clipped.geometry.y)),
            view_proportion=0.9,
        )

        # Create the map with pydeck and dash_deck
        adm_layer = pdk.Layer(
            "GeoJsonLayer",
            data=selected_microregion,
            get_line_color=[255, 0, 0],
            get_line_width=500,
            pickable=False,
            stroked=True,
            filled=False,
        )

        map_layer = pdk.Layer(
            "H3HexagonLayer",
            data=hexagons_clipped,
            get_hexagon="hex",
            get_fill_color="color",
            get_line_color=[0, 0, 0],
            get_elevation=height_variable,
            elevation_scale=height_scale,
            elevation_range=[0, 500],
            extruded=True,
            pickable=True,
            auto_highlight=True,
            coverage=1,
        )

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=schools_clipped,
            get_position="geometry.coordinates",
            get_color=[255, 0, 0],
            get_radius=100,
            pickable=True,
            auto_highlight=True,
        )

        r = pdk.Deck(
            layers=[adm_layer, map_layer, scatter_layer],
            initial_view_state=view_state,
            map_provider="mapbox",
            map_style=pdk.map_styles.SATELLITE,
        )

        # Return the updated layers
        return r.to_json(), fig_bar_src


import hotspot_analysis as ha
from shapely.geometry import box


def calculate_index(hexs, var_labels, switches, sliders):
    weights = pd.DataFrame(
        {
            "column_name": list(var_labels.keys()),
            "weights": sliders,
        }
    )
    # Filter the values with the switches
    weights = weights[switches]
    # Normalize the weights to sum to 1
    weights["weights_norm"] = weights["weights"] / weights["weights"].sum()

    return ha.h3_hotspot_analysis(hexs, weights["column_name"], weights["weights_norm"])


@app.callback(
    Output("color-variable-dropdown", "data"),
    Output("color-variable-dropdown", "value"),
    Output("color-palette-dropdown", "data"),
    Output("color-palette-dropdown", "value"),
    Input("create-capacity-index-button", "n_clicks"),
    Input("create-access-index-button", "n_clicks"),
    Input("run-hotspot-analysis-button", "n_clicks"),
    State({"type": "layer-switch-capacity", "index": ALL}, "value"),
    State({"type": "layer-slider-capacity", "index": ALL}, "value"),
    State({"type": "layer-switch-access", "index": ALL}, "value"),
    State({"type": "layer-slider-access", "index": ALL}, "value"),
    State("color-variable-dropdown", "data"),
    State("color-variable-dropdown", "value"),
    State("color-palette-dropdown", "data"),
    State("color-palette-dropdown", "value"),
    prevent_initial_call=True,
)
def calculate_index_callback(
    capacity_button,
    access_button,
    hotspot_button,
    capacity_switches,
    capacity_sliders,
    access_switches,
    access_sliders,
    color_options_state,
    color_variable_value,
    color_palette_state,
    color_palette_value,
):
    button_clicked = ctx.triggered_id

    if button_clicked:
        # Prepare data
        hexs = data["hex"]
        # Fill na values with 0 in numerical columns
        hexs[hexs.select_dtypes(include="number").columns] = hexs.select_dtypes(
            include="number"
        ).fillna(0)
        # Fill na values with "N" in categorical columns
        hexs[hexs.select_dtypes(include="object").columns] = hexs.select_dtypes(
            include="object"
        ).fillna("N")

        microregion = data["selected_microregion"].iloc[0]
        microregion_hexs = hexs.clip(box(*microregion.geometry.bounds).buffer(0.005))

        if button_clicked == "create-capacity-index-button":
            print("Calculating capacity index ...")
            capacity_index, capacity_gi, capacity_psim = calculate_index(
                microregion_hexs,
                capacity_var_labels,
                capacity_switches,
                capacity_sliders,
            )

            # Create empty columns for the capacity index and the two scoresç
            hexs = hexs.assign(
                capacity_index=np.nan, capacity_gi=np.nan, capacity_psim=np.nan
            )

            # Add the capacity index to the hexagons dataframe
            hexs.loc[microregion_hexs.index, "capacity_index"] = capacity_index
            hexs.loc[microregion_hexs.index, "capacity_gi"] = capacity_gi
            hexs.loc[microregion_hexs.index, "capacity_psim"] = capacity_psim

            # Update the data dictionary
            data["hex"] = hexs

            # Add the capacity index to the color variable options
            color_options_state = [
                opt for opt in color_options_state if opt["value"] != "capacity_index"
            ]
            color_options_state.append(
                {
                    "label": "Capacity Index",
                    "value": "capacity_index",
                    "group": "Schools Capacity",
                }
            )
            column_labels["capacity_index"] = "Capacity Index"

            return (
                color_options_state,
                "capacity_index",
                color_palette_state,
                color_palette_value,
            )

        if button_clicked == "create-access-index-button":
            print("Calculating accessibility index ...")
            access_index, access_gi, access_psim = calculate_index(
                microregion_hexs, access_var_labels, access_switches, access_sliders
            )

            # Create empty columns for the capacity index and the two scoresç
            hexs = hexs.assign(
                accessibility_index=np.nan,
                accessibility_gi=np.nan,
                accessibility_psim=np.nan,
            )

            # Add the capacity index to the hexagons dataframe
            hexs.loc[microregion_hexs.index, "accessibility_index"] = access_index
            hexs.loc[microregion_hexs.index, "accessibility_gi"] = access_gi
            hexs.loc[microregion_hexs.index, "accessibility_psim"] = access_psim

            # Update the data dictionary
            data["hex"] = hexs

            # Add the capacity index to the color variable options
            color_options_state = [
                opt
                for opt in color_options_state
                if opt["value"] != "accessibility_index"
            ]
            color_options_state.append(
                {
                    "label": "Accessibility Index",
                    "value": "accessibility_index",
                    "group": "Schools Accessibility",
                }
            )
            column_labels["accessibility_index"] = "Accessibility Index"

            return (
                color_options_state,
                "accessibility_index",
                color_palette_state,
                color_palette_value,
            )

        if button_clicked == "run-hotspot-analysis-button":
            # Check if the capacity and accessibility indexes are available
            if ("capacity_index" in hexs.columns) and (
                "accessibility_index" in hexs.columns
            ):
                # Run the crossed analysis
                print("Running hotspot analysis ...")
                # Create clusters
                pvalue = 0.05
                start = time.time()
                clusters = ha.h3_scores_clusters(
                    {
                        "gi": microregion_hexs["capacity_gi"],
                        "psim": microregion_hexs["capacity_psim"],
                    },
                    {
                        "gi": microregion_hexs["accessibility_gi"],
                        "psim": microregion_hexs["accessibility_psim"],
                    },
                    microregion_hexs,
                    significance=pvalue,  # 95% confidence level
                )
                microregion_hexs["clusters"] = clusters.replace(
                    {"HH": 0, "HL": 1, "LH": 2, "LL": 3, "N": 4}
                )

                print(f"Clusters created in {time.time() - start:.2f} seconds")

                cluster_labels = ["HH", "HL", "LH", "LL", "N"]
                ["yellowgreen", "gold", "orange", "red", "lightgray"],
                [0, 1, 2, 3, 4]

                # Plot clusters in the first element of the third row
                cluster_counts = microregion_hexs["clusters"].value_counts()
                cluster_counts = (
                    cluster_counts.reindex(cluster_labels).fillna(0).astype(int)
                )

                # Create empty columns for the capacity index and the two scoresç
                hexs = hexs.assign(clusters=np.nan)

                # Add the capacity index to the hexagons dataframe
                hexs.loc[microregion_hexs.index, "clusters"] = clusters

                # Update the data dictionary
                data["hex"] = hexs

                # Add clusters to the color variable options
                color_options_state = [
                    opt for opt in color_options_state if opt["value"] != "clusters"
                ]
                color_options_state.append(
                    {
                        "label": "Cluster Hot-Cold Spots",
                        "value": "clusters",
                        "group": "Analysis Results",
                    }
                )
                column_labels["clusters"] = "Cluster Hot-Cold Spots"

                color_palette_state.append(
                    {
                        "value": "clusters_cmap",
                        "label": "Clusters Colors",
                        "group": "Analysis Results",
                    }
                )

                return (
                    color_options_state,
                    "clusters",
                    color_palette_state,
                    "clusters_cmap",
                )


if __name__ == "__main__":
    app.run_server(debug=True)
