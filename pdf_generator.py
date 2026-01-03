from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime, timedelta
import io
import base64
import os
from config import HOTEL_INFO

def formatear_precio(precio):
    return f"${precio:,.0f}".replace(",", ".")

def generar_cotizacion_pdf(info_reserva, totales, cantidad_noches):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=40,
        bottomMargin=30,
    )
    
    elementos = []
    styles = getSampleStyleSheet()
    
    estilo_titulo_doc = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=20, alignment=TA_RIGHT, textColor=colors.black)
    estilo_hotel_nombre = ParagraphStyle('HotelName', parent=styles['Heading1'], fontSize=18, textColor=colors.black)
    estilo_label = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    estilo_valor = ParagraphStyle('Value', parent=styles['Normal'], fontSize=9)
    estilo_tabla_hdr = ParagraphStyle('TblHdr', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER)

    # Encabezado con logo
    logo_path = "logo.png" 
    
    col_izq = []
    if os.path.exists(logo_path):
        img = Image(logo_path, width=1.2*inch, height=1.2*inch)
        img.hAlign = 'LEFT'
        col_izq.append(img)
    else:
        col_izq.append(Paragraph(HOTEL_INFO['nombre'], estilo_hotel_nombre))

    header_data = [
        [col_izq, Paragraph("COTIZACIÓN", estilo_titulo_doc)]
    ]
    header_tab = Table(header_data, colWidths=[3.5*inch, 3*inch])
    header_tab.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elementos.append(header_tab)
    elementos.append(Spacer(1, 0.2*inch))
    
    # Info de control
    fecha_emision = datetime.now().strftime('%d.%m.%Y')
    fecha_validez = (datetime.now() + timedelta(days=2)).strftime('%d.%m.%Y')
    
    control_data = [
        [Paragraph("FECHA EMISIÓN", estilo_label), Paragraph(fecha_emision, estilo_valor)],
        [Paragraph("FECHA VALIDEZ", estilo_label), Paragraph(fecha_validez, estilo_valor)]
    ]
    control_tab = Table(control_data, colWidths=[1.5*inch, 1.2*inch], hAlign='RIGHT')
    control_tab.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey)
    ]))
    elementos.append(control_tab)
    elementos.append(Spacer(1, 0.3*inch))

    # Datos de estadía
    estadia_data = [
        [Paragraph("CHECK IN", estilo_label), info_reserva['check_in'], Paragraph("NOCHES", estilo_label), str(cantidad_noches)],
        [Paragraph("CHECK OUT", estilo_label), info_reserva['check_out'], Paragraph("HUÉSPEDES", estilo_label), str(info_reserva['cant_personas'])]
    ]
    estadia_tab = Table(estadia_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    estadia_tab.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ('BACKGROUND', (2,0), (2,-1), colors.whitesmoke),
    ]))
    elementos.append(estadia_tab)
    elementos.append(Spacer(1, 0.3*inch))

    # Tabla de cargos - AHORA LISTA TODAS LAS HABITACIONES
    tabla_header = [
        Paragraph("DESCRIPCIÓN", estilo_tabla_hdr), 
        Paragraph("CANT", estilo_tabla_hdr), 
        Paragraph("UNITARIO", estilo_tabla_hdr), 
        Paragraph("TOTAL", estilo_tabla_hdr)
    ]
    datos_items = [tabla_header]
    
    for hab in totales['habitaciones']:
        datos_items.append([
            hab['tipo'],
            str(hab['cantidad']),
            formatear_precio(hab['precio_noche']),
            formatear_precio(hab['total'])
        ])

    items_tab = Table(datos_items, colWidths=[3.2*inch, 0.8*inch, 1.2*inch, 1.3*inch])
    items_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.black),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
    ]))
    elementos.append(items_tab)

    # Totales
    totales_data = [
        ["", "NETO", formatear_precio(totales['total_neto'])],
        ["", "IVA (19%)", formatear_precio(totales['iva'])],
        ["", "TOTAL FINAL", formatear_precio(totales['total_bruto'])]
    ]
    totales_tab = Table(totales_data, colWidths=[3.7*inch, 1.5*inch, 1.3*inch])
    totales_tab.setStyle(TableStyle([
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (1,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (1,2), (2,2), colors.lightgrey),
    ]))
    elementos.append(totales_tab)
    
    # Pie de página
    elementos.append(Spacer(1, 0.5*inch))
    
    linea = Table([[""]], colWidths=[6.5*inch])
    linea.setStyle(TableStyle([('LINEABOVE', (0,0), (-1,0), 1, colors.black)]))
    elementos.append(linea)
    
    banco_y_terminos = f"""
    <b>DATOS DE PAGO:</b> {HOTEL_INFO['nombre']} | RUT: {HOTEL_INFO['rut']} | Banco de Chile | Cta: 2501678302<br/>
    <b>TÉRMINOS:</b> Cotización válida por 48 horas. Reserva requiere 100% de pago anticipado.
    """
    elementos.append(Paragraph(banco_y_terminos, estilo_valor))

    doc.build(elementos)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return base64.b64encode(pdf_bytes).decode('utf-8')