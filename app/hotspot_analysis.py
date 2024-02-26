# School Infraestucture Analysis

# Load data and geospatial libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import urbanpy as up
import h3
import libpysal
import contextily as ctx
from esda.getisord import G_Local


def minmax_scaler(col, a=0, b=1):
    """
    Min-max scaler

    Parameters
    ----------
    col : pandas.Series
        Series to be scaled
    a : float, optional
        Min value of the scaled Series. Default is 0.
    b : float, optional
        Max value of the scaled Series. Default is 1.

    Returns
    -------
    pandas.Series
        Scaled Series
    """

    return (col - col.min()) * (b - a) / (col.max() - col.min()) + a


def linear_combination(x, w):
    """
    Linear combination of features

    Parameters
    ----------
    row : pandas.Series
        Series with features to be combined
    weights : list
        List of weights for each feature

    Returns
    -------
    float
        Linear combination of features
    """
    return np.dot(x, w)


def w_from_hids(hids, kring=1):
    """
    Create a spatial weights matrix from a list of hexagons and a k-ring.
    Extracted from: https://gist.github.com/darribas/c909209bc58fc0deddf46d8ec8fce6d0

    Parameters
    ----------
    hids : list
        List of hexagons ids
    kring : int, optional
        Number of rings to be considered. Default is 1.

    Returns
    -------
    pysal.lib.weights.W
        Spatial weights matrix

    """
    shids = set(hids)
    neis = {}
    for hid in hids:
        neis[hid] = list(h3.k_ring(hid, kring).intersection(shids))
    w = libpysal.weights.W(neis, id_order=hids, ids=hids)
    return w


def composite_spatial_index(
    hex_gdf: gpd.GeoDataFrame,
    features_names: list,
    features_weights: list,
):
    """
    Calculate a composite spatial index for a set of features

    Parameters
    ----------
    hex_gdf : gpd.GeoDataFrame
        GeoDataFrame with hexagons and features
    features_names : list
        List of features names
    features_weights : list
        List of weights for each feature

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with the composite index
    """

    # Check if features weights sum to 1.0
    try:
        assert np.array(features_weights).sum() == 1.0
    except AssertionError as e:
        e.args += ("Features weights must sum to 1.0",)
        raise e

    # Check there are no na values in the features
    if hex_gdf[features_names].isna().sum().sum() > 0:
        raise ValueError(
            "There are NA values in the features. Please remove/impute NA values."
        )

    # Create a new column with the weighted sum of mix-max scaled features
    composite_score = (
        hex_gdf[features_names]
        .apply(minmax_scaler, axis=0)  # Make columns values between 0 and 1
        .apply(
            linear_combination,
            w=features_weights,
            axis=1,  # Row-wise linear combination
        )
    )

    return composite_score


# Create a function to streamline the process
def h3_hotspot_analysis(
    hex_gdf: gpd.GeoDataFrame,
    features_names: list,
    features_weights: list,
    spatial_weights: libpysal.weights.W = None,
    kring: int = 3,
):
    """
    Perform a hotspot analysis for a set of features

    Parameters
    ----------
    hex_col : str
        Column name with the hexagons ids
    hex_gdf : gpd.GeoDataFrame
        GeoDataFrame with hexagons and features
    features_names : list
        List of features names
    features_weights : list
        List of weights for each feature
    kring : int, optional
        Number of rings to be considered. Default is 1.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with the composite index
    """

    # Create a composite spatial index
    composite_score = composite_spatial_index(hex_gdf, features_names, features_weights)

    spatial_weights = w_from_hids(hex_gdf["hex"], kring=kring)

    # Perform a spatial hotspot analysis
    hotspot = G_Local(composite_score, spatial_weights, star=True)

    return composite_score, hotspot.Zs, hotspot.p_sim


def h3_scores_clusters(
    score_1: dict,
    score_2: dict,
    hexs: gpd.GeoDataFrame,
    significance: float,
):
    """
    Calculate h3 scores clusters as High-Low combinations of two scores.

    Parameters
    ----------
    score_1: dict
        Dictionary with the composite score, Gs and p_sim from the hotspot analysis
    score_2: dict
        Dictionary with the composite score, Gs and p_sim from the hotspot analysis
    hexs: gpd.GeoDataFrame
        GeoDataFrame with the hexagons
    significance: float

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with the composite index
    """

    high_1 = (score_1["psim"] < significance) & (score_1["gi"] > 0)
    low_1 = (score_1["psim"] < significance) & (score_1["gi"] < 0)

    high_2 = (score_2["psim"] < significance) & (score_2["gi"] > 0)
    low_2 = (score_2["psim"] < significance) & (score_2["gi"] < 0)

    # Assign the clusters (HH, HL, LH, LL), and N for non-significant

    clusters = pd.Series(index=hexs.index, data="N")
    clusters[high_1 & high_2] = "HH"
    clusters[high_1 & low_2] = "HL"
    clusters[low_1 & high_2] = "LH"
    clusters[low_1 & low_2] = "LL"

    return clusters


if __name__ == "__main__":
    import time
    import contextily as ctx
    from shapely.geometry import box
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from tqdm import tqdm

    # Load data
    start = time.time()
    hexs = gpd.read_parquet(
        "outputs/20240129_para_hexs_with_accessibility_capacity_vars.parquet"
    )
    print(f"Data loaded in {time.time() - start:.2f} seconds")

    # Fill na values with 0 in numerical columns
    hexs[hexs.select_dtypes(include="number").columns] = hexs.select_dtypes(
        include="number"
    ).fillna(0)
    # Fill na values with "N" in categorical columns
    hexs[hexs.select_dtypes(include="object").columns] = hexs.select_dtypes(
        include="object"
    ).fillna("N")

    # Define features and weights for the two scores
    access_features = [
        "population_2020",  # Higher better
        "pop_6_14_years_adj",  # Higher better
        "income_pc",  # Higher better
        "ensino_fundamental",  # Higher better
        "duration_to_school_min_by_foot",  # Lower better
        "schools_within_15min_travel_time_car",  # Higher better
    ]
    # A lower duration to school is considered positive, we need to invert the values of this feature
    hexs["duration_to_school_min_by_foot"] = hexs["duration_to_school_min_by_foot"] * -1
    access_weights = [0.2, 0.2, 0.2, 0.2, 0.1, 0.1]

    capacity_features = [
        "students_per_professor_FUND",
        "students_per_class_FUND",
        "IED_NIV_4_FUND",
        "IED_NIV_5_FUND",
        "IED_NIV_6_FUND",
    ]
    capacity_weights = [0.2, 0.2, 0.2, 0.2, 0.2]

    # High number of students per professor or class and higher percentage of professors in effort levels 4, 5 and 6 are considered negative
    # Since to consider the capacity of the schools, we want to consider the opposite of the values of these features
    # To do this we will multiply these features by -1, this will make high values of the final score to be considered as good capacity and low values as bad capacity
    start = time.time()
    hexs[capacity_features] = hexs[capacity_features] * -1
    print(f"Capacity features inverted in {time.time() - start:.2f} seconds")

    microregions = gpd.read_parquet("outputs/para_micro_regions.parquets")
    microregions_sample = microregions.sample(5)

    for index, microregion in tqdm(microregions_sample.iterrows()):
        microregion_hexs = hexs.clip(box(*microregion.geometry.bounds).buffer(0.005))

        # Perform hotspot analysis
        start = time.time()
        access_score, access_gi, access_psim = h3_hotspot_analysis(
            microregion_hexs, access_features, access_weights
        )
        print(f"Access hotspot analysis performed in {time.time() - start:.2f} seconds")

        start = time.time()
        capacity_score, capacity_gi, capacity_psim = h3_hotspot_analysis(
            microregion_hexs, capacity_features, capacity_weights
        )
        print(
            f"Capacity hotspot analysis performed in {time.time() - start:.2f} seconds"
        )

        # Create clusters
        pvalue = 0.05
        start = time.time()
        clusters = h3_scores_clusters(
            {"score": access_score, "gi": access_gi, "psim": access_psim},
            {"score": capacity_score, "gi": capacity_gi, "psim": capacity_psim},
            microregion_hexs,
            pvalue,  # significance level
        )
        microregion_hexs["clusters"] = clusters
        print(f"Clusters created in {time.time() - start:.2f} seconds")

        # Plot clusters
        start = time.time()

        fig, axes = plt.subplots(3, 2, figsize=(10, 10), sharex=True, sharey=True)

        # Plot access score in the first element of the first row
        microregion_hexs.plot(
            column=access_score,
            ax=axes[0, 0],
            legend=True,
            cmap="magma",
            vmin=0,
            vmax=1,
        )
        axes[0, 0].set_title("Access Index")

        # Plot access gi with p_sim > .5 in the second element of the first row
        microregion_hexs[access_psim < pvalue].plot(
            column=access_gi[access_psim < pvalue],
            ax=axes[0, 1],
            legend=True,
            cmap="RdYlBu_r",
            vmin=-3,
            vmax=3,
        )
        axes[0, 1].set_title("Access Hot/Cold Spots")

        # Plot capacity score in the first element of the second row
        microregion_hexs.plot(
            column=capacity_score,
            ax=axes[1, 0],
            legend=True,
            cmap="plasma",
            vmin=0,
            # vmax=1,
        )
        axes[1, 0].set_title("Capacity Index")

        # Plot capacity gi with p_sim > .5 in the second element of the second row
        microregion_hexs[access_psim < pvalue].plot(
            column=capacity_gi[access_psim < pvalue],
            ax=axes[1, 1],
            legend=True,
            cmap="RdYlBu_r",
            vmin=-3,
            vmax=3,
        )
        axes[1, 1].set_title("Capacity Hot/Cold Spots")

        # Plot clusters in the first element of the third row
        cluster_counts = microregion_hexs["clusters"].value_counts()
        cluster_counts = (
            cluster_counts.reindex(["HH", "HL", "LH", "LL", "N"]).fillna(0).astype(int)
        )
        microregion_hexs.plot(
            column="clusters",
            ax=axes[2, 0],
            categories=["HH", "HL", "LH", "LL", "N"],
            legend=True,
            categorical=True,
            cmap=mcolors.ListedColormap(
                ["yellowgreen", "gold", "orange", "red", "lightgray"]
            ),
            legend_kwds={
                "loc": "upper left",
                "bbox_to_anchor": (1.3, 1),
                "title": "Access - Capacity (hex count)",
                "labels": [
                    f"High - High ({cluster_counts['HH']})",
                    f"High - Low ({cluster_counts['HL']})",
                    f"Low  - High ({cluster_counts['LH']})",
                    f"Low  - Low ({cluster_counts['LL']})",
                    f"Non Significant ({cluster_counts['N']})",
                ],
            },
        )
        axes[2, 0].set_title("Clusters")

        # Change legend point markers to squares
        cluster_legends = axes[2, 0].get_legend()
        for ea in cluster_legends.legendHandles:
            ea.set_marker("s")

        # Remove the last element
        axes[2, 1].remove()

        # Add basemap
        for ax in axes.flatten():
            gpd.GeoSeries(microregion.geometry).plot(
                ax=ax, color="none", edgecolor="red", linewidth=0.5
            )
            ax.set_axis_off()
            ctx.add_basemap(
                ax, crs=microregion_hexs.crs, source=ctx.providers.CartoDB.Positron
            )

        plt.suptitle(f"{microregion['name_micro']}, {microregion['abbrev_state']}")

        plt.tight_layout()

        plt.show()

        print(f"Plot created in {time.time() - start:.2f} seconds")
