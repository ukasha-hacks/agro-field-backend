from app.schemas import Description, Statistic


def describe(statistics: list[Statistic]) -> list[Description]:
    metrics = {item.metric_id: item for item in statistics}
    templates = {
        "rainfall_total_mm": "Rainfall totalled {value:.2f} mm during the selected period.",
        "temperature_mean_c": "Mean air temperature was {value:.2f} degC during the selected period.",
        "surface_soil_wetness_mean": "Mean modelled surface wetness was {value:.3f} on the 0-1 index.",
        "root_zone_soil_wetness_mean": "Mean modelled root-zone wetness was {value:.3f} on the 0-1 index.",
    }
    descriptions = []
    for key, template in templates.items():
        if key not in metrics:
            continue
        item = metrics[key]
        if item.value is None:
            text = f"{item.label} is unavailable: {item.valid_days} of {item.expected_days} expected days have data."
        else:
            text = template.format(value=item.value)
        descriptions.append(Description(text=text, evidence_ids=[key]))
    return descriptions
