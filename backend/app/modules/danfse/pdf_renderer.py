"""Renderizador nativo de PDF binário (application/pdf) do DANFSe v2.0 + QR Code.

Port estrutural inspirado no layout oficial NT 008 SE/CGNFSE (`ADR003`) usando
ReportLab puro e QR Code vetorial (`QrCodeWidget`), sem dependências externas
de sistema (Cairo/GTK).
"""

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from .domain import DanfsePdfDocument, formatar_moeda_br
from .pdf_primitives import (
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_INK,
    COLOR_MUTED,
    COLOR_SOFT_BG,
    COLOR_WARNING,
    STYLE_SMALL,
    draw_cell,
    draw_paragraph_box,
    draw_qr_code,
    draw_section_header,
    draw_watermark,
)


def _render_header(c: Canvas, doc: DanfsePdfDocument, margin: float, y: float, content_w: float) -> float:
    header_h = 34 * mm
    qr_col_w = 34 * mm
    left_w = content_w - qr_col_w

    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.8)
    c.rect(margin, y - header_h, content_w, header_h, stroke=1, fill=0)
    c.line(margin + left_w, y, margin + left_w, y - header_h)

    title_h = 13 * mm
    c.setFillColor(COLOR_SOFT_BG)
    c.rect(margin, y - title_h, left_w, title_h, stroke=1, fill=1)

    c.setFillColor(COLOR_ACCENT)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(margin + 3 * mm, y - 5.8 * mm, "DANFSe v2.0")
    c.setFillColor(COLOR_INK)
    c.setFont("Helvetica-Bold", 9.0)
    c.drawString(margin + 33 * mm, y - 5.8 * mm, "Documento Auxiliar da NFS-e")
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.8)
    c.drawString(
        margin + 3 * mm,
        y - 10.6 * mm,
        "Padrão Nacional NFS-e • Reforma Tributária do Consumo (IBS / CBS — LC 214/2025)",
    )

    if doc.sem_validade_juridica:
        c.setFillColor(COLOR_WARNING)
        c.setFont("Helvetica-Bold", 7.0)
        c.drawRightString(margin + left_w - 2.5 * mm, y - 5.6 * mm, "NFS-e SEM VALIDADE JURÍDICA")

    row1_y = y - title_h
    row_h = (header_h - title_h) / 2
    draw_cell(c, margin, row1_y, left_w * 0.30, row_h, "NÚMERO DA NFS-E", doc.numero_nfse, bold_value=True)
    draw_cell(c, margin + left_w * 0.30, row1_y, left_w * 0.24, row_h, "COMPETÊNCIA DA NFS-E", doc.competencia)
    draw_cell(
        c,
        margin + left_w * 0.54,
        row1_y,
        left_w * 0.46,
        row_h,
        "DATA E HORA DA EMISSÃO DA NFS-E",
        doc.data_hora_emissao,
    )

    row2_y = row1_y - row_h
    draw_cell(c, margin, row2_y, left_w * 0.66, row_h, "CHAVE DE ACESSO DA NFS-E", doc.chave_acesso, bold_value=True)
    draw_cell(
        c,
        margin + left_w * 0.66,
        row2_y,
        left_w * 0.34,
        row_h,
        "SITUAÇÃO DA NFS-e",
        doc.situacao_texto,
        bold_value=True,
    )

    qr_size = 24 * mm
    qr_x = margin + left_w + (qr_col_w - qr_size) / 2
    draw_qr_code(c, doc.qrcode_url, qr_x, y - 25.5 * mm, qr_size)
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 5.2)
    qr_cx = margin + left_w + qr_col_w / 2
    c.drawCentredString(qr_cx, y - 28.4 * mm, "Autenticidade via QR Code")
    c.drawCentredString(qr_cx, y - 30.8 * mm, "ou portal nacional da NFS-e")
    c.drawCentredString(qr_cx, y - 33.0 * mm, "www.nfse.gov.br")
    return y - header_h - 2.5 * mm


def _render_party_section(
    c: Canvas,
    title: str,
    nome: str,
    documento: str,
    endereco: str,
    municipio: str,
    margin: float,
    y: float,
    content_w: float,
) -> float:
    r_h = 9.5 * mm
    y = draw_section_header(c, margin, y, content_w, title)
    draw_cell(c, margin, y, content_w * 0.62, r_h, "Nome / Nome Empresarial", nome, bold_value=True)
    draw_cell(c, margin + content_w * 0.62, y, content_w * 0.38, r_h, "CNPJ / CPF / NIF", documento, bold_value=True)
    y -= r_h
    draw_cell(c, margin, y, content_w * 0.62, r_h, "Endereço", endereco)
    draw_cell(c, margin + content_w * 0.62, y, content_w * 0.38, r_h, "Município / Sigla UF", municipio)
    return y - r_h - 2.5 * mm


def _render_canhoto(c: Canvas, doc: DanfsePdfDocument, margin: float, content_w: float) -> None:
    canhoto_y = margin + 22 * mm
    c.setStrokeColor(COLOR_BORDER)
    c.setDash(3, 2)
    c.line(margin, canhoto_y + 2.5 * mm, margin + content_w, canhoto_y + 2.5 * mm)
    c.setDash()

    c_h = 15 * mm
    draw_cell(c, margin, canhoto_y, content_w * 0.22, c_h, "DATA CIENTIFICAÇÃO:", "____/____/________")
    draw_cell(c, margin + content_w * 0.22, canhoto_y, content_w * 0.42, c_h, "IDENTIFICAÇÃO E ASSINATURA", "")
    draw_cell(
        c,
        margin + content_w * 0.64,
        canhoto_y,
        content_w * 0.36,
        c_h,
        "Nº NFS-e / CHAVE NFS-e",
        f"Nº {doc.numero_nfse} | {doc.chave_acesso[:22]}",
        bold_value=True,
    )

    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.2)
    c.drawString(margin, margin + 2.0 * mm, f"Consulta pública: {doc.qrcode_url}")
    c.drawRightString(margin + content_w, margin + 2.0 * mm, "Calculadora RTC RFB Free Suite PY • DANFSe v2.0")


def renderizar_danfse_pdf(doc: DanfsePdfDocument) -> bytes:
    """Renderiza um `DanfsePdfDocument` em PDF binário A4 com QR Code vetorial."""
    buffer = BytesIO()
    page_w, page_h = A4
    margin = 12 * mm
    content_w = page_w - 2 * margin
    r_h = 9.5 * mm
    col_w = content_w / 4

    c = Canvas(buffer, pagesize=A4)
    c.setTitle(f"DANFSe v2.0 - NFS-e {doc.numero_nfse}")
    c.setAuthor("Calculadora RTC RFB Free Suite PY")
    c.setSubject(f"Documento Auxiliar da NFS-e - Chave {doc.chave_acesso}")

    y = _render_header(c, doc, margin, page_h - margin, content_w)
    y = _render_party_section(
        c,
        "PRESTADOR / FORNECEDOR",
        doc.prestador_nome,
        doc.prestador_documento,
        doc.prestador_endereco,
        doc.prestador_municipio,
        margin,
        y,
        content_w,
    )
    y = _render_party_section(
        c,
        "TOMADOR / ADQUIRENTE",
        doc.tomador_nome,
        doc.tomador_documento,
        doc.tomador_endereco,
        doc.tomador_municipio,
        margin,
        y,
        content_w,
    )

    # Serviço Prestado
    y = draw_section_header(c, margin, y, content_w, "SERVIÇO PRESTADO")
    draw_cell(c, margin, y, content_w * 0.50, r_h, "Local da Prestação / Sigla UF", doc.local_prestacao)
    draw_cell(
        c,
        margin + content_w * 0.50,
        y,
        content_w * 0.50,
        r_h,
        "Código de Tributação Nacional / NBS",
        doc.codigo_tributacao,
    )
    y = draw_paragraph_box(
        c,
        margin,
        y - r_h,
        content_w,
        min_h=22 * mm,
        max_h=46 * mm,
        label="Descrição do Serviço",
        text=doc.discriminacao_servico,
    ) - 2.5 * mm

    # Tributação IBS / CBS
    y = draw_section_header(c, margin, y, content_w, "TRIBUTAÇÃO IBS / CBS (REFORMA TRIBUTÁRIA — LC 214/2025)")
    draw_cell(c, margin, y, col_w, r_h, "CST / cClassTrib", doc.cst_cclasstrib)
    draw_cell(
        c, margin + col_w, y, col_w, r_h, "Valor Total Apurado - IBS",
        formatar_moeda_br(doc.valor_ibs), bold_value=True, align_right=True,
    )
    draw_cell(
        c, margin + col_w * 2, y, col_w, r_h, "Valor Total Apurado - CBS",
        formatar_moeda_br(doc.valor_cbs), bold_value=True, align_right=True,
    )
    draw_cell(
        c, margin + col_w * 3, y, col_w, r_h, "Total do IBS/CBS",
        formatar_moeda_br(doc.valor_total_ibs_cbs), bold_value=True, align_right=True, fill_color=COLOR_SOFT_BG,
    )
    y -= r_h + 2.5 * mm

    # Valor Total da NFS-e
    y = draw_section_header(c, margin, y, content_w, "VALOR TOTAL DA NFS-E")
    t_h = 11.0 * mm
    draw_cell(
        c, margin, y, col_w, t_h, "VALOR DA OPERAÇÃO / SERVIÇO",
        formatar_moeda_br(doc.valor_servicos), bold_value=True, align_right=True,
    )
    draw_cell(
        c, margin + col_w, y, col_w, t_h, "TOTAL DO IBS/CBS",
        formatar_moeda_br(doc.valor_total_ibs_cbs), bold_value=True, align_right=True,
    )
    draw_cell(
        c, margin + col_w * 2, y, col_w, t_h, "VALOR LÍQUIDO DA NFS-e",
        formatar_moeda_br(doc.valor_liquido_nota), bold_value=True, align_right=True,
    )
    draw_cell(
        c, margin + col_w * 3, y, col_w, t_h, "VALOR LÍQUIDO + IBS/CBS",
        formatar_moeda_br(doc.valor_liquido_com_rtc), bold_value=True, align_right=True, fill_color=COLOR_SOFT_BG,
    )
    y -= t_h + 2.5 * mm

    # Informações Complementares
    y = draw_section_header(c, margin, y, content_w, "INFORMAÇÕES COMPLEMENTARES")
    draw_paragraph_box(
        c,
        margin,
        y,
        content_w,
        min_h=16 * mm,
        max_h=30 * mm,
        label="Observações e Autenticidade",
        text=doc.informacoes_complementares,
        style=STYLE_SMALL,
    )

    _render_canhoto(c, doc, margin, content_w)
    draw_watermark(c, page_w, page_h, doc.marca_dagua)

    c.showPage()
    c.save()
    return buffer.getvalue()
