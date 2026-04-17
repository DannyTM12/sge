"""Generador de boleta académica en PDF usando reportlab."""

from datetime import datetime
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.alumno import MiMateriaRead


async def generar_boleta(
    alumno_datos: dict,
    institucion_datos: dict,
    ciclo_datos: dict,
    grupo_nombre: str,
    materias: list[MiMateriaRead],
    folio: str,
) -> bytes:
    """
    Genera el PDF de boleta y devuelve los bytes.
    No incluye CURP en el documento — dato sensible innecesario (LFPDPPP).
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    center = ParagraphStyle("center", parent=styles["Normal"], alignment=TA_CENTER)
    right = ParagraphStyle("right", parent=styles["Normal"], alignment=TA_RIGHT)
    bold_center = ParagraphStyle(
        "bold_center", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=13
    )
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8)

    elements = []

    # ── Encabezado institución ────────────────────────────────────────────────
    elements.append(Paragraph(f"<b>{institucion_datos.get('nombre', '')}</b>", bold_center))
    if institucion_datos.get("direccion"):
        elements.append(Paragraph(institucion_datos["direccion"], center))
    if institucion_datos.get("telefono"):
        elements.append(Paragraph(f"Tel: {institucion_datos['telefono']}", center))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(f"<b>Ciclo Escolar: {ciclo_datos['nombre']}</b>", center))
    elements.append(Spacer(1, 0.15 * inch))

    # ── Datos del alumno (sin CURP) ───────────────────────────────────────────
    alumno_table_data = [
        ["Alumno:", alumno_datos.get("nombre_completo", "")],
        ["Matrícula:", alumno_datos.get("matricula") or "—"],
        ["Grupo:", grupo_nombre],
    ]
    alumno_table = Table(alumno_table_data, colWidths=[1.2 * inch, 5.0 * inch])
    alumno_table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
    )
    elements.append(alumno_table)
    elements.append(Spacer(1, 0.2 * inch))

    # ── Tabla de calificaciones ───────────────────────────────────────────────
    max_parciales = max((m.num_parciales for m in materias), default=3)
    header = (
        ["Materia", "Clave"]
        + [f"P{i + 1}" for i in range(max_parciales)]
        + ["Calculada", "Final"]
    )

    table_data = [header]
    has_modificadas = False

    for materia in materias:
        row = [materia.materia_nombre, materia.clave or "—"]
        for i in range(max_parciales):
            if i < len(materia.parciales):
                p = materia.parciales[i]
                if p.esta_publicada and p.calificacion is not None:
                    row.append(str(p.calificacion))
                else:
                    row.append("—")
            else:
                row.append("—")

        row.append(str(materia.calificacion_calculada) if materia.calificacion_calculada is not None else "—")

        final_str = str(materia.calificacion_final) if materia.calificacion_final is not None else "—"
        if materia.fue_modificada_manualmente:
            final_str += " *"
            has_modificadas = True
        row.append(final_str)
        table_data.append(row)

    page_width = letter[0] - 1.5 * inch
    parcial_col_w = 0.55 * inch
    fixed_w = [2.3 * inch, 0.7 * inch] + [parcial_col_w] * max_parciales + [0.75 * inch, 0.75 * inch]
    total = sum(fixed_w)
    if total > page_width:
        factor = page_width / total
        col_widths = [w * factor for w in fixed_w]
    else:
        col_widths = fixed_w

    cal_table = Table(table_data, colWidths=col_widths)
    cal_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    elements.append(cal_table)
    elements.append(Spacer(1, 0.15 * inch))

    # ── Promedio general ──────────────────────────────────────────────────────
    califs_finales = [m.calificacion_final for m in materias if m.calificacion_final is not None]
    if califs_finales:
        promedio = sum(califs_finales) / len(califs_finales)
        elements.append(Paragraph(f"<b>Promedio general: {promedio:.2f}</b>", right))
        elements.append(Spacer(1, 0.1 * inch))

    # ── Nota de calificaciones ajustadas ─────────────────────────────────────
    if has_modificadas:
        elements.append(Paragraph("* Calificación ajustada por administración", small))
        elements.append(Spacer(1, 0.05 * inch))

    # ── Pie: folio y fecha ────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.2 * inch))
    fecha_emision = datetime.now().strftime("%d/%m/%Y %H:%M")
    elements.append(
        Paragraph(f"Folio: {folio}  |  Fecha de emisión: {fecha_emision}", center)
    )

    def _add_watermark(canvas: Canvas, doc) -> None:  # noqa: ARG001
        canvas.saveState()
        canvas.setFont("Helvetica", 24)
        canvas.setFillColor(colors.Color(0.75, 0.75, 0.75, alpha=0.25))
        w, h = letter
        canvas.translate(w / 2, h / 2)
        canvas.rotate(42)
        canvas.drawCentredString(0, 0, "Documento informativo.")
        canvas.translate(0, -0.4 * inch)
        canvas.drawCentredString(0, 0, "No constituye documento oficial.")
        canvas.restoreState()

    doc.build(elements, onFirstPage=_add_watermark, onLaterPages=_add_watermark)
    return buffer.getvalue()
