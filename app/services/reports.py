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
from matplotlib.font_manager import FontProperties
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from app.data_store import MAP_PREVIEW, DataStore
from app.schemas import ExploreResponse, Panel

CHART_LOCK = Lock()
PAGE_WIDTH = A4[0] - 32 * mm

# Bundled fonts keep the exported report readable without a network request.
FONT_DIR = Path(__file__).resolve().parents[2] / "assets/fonts/dm-sans"
pdfmetrics.registerFont(TTFont("AgroSans", str(FONT_DIR / "DMSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("AgroSans-Bold", str(FONT_DIR / "DMSans-Bold.ttf")))
pdfmetrics.registerFontFamily("AgroSans", normal="AgroSans", bold="AgroSans-Bold")
CHART_FONT = FontProperties(fname=FONT_DIR / "DMSans-Regular.ttf")
CHART_BOLD = FontProperties(fname=FONT_DIR / "DMSans-Bold.ttf")


def paragraph(text, style):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def display_unit(unit):
    return {"dimensionless_index": "/ 1", "degC": "°C"}.get(unit, unit)


def statistic_label(item):
    if item.unit == "dimensionless_index":
        labels = {"mean": "average", "min": "lowest day", "max": "highest day"}
        name = item.label.split(":")[0]
        return f"{name}: {labels.get(item.aggregation, item.aggregation)}"
    return item.label


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
        axis.set_title(f"{panel.title} - {location_name}", fontproperties=CHART_BOLD, fontsize=11)
        axis.set_ylabel(panel.y_axis_label.replace("degC", "°C"), fontproperties=CHART_FONT, fontsize=9)
        axis.set_xlabel("Date (UTC) - selected days in each period", fontproperties=CHART_FONT, fontsize=8)
        locator = AutoDateLocator(minticks=3, maxticks=7)
        axis.xaxis.set_major_locator(locator)
        axis.xaxis.set_major_formatter(ConciseDateFormatter(locator))
        axis.tick_params(labelsize=8)
        for label in [*axis.get_xticklabels(), *axis.get_yticklabels(), axis.xaxis.get_offset_text()]:
            label.set_fontproperties(CHART_FONT)
            label.set_fontsize(8)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color="#dce3d8", linewidth=0.6)
        if panel.category == "soil_wetness":
            axis.set_ylim(0, 1)
        if len(visible) > 1:
            legend_font = CHART_FONT.copy()
            legend_font.set_size(8)
            axis.legend(frameon=False, prop=legend_font, loc="best")
        buffer = BytesIO()
        figure.savefig(buffer, format="png", dpi=150)
        figure.clear()
        buffer.seek(0)
        return buffer


def table(rows, widths, styles):
    cells = [[paragraph(cell, styles["TableHead"] if index == 0 else styles["TableBody"])
              for cell in row] for index, row in enumerate(rows)]
    result = LongTable(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#153329")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6ed")]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#91a695")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
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
        topMargin=15 * mm, bottomMargin=18 * mm, title="Agro Field historical report", author="Agro Field",
    )
    styles = getSampleStyleSheet()
    for name, style in styles.byName.items():
        is_heading = name.startswith("Heading") or name == "Title"
        style.fontName = "AgroSans-Bold" if is_heading else "AgroSans"
    styles["BodyText"].fontSize = 10
    styles["BodyText"].leading = 14
    styles["BodyText"].spaceAfter = 6
    styles["Title"].fontSize = 28
    styles["Title"].leading = 34
    styles["Title"].textColor = colors.HexColor("#153329")
    for name in ["Heading2", "Heading3"]:
        styles[name].textColor = colors.HexColor("#245e3a")
        styles[name].keepWithNext = True
        styles[name].spaceBefore = 14
        styles[name].spaceAfter = 8
    styles.add(ParagraphStyle("TableBody", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=0))
    styles.add(ParagraphStyle("TableHead", parent=styles["TableBody"], fontName="AgroSans-Bold", textColor=colors.white))
    story = [paragraph("Agro Field", styles["Title"])]
    location = result.location
    selection = result.request
    heading = f"{location.name}\n{selection.start_date} to {selection.end_date}"
    story.append(paragraph(heading, styles["Heading2"]))
    info = (
        f"Historical data, {selection.interval} view. Coordinates: {location.latitude}, {location.longitude}. "
        "These are gridded point samples, not district averages or farm observations."
    )
    story.append(paragraph(info, styles["BodyText"]))
    story.append(paragraph("Selected-period statistics", styles["Heading2"]))
    rows = [["Measure", "Value", "Days present"]]
    for item in result.statistics:
        value = "Unavailable" if item.value is None else f"{item.value:,.3f} {display_unit(item.unit)}"
        if item.date:
            value += f"\n{item.date.strftime('%d %b %Y')}"
        rows.append([statistic_label(item), value, f"{item.valid_days} / {item.expected_days}"])
    story.append(table(rows, [PAGE_WIDTH * 0.4, PAGE_WIDTH * 0.38, PAGE_WIDTH * 0.22], styles))
    story.append(paragraph("Days present means valid daily records out of selected calendar days. If an extreme repeats, its first date is shown. Wetness uses a 0-1 model index, not a percentage or a soil fertility test.", styles["BodyText"]))
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
        story.append(paragraph(item.text.replace(" degC", " °C"), styles["BodyText"]))
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
        story.append(PageBreak())
        add_rotation(story, rotation, styles)
    story.append(PageBreak())
    story.append(paragraph("Limitations and sources", styles["Heading2"]))
    for warning in result.warnings:
        story.append(paragraph(warning.message, styles["BodyText"]))
    sources = {source.source_id: source for source in result.sources}
    if rotation is not None:
        sources.update({source.source_id: source for source in rotation.sources})
    for source in sources.values():
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
    story.append(paragraph("Rotation comparison", styles["Heading2"]))
    status = rotation.status.replace("_", " ")
    priority = rotation.priority.replace("_", " ")
    story.append(paragraph(f"Assessment status: {status}. Priority: {priority}.", styles["BodyText"]))
    if rotation.status == "reference_only":
        story.append(paragraph("Reference-based options for local review, not validated rotation recommendations. Only the supplied local files were used.", styles["BodyText"]))
    for strategy in [rotation.baseline, *rotation.alternatives]:
        story.append(paragraph(strategy.strategy_id.replace("_", " ").title(), styles["Heading3"]))
        sequence = [" + ".join(season.crops) or "Fallow" for season in strategy.sequence]
        story.append(paragraph(" -> ".join(sequence), styles["BodyText"]))
        if strategy.strategy_id != "existing_rotation":
            for text in [*strategy.explanations, *(strategy.tradeoffs or [])]:
                story.append(paragraph(text, styles["BodyText"]))
        rows = [["Criterion", "Result", "Explanation"]]
        rows.extend([[item.criterion.replace("_", " "), item.status, item.reason] for item in strategy.checks])
        story.append(table(rows, [PAGE_WIDTH * 0.26, PAGE_WIDTH * 0.13, PAGE_WIDTH * 0.61], styles))
    for slot in rotation.unfilled_alternative_slots:
        label = slot.strategy_id.replace("_", " ").title()
        story.append(paragraph(f"{label}: {slot.reason}", styles["BodyText"]))
    story.append(paragraph("Information still needed", styles["Heading3"]))
    for missing in rotation.missing_information:
        story.append(paragraph(missing, styles["BodyText"]))
    for warning in rotation.warnings:
        story.append(paragraph(warning.message, styles["BodyText"]))
    versions = f"Assessment: {rotation.assessment_id}. Rules: {rotation.rules_version}."
    story.append(paragraph(versions, styles["BodyText"]))
