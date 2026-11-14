from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from app.data_store import MAP_PREVIEW, DataStore
from app.schemas import ExploreResponse, Panel

CHART_LOCK = Lock()
PAGE_WIDTH = A4[0] - 32 * mm

# Matplotlib already ships these fonts, so reports need no font download.
FONT_DIR = Path(matplotlib.get_data_path()) / "fonts/ttf"
pdfmetrics.registerFont(TTFont("AgroSans", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("AgroSans-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))


def paragraph(text, style):
    return Paragraph(escape(str(text)), style)


def render_chart(panel: Panel, location_name: str):
    with CHART_LOCK:
        figure = Figure(figsize=(8, 2.5), layout="constrained")
        FigureCanvasAgg(figure)
        axis = figure.subplots()
        palette = ["#26734d", "#456ca5"]
        visible = [series for series in panel.series if series.visible_by_default]
        for series, color in zip(visible, palette):
            dates = [point.period_start for point in series.points]
            values = [point.value for point in series.points]
            axis.plot(dates, values, color=color, label=series.label, linewidth=1.5, marker=".", markersize=3)
        axis.set_title(f"{panel.title} - {location_name}", fontsize=10)
        axis.set_ylabel(panel.y_axis_label, fontsize=8)
        axis.set_xlabel("Date (UTC); point values cover their stated periods", fontsize=8)
        locator = AutoDateLocator(minticks=3, maxticks=7)
        axis.xaxis.set_major_locator(locator)
        axis.xaxis.set_major_formatter(ConciseDateFormatter(locator))
        axis.tick_params(labelsize=8)
        axis.grid(axis="y", alpha=0.2)
        if panel.category == "soil_wetness":
            axis.set_ylim(0, 1)
        if len(visible) > 1:
            axis.legend(frameon=False, fontsize=8, loc="best")
        buffer = BytesIO()
        figure.savefig(buffer, format="png", dpi=150)
        figure.clear()
        buffer.seek(0)
        return buffer


def table(rows, widths, styles):
    cells = [[paragraph(cell, styles["BodyText"]) for cell in row] for row in rows]
    result = LongTable(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0e8")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#91a695")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return result


def add_footer(canvas, document):
    canvas.saveState()
    canvas.setFont("AgroSans", 8)
    canvas.drawString(16 * mm, 10 * mm, "Agro Field | Historical planning support")
    canvas.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def report_bytes(store: DataStore, result: ExploreResponse, rotation=None) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm,
        topMargin=15 * mm, bottomMargin=18 * mm, title="Agro Field historical report",
    )
    styles = getSampleStyleSheet()
    for name, style in styles.byName.items():
        is_heading = name.startswith("Heading") or name == "Title"
        style.fontName = "AgroSans-Bold" if is_heading else "AgroSans"
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    story = [paragraph("Agro Field", styles["Title"])]
    location = result.location
    selection = result.request
    heading = f"{location.name} | {selection.start_date} to {selection.end_date}"
    story.append(paragraph(heading, styles["Heading2"]))
    info = (
        f"Historical data, {selection.interval} view. Coordinates: {location.latitude}, {location.longitude}. "
        "These are gridded point samples, not district averages or farm observations."
    )
    story.append(paragraph(info, styles["BodyText"]))
    story.append(paragraph("Selected-period statistics", styles["Heading2"]))
    rows = [["Metric", "Value", "Valid / expected days"]]
    for item in result.statistics:
        value = "Unavailable" if item.value is None else f"{item.value:.3f} {item.unit}"
        if item.date:
            value += f" on {item.date} (earliest tie)"
        rows.append([item.label, value, f"{item.valid_days} / {item.expected_days}"])
    story.append(table(rows, [PAGE_WIDTH * 0.38, PAGE_WIDTH * 0.4, PAGE_WIDTH * 0.22], styles))
    story.append(paragraph("Historical graphs", styles["Heading2"]))
    partial = any(point.partial_calendar_month for panel in result.panels for series in panel.series for point in series.points)
    if partial:
        story.append(paragraph("Boundary months are partial. Their points contain only the selected days.", styles["BodyText"]))
    for panel in result.panels:
        chart = render_chart(panel, location.name)
        story.append(Image(chart, width=PAGE_WIDTH, height=PAGE_WIDTH * 2.5 / 8))
        story.append(Spacer(1, 4 * mm))
    story.append(paragraph("What the observations show", styles["Heading2"]))
    for item in result.descriptions:
        story.append(paragraph(item.text, styles["BodyText"]))
    map_items = [paragraph("Map reference", styles["Heading2"])]
    preview = store.root / MAP_PREVIEW
    if preview.is_file() and result.map_references:
        map_items.append(Image(str(preview), width=PAGE_WIDTH, height=PAGE_WIDTH * 0.8))
        caption = (
            f"Selected location: {location.name}. The reference image labels all four sample points. "
            "It does not add a new selection highlight or show the selected period's weather. "
            "FAO/IIASA GAEZ v4: maize soil/terrain suitability, rain-fed, low inputs; baseline 2010. "
            "The rectangle includes neighboring land. Source terms: CC-BY-NC-SA-4.0."
        )
        map_items.append(paragraph(caption, styles["BodyText"]))
    else:
        map_items.append(paragraph(
            f"Reference map unavailable. Selected coordinates: {location.latitude}, {location.longitude}.",
            styles["BodyText"],
        ))
    story.append(KeepTogether(map_items))
    if rotation is not None:
        add_rotation(story, rotation, styles)
    story.append(paragraph("Limitations and sources", styles["Heading2"]))
    for warning in result.warnings:
        story.append(paragraph(warning.message, styles["BodyText"]))
    for source in result.sources:
        text = f"{source.name}. {source.period}. {source.url} {source.limitations}"
        story.append(paragraph(text, styles["BodyText"]))
    generated = datetime.now(ZoneInfo("Africa/Kampala")).isoformat(timespec="seconds")
    versions = (
        f"Generated: {generated} (Africa/Kampala). Analysis: {result.analysis_id}. "
        f"Data: {result.data_version}. Methods: {result.methods_version}."
    )
    story.append(paragraph(versions, styles["BodyText"]))
    document.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    return buffer.getvalue()


def add_rotation(story, rotation, styles):
    # The comparison stage supplies this section once its contract is available.
    raise NotImplementedError("Rotation reports are not available at this stage")
