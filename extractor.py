import re
from datetime import datetime, timedelta

def normalizar_texto_mejorado(texto):
    texto = texto.lower()
    replacements = (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"))
    for a, b in replacements:
        texto = texto.replace(a, b)
    
    numeros = {
        "una": "1", "un": "1", "uno": "1", "dos": "2", "tres": "3", 
        "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7", 
        "ocho": "8", "nueve": "9", "diez": "10"
    }
    
    for palabra, digito in numeros.items():
        texto = re.sub(r'\b' + palabra + r'\b', digito, texto)
    
    terminos = {
        "habitacion": "hab", "habitaciones": "hab", 
        "piezas": "hab", "pieza": "hab", "matrimonial": "doble",
        "simple": "single", "sencilla": "single", "estandar": "standard"
    }
    
    for palabra, reemplazo in terminos.items():
        texto = re.sub(r'\b' + palabra + r'\b', reemplazo, texto)
        
    return texto

def extraer_fechas(texto):
    """Extrae fechas de check-in y check-out del texto"""
    resultado = {"check_in": None, "check_out": None}
    fecha_actual = datetime.now()
    
    # Fechas relativas comunes
    if "mañana" in texto or "manana" in texto:
        check_in = fecha_actual + timedelta(days=1)
        resultado['check_in'] = check_in.strftime('%Y-%m-%d')
        resultado['check_out'] = (check_in + timedelta(days=1)).strftime('%Y-%m-%d')
    elif "hoy" in texto:
        resultado['check_in'] = fecha_actual.strftime('%Y-%m-%d')
        resultado['check_out'] = (fecha_actual + timedelta(days=1)).strftime('%Y-%m-%d')
    elif "pasado mañana" in texto or "pasado manana" in texto:
        check_in = fecha_actual + timedelta(days=2)
        resultado['check_in'] = check_in.strftime('%Y-%m-%d')
        resultado['check_out'] = (check_in + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Buscar patrones de fecha: del X al Y
    rango_match = re.search(r'del\s+(\d+)\s+al\s+(\d+)', texto)
    if rango_match:
        dia_inicio = int(rango_match.group(1))
        dia_fin = int(rango_match.group(2))
        
        mes = fecha_actual.month
        año = fecha_actual.year
        
        if dia_inicio < fecha_actual.day:
            mes += 1
            if mes > 12:
                mes = 1
                año += 1
        
        resultado['check_in'] = f"{año}-{mes:02d}-{dia_inicio:02d}"
        resultado['check_out'] = f"{año}-{mes:02d}-{dia_fin:02d}"
    
    # Buscar fechas explícitas dd/mm
    fecha_match = re.search(r'(\d{1,2})[/-](\d{1,2})', texto)
    if fecha_match and not resultado['check_in']:
        dia = int(fecha_match.group(1))
        mes = int(fecha_match.group(2))
        
        año = fecha_actual.year
        if mes < fecha_actual.month or (mes == fecha_actual.month and dia < fecha_actual.day):
            año += 1
        
        resultado['check_in'] = f"{año}-{mes:02d}-{dia:02d}"
        resultado['check_out'] = f"{año}-{mes:02d}-{(dia + 1):02d}"
    
    return resultado

def extraer_habitaciones(texto):
    """Extrae información de habitaciones del texto"""
    resultado = {"cantidad_habitaciones": None, "tipo_habitaciones": None}
    
    # Patrón mejorado para detectar múltiples tipos de habitaciones
    # Ej: "1 doble y 2 estandar", "2 standard, 1 superior"
    patron_hab = r'(\d+)\s*(?:hab|habs|piezas?)?\s*(doble|single|standard|superior)'
    
    # Encontrar todas las coincidencias
    coincidencias = re.findall(patron_hab, texto)
    
    if coincidencias:
        habitaciones = []
        total = 0
        
        for cant_str, tipo in coincidencias:
            cantidad = int(cant_str)
            total += cantidad
            
            # Normalizar nombres para consistencia
            if tipo == "standard":
                tipo = "estandar"
            
            habitaciones.append(f"{cantidad} {tipo}")
        
        resultado['cantidad_habitaciones'] = str(total)
        resultado['tipo_habitaciones'] = ", ".join(habitaciones)
    else:
        # Buscar cantidad general de habitaciones
        match_gen = re.search(r'(\d+)\s*(?:hab|habitacion|habitaciones|pieza)', texto)
        if match_gen:
            cantidad = match_gen.group(1)
            resultado['cantidad_habitaciones'] = cantidad
            resultado['tipo_habitaciones'] = f"{cantidad} estandar"
    
    return resultado

def extraer_personas(texto):
    """Extrae cantidad de personas del texto"""
    resultado = {"cant_personas": None}
    
    # Patrones para buscar cantidad de personas
    patrones = [
        r'(?:somos|para|son)\s+(\d+)\s*(?:personas|adultos|pax)?',
        r'(\d+)\s+(?:personas|adultos|pax)',
        r'para\s+(\d+)\b'
    ]
    
    for patron in patrones:
        match = re.search(patron, texto)
        if match and match.group(1):
            resultado['cant_personas'] = match.group(1)
            break
    
    return resultado

def extraer_informacion_reserva(mensaje):
    """Extrae información de reserva del mensaje"""
    resultado = {
        "check_in": None, 
        "check_out": None,
        "cant_personas": None, 
        "cantidad_habitaciones": None, 
        "tipo_habitaciones": None
    }
    
    texto = normalizar_texto_mejorado(mensaje)
    
    # Extraer cada componente por separado
    fechas = extraer_fechas(texto)
    habitaciones = extraer_habitaciones(texto)
    personas = extraer_personas(texto)
    
    # Combinar resultados
    resultado.update(fechas)
    resultado.update(habitaciones)
    resultado.update(personas)
    
    # Lógica de fallback para cantidad de habitaciones
    if resultado['cantidad_habitaciones'] and resultado['cant_personas']:
        try:
            habs = int(resultado['cantidad_habitaciones'])
            pers = int(resultado['cant_personas'])
            
            # Si no hay tipo específico pero sí hay cantidad, asignar "estandar"
            if not resultado['tipo_habitaciones'] and habs > 0:
                resultado['tipo_habitaciones'] = f"{habs} estandar"
        except ValueError:
            pass
    
    return resultado