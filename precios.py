from config import PRECIOS_HABITACIONES

def parsear_tipos_habitaciones_corregido(tipo_habitaciones_str):
    """
    Parsea string de tipos de habitaciones, corrigiendo el problema de suma incorrecta.
    Ej: "1 doble, 2 estandar" -> [("Habitación Doble 2 Camas", 1), ("Habitación Estándar", 2)]
    """
    if not tipo_habitaciones_str:
        return []
    
    resultado = []
    
    # Dividir por comas, "y", "e"
    import re
    partes = re.split(r'[,;]|\s+y\s+|\s+e\s+', tipo_habitaciones_str.lower())
    
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        
        # Buscar patron "cantidad tipo"
        match = re.search(r'(\d+)\s+(doble|single|estandar|standard|superior)', parte)
        if match:
            cantidad = int(match.group(1))
            tipo_raw = match.group(2)
            
            # Normalizar tipo
            tipo_normalizado = normalizar_tipo_habitacion(tipo_raw)
            resultado.append((tipo_normalizado, cantidad))
    
    # Si no se encontraron, usar fallback
    if not resultado:
        # Intentar extraer solo cantidad
        match_cant = re.search(r'(\d+)', tipo_habitaciones_str)
        if match_cant:
            cantidad = int(match_cant.group(1))
            resultado.append(("Habitación Estándar", cantidad))
    
    return resultado

def normalizar_tipo_habitacion(tipo_str):
    """Normaliza nombres de tipos de habitación"""
    if not tipo_str:
        return 'Habitación Estándar'
    
    tipo_lower = tipo_str.lower().strip()
    tipo_lower = tipo_lower.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    
    if 'single' in tipo_lower or 'sencilla' in tipo_lower or 'simple' in tipo_lower:
        return 'Habitación Single'
    elif 'estandar' in tipo_lower or 'standard' in tipo_lower:
        return 'Habitación Estándar'
    elif 'superior' in tipo_lower or 'premium' in tipo_lower:
        return 'Habitación Superior'
    elif 'doble' in tipo_lower or 'matrimonial' in tipo_lower:
        return 'Habitación Doble 2 Camas'
    else:
        return 'Habitación Estándar'

def calcular_totales_corregido(tipo_habitaciones_str, cantidad_noches, precios):
    """
    Versión corregida que procesa correctamente múltiples tipos de habitaciones.
    """
    habitaciones_parseadas = parsear_tipos_habitaciones_corregido(tipo_habitaciones_str)
    
    if not habitaciones_parseadas:
        habitaciones_parseadas = [('Habitación Estándar', 1)]
    
    habitaciones_detalle = []
    total_neto = 0
    
    for tipo_normalizado, cantidad in habitaciones_parseadas:
        precio_noche = precios.get(tipo_normalizado, 50000)
        total_tipo = cantidad * cantidad_noches * precio_noche
        
        habitaciones_detalle.append({
            "tipo": tipo_normalizado,
            "cantidad": cantidad,
            "precio_noche": precio_noche,
            "total": total_tipo
        })
        
        total_neto += total_tipo
    
    iva = int(total_neto * 0.19)
    total_bruto = total_neto + iva
    
    return {
        "habitaciones": habitaciones_detalle,
        "total_neto": total_neto,
        "iva": iva,
        "total_bruto": total_bruto
    }

def formatear_precio(precio):
    return f"${precio:,.0f}".replace(",", ".")

# Mantener compatibilidad con el código existente
def parsear_tipos_habitaciones(tipo_habitaciones_str):
    return parsear_tipos_habitaciones_corregido(tipo_habitaciones_str)

def calcular_totales(tipo_habitaciones_str, cantidad_noches, precios):
    return calcular_totales_corregido(tipo_habitaciones_str, cantidad_noches, precios)