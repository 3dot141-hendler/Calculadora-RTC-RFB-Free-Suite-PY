"""Primitivas vetoriais ReportLab reutilizáveis para o DANFSe v2.0."""

from xml.sax.saxutils import escape

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

COLOR_INK = colors.HexColor("#0f172a")
COLOR_MUTED = colors.HexColor("#475569")
COLOR_BORDER = colors.HexColor("#94a3b8")
COLOR_SECTION_BG = colors.HexColor("#e2e8f0")
COLOR_SOFT_BG = colors.HexColor("#f8fafc")
COLOR_ACCENT = colors.HexColor("#1d4ed8")
COLOR_WARNING = colors.HexColor("#b91c1c")

STYLE_BODY = ParagraphStyle(
    name="DanfseBody",
    fontName="Helvetica",
    fontSize=8.0,
    leading=10.5,
    textColor=COLOR_INK,
)
STYLE_SMALL = ParagraphStyle(
    name="DanfseSmall",
    fontName="Helvetica",
    fontSize=7.2,
    leading=9.4,
    textColor=COLOR_MUTED,
)


def draw_section_header(c: Canvas, x: float, y: float, w: float, title: str) -> float:
    """Desenha faixa cinza de título de seção e retorna o novo topo `y`."""
    h = 5.6 * mm
    c.setFillColor(COLOR_SECTION_BG)
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.6)
    c.rect(x, y - h, w, h, stroke=1, fill=1)
    c.setFillColor(COLOR_INK)
    c.setFont("Helvetica-Bold", 7.6)
    c.drawString(x + 2.2 * mm, y - h + 1.8 * mm, title)
    return y - h


def draw_cell(
    c: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    value: str,
    *,
    bold_value: bool = False,
    align_right: bool = False,
    fill_color: colors.Color | None = None,
) -> None:
    """Desenha célula com rótulo superior pequeno e valor inferior truncado com segurança."""
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    if fill_color is not None:
        c.setFillColor(fill_color)
        c.rect(x, y - h, w, h, stroke=1, fill=1)
    else:
        c.rect(x, y - h, w, h, stroke=1, fill=0)

    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.2)
    c.drawString(x + 1.8 * mm, y - 3.0 * mm, label[:68])

    c.setFillColor(COLOR_INK)
    c.setFont("Helvetica-Bold" if bold_value else "Helvetica", 8.0)
    clean_val = (value or "-").strip()
    max_chars = max(12, int(w / (1.85 * mm)))
    if len(clean_val) > max_chars:
        clean_val = clean_val[: max_chars - 1] + "…"

    if align_right:
        c.drawRightString(x + w - 1.8 * mm, y - h + 2.0 * mm, clean_val)
    else:
        c.drawString(x + 1.8 * mm, y - h + 2.0 * mm, clean_val)


def draw_paragraph_box(
    c: Canvas,
    x: float,
    y: float,
    w: float,
    min_h: float,
    max_h: float,
    label: str,
    text: str,
    style: ParagraphStyle = STYLE_BODY,
) -> float:
    """Desenha caixa multi-linha com escape seguro XML e retorna o novo topo `y`."""
    safe_text = escape((text or "-").strip()).replace("\n", "<br/>")
    para = Paragraph(safe_text, style)
    inner_w = w - 3.6 * mm
    _, para_h = para.wrap(inner_w, max_h - 5.5 * mm)
    box_h = min(max(min_h, para_h + 6.5 * mm), max_h)

    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y - box_h, w, box_h, stroke=1, fill=0)

    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.2)
    c.drawString(x + 1.8 * mm, y - 3.0 * mm, label)

    para.drawOn(c, x + 1.8 * mm, y - box_h + max(1.6 * mm, box_h - 4.5 * mm - para_h))
    return y - box_h


def draw_qr_code(c: Canvas, url: str, x: float, y_bottom: float, size: float) -> None:
    """Renderiza QR Code vetorial escalado com precisão dentro da caixa informada."""
    qr_widget = QrCodeWidget(url, barLevel="M")
    bounds = qr_widget.getBounds()
    qr_w = max(bounds[2] - bounds[0], 1.0)
    qr_h = max(bounds[3] - bounds[1], 1.0)
    drawing = Drawing(size, size, transform=[size / qr_w, 0, 0, size / qr_h, 0, 0])
    drawing.add(qr_widget)
    renderPDF.draw(drawing, c, x, y_bottom)


def draw_watermark(c: Canvas, page_w: float, page_h: float, texto: str) -> None:
    """Aplica marca d'água diagonal translúcida (CANCELADA / SUBSTITUÍDA)."""
    if not texto:
        return
    c.saveState()
    c.translate(page_w / 2, page_h / 2)
    c.rotate(38)
    c.setFillColor(colors.Color(0.75, 0.1, 0.1, alpha=0.16))
    c.setFont("Helvetica-Bold", 62)
    c.drawCentredString(0, 0, texto)
    c.restoreState()
