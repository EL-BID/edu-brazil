access_var_labels = {
    "pop_6_14_years_adj": "Population Ages 6-14",
    "income_pc": "Avg Income Per Cápita (R$)",
    "ensino_fundamental": "Schools - Ensino Fundamental",
    "duration_to_school_min_by_foot": "Travel time to the nearest school by foot",
    "duration_to_school_min_by_car": "Travel time to the nearest school by car",
    "schools_within_15min_travel_time_foot": "Schools at <15 minutes by foot",
    "schools_within_30min_travel_time_foot": "Schools at <30 minutes by foot",
    "schools_within_15min_travel_time_car": "Schools at <15 minutes by car",
    "schools_within_30min_travel_time_car": "Schools at <30 minutes by car",
}

capacity_var_labels = {
    "students_per_professor_FUND": "Average Students per Teacher",
    "students_per_class_FUND": "Average Students per Class (calc.)",
    "MAT_FUND": "Average Students per Class (given)",
    "IED_NIV": "Perc. Teachers with effort indicator",
    # "IED_NIV_1_FUND": "Perc. Teachers with effort indicator - Level 1",
    # "IED_NIV_2_FUND": "Perc. Teachers with effort indicator - Level 2",
    # "IED_NIV_3_FUND": "Perc. Teachers with effort indicator - Level 3",
    # "IED_NIV_4_FUND": "Perc. Teachers with effort indicator - Level 4",
    # "IED_NIV_5_FUND": "Perc. Teachers with effort indicator - Level 5",
    # "IED_NIV_6_FUND": "Perc. Teachers with effort indicator - Level 6",
}


column_labels = {
    "duration_to_school_min_by_foot_cat": "Travel time to the nearest school by foot",
    "duration_to_school_min_by_car_cat": "Travel time to the nearest school by car",
    "population_2020": "Population All Ages",
    "pop_6_14_years_adj": "Population Ages 6-14",
    "income_pc": "Avg Income Per Cápita (R$)",
    "territory type": "Territory Type",
    "ensino_fundamental": "Schools - Ensino Fundamental",
    "duration_to_school_min_by_foot": "Travel time to the nearest school by foot",
    "duration_to_school_min_by_car": "Travel time to the nearest school by car",
    "schools_within_15min_travel_time_foot": "Schools at <15 minutes by foot",
    "schools_within_30min_travel_time_foot": "Schools at <30 minutes by foot",
    "schools_within_15min_travel_time_car": "Schools at <15 minutes by car",
    "schools_within_30min_travel_time_car": "Schools at <30 minutes by car",
    "students_per_professor_FUND": "Average Students per Teacher",
    "students_per_class_FUND": "Average Students per Class (calc.)",
    "MAT_FUND": "Average Students per Class (given)",
    "IED_NIV_1_FUND": "(%) Teachers Effort indicator - Level 1",
    "IED_NIV_2_FUND": "(%) Teachers Effort indicator - Level 2",
    "IED_NIV_3_FUND": "(%) Teachers Effort indicator - Level 3",
    "IED_NIV_4_FUND": "(%) Teachers Effort indicator - Level 4",
    "IED_NIV_5_FUND": "(%) Teachers Effort indicator - Level 5",
    "IED_NIV_6_FUND": "(%) Teachers Effort indicator - Level 6",
}

color_variable_options = [
    (
        "Sociodemographic",
        [
            "population_2020",
            "pop_6_14_years_adj",
            "income_pc",
            "ensino_fundamental",
            "territory type",
        ],
    ),
    (
        "Schools Capacity",
        [
            "students_per_professor_FUND",
            "students_per_class_FUND",
            "MAT_FUND",
            "IED_NIV_1_FUND",
            "IED_NIV_2_FUND",
            "IED_NIV_3_FUND",
            "IED_NIV_4_FUND",
            "IED_NIV_5_FUND",
            "IED_NIV_6_FUND",
        ],
    ),
    (
        "Accessibility",
        [
            "duration_to_school_min_by_foot_cat",
            "duration_to_school_min_by_car_cat",
            "schools_within_15min_travel_time_foot",
            "schools_within_30min_travel_time_foot",
            "schools_within_15min_travel_time_car",
            "schools_within_30min_travel_time_car",
        ],
    ),
]


height_variable_options = [
    (
        "Sociodemographic",
        ["population_2020", "pop_6_14_years_adj", "income_pc", "ensino_fundamental"],
    ),
    (
        "Schools Capacity",
        [
            "students_per_professor_FUND",
            "students_per_class_FUND",
            "MAT_FUND",
            "IED_NIV_1_FUND",
            "IED_NIV_2_FUND",
            "IED_NIV_3_FUND",
            "IED_NIV_4_FUND",
            "IED_NIV_5_FUND",
            "IED_NIV_6_FUND",
        ],
    ),
    (
        "Accessibility",
        [
            "duration_to_school_min_by_foot",
            "duration_to_school_min_by_car",
            "schools_within_15min_travel_time_foot",
            "schools_within_30min_travel_time_foot",
            "schools_within_15min_travel_time_car",
            "schools_within_30min_travel_time_car",
        ],
    ),
]
