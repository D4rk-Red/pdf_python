from flask import Flask, request, jsonify
import requests
import time
import json
from datetime import datetime
from config import (
    API_KEY, EVOLUTION_API_BASE, WEBHOOK_TOKEN,
    DURACION_ESCRIBIENDO, TIEMPO_MENSAJE_ANTIGUO, TIEMPO_AGRUPACION,
    NUMERO_AUTORIZADO
)
from extractor import extraer_informacion_reserva
from pdf_generator import generar_cotizacion_pdf
from precios import obtener_precios_habitaciones, calcular_totales

app = Flask(__name__)

conversaciones_activas = {}
mensajes_procesados = set()

def debe_procesar_mensaje(numero, message_id, timestamp_mensaje):
    ahora = time.time()
    
    if message_id in mensajes_procesados:
        return False
    
    diferencia = ahora - timestamp_mensaje
    if diferencia > TIEMPO_MENSAJE_ANTIGUO:
        mensajes_procesados.add(message_id)
        return False
    
    if numero in conversaciones_activas:
        conv = conversaciones_activas[numero]
        
        if conv["estado"] == "cerrada":
            tiempo_desde_cierre = ahora - conv["timestamp"]
            if tiempo_desde_cierre < 5:
                mensajes_procesados.add(message_id)
                return False
            else:
                conv["estado"] = "activa"
                conv["timestamp"] = ahora
                conv["message_ids"] = [message_id]
        
        elif conv["estado"] == "activa":
            tiempo_desde_ultimo = ahora - conv["timestamp"]
            if tiempo_desde_ultimo < TIEMPO_AGRUPACION:
                conv["message_ids"].append(message_id)
                conv["timestamp"] = ahora
                mensajes_procesados.add(message_id)
                return False
    else:
        conversaciones_activas[numero] = {
            "estado": "activa",
            "timestamp": ahora,
            "message_ids": [message_id]
        }
    
    mensajes_procesados.add(message_id)
    return True

def cerrar_conversacion(numero):
    if numero in conversaciones_activas:
        conversaciones_activas[numero]["estado"] = "cerrada"
        conversaciones_activas[numero]["timestamp"] = time.time()

def limpiar_cache():
    if len(mensajes_procesados) > 1000:
        mensajes_procesados.clear()
    
    ahora = time.time()
    for numero in list(conversaciones_activas.keys()):
        if ahora - conversaciones_activas[numero]["timestamp"] > 3600:
            del conversaciones_activas[numero]

def marcar_como_leido(remote_jid, message_id, instance_name):
    url = f"{EVOLUTION_API_BASE}/chat/markMessageAsRead/{instance_name}"
    headers = {"Content-Type": "application/json", "apikey": API_KEY}
    payload = {"remoteJid": remote_jid, "id": message_id}
    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
        return True
    except Exception:
        return False

def mostrar_escribiendo(numero, instance_name, duracion=3):
    url = f"{EVOLUTION_API_BASE}/chat/sendPresence/{instance_name}"
    headers = {"Content-Type": "application/json", "apikey": API_KEY}
    payload = {"number": numero, "presence": "composing", "delay": duracion * 1000}
    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
        time.sleep(duracion)
        return True
    except Exception:
        return False

def enviar_mensaje(numero, texto, instance_name):
    url = f"{EVOLUTION_API_BASE}/message/sendText/{instance_name}"
    headers = {"Content-Type": "application/json", "apikey": API_KEY}
    payload = {"number": numero, "text": texto}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        return True
    except Exception:
        return False

def enviar_pdf(numero, pdf_base64, instance_name, filename="cotizacion.pdf"):
    url = f"{EVOLUTION_API_BASE}/message/sendMedia/{instance_name}"
    headers = {"Content-Type": "application/json", "apikey": API_KEY}
    payload = {
        "number": numero,
        "mediatype": "document",
        "media": pdf_base64,
        "fileName": filename
    }
    try:
        requests.post(url, headers=headers, json=payload, timeout=30)
        return True
    except Exception:
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    token = request.args.get('token')
    if token != WEBHOOK_TOKEN:
        return jsonify({"error": "Token invalido"}), 401
    
    data = request.json
    try:
        event = data.get('event')
        if event != 'messages.upsert':
            return jsonify({"status": "ok"}), 200
        
        instance_name = data.get('instance')
        mensaje_data = data.get('data', {})
        
        if mensaje_data.get('key', {}).get('fromMe'):
            return jsonify({"status": "ok"}), 200
        
        key = mensaje_data.get('key', {})
        remote_jid = key.get('remoteJid', '')
        message_id = key.get('id', '')
        numero = remote_jid.split('@')[0]
        
        if numero != NUMERO_AUTORIZADO:
            return jsonify({"status": "no_autorizado"}), 200
            
        timestamp_mensaje = mensaje_data.get('messageTimestamp', 0)
        message = mensaje_data.get('message', {})
        texto = (message.get('conversation') or 
                message.get('extendedTextMessage', {}).get('text') or '')
        
        if not texto or not numero:
            return jsonify({"status": "ok"}), 200
        
        if not debe_procesar_mensaje(numero, message_id, timestamp_mensaje):
            return jsonify({"status": "ok"}), 200
        
        limpiar_cache()
        marcar_como_leido(remote_jid, message_id, instance_name)
        
        info_reserva = extraer_informacion_reserva(texto)
        
        campos_requeridos = ['check_in', 'check_out', 'cant_personas', 
                           'cantidad_habitaciones', 'tipo_habitaciones']
        
        campos_faltantes = [campo for campo in campos_requeridos 
                          if not info_reserva.get(campo)]
        
        if campos_faltantes:
            mostrar_escribiendo(numero, instance_name, duracion=DURACION_ESCRIBIENDO)
            mensaje_error = (
                "Necesito mas informacion para la cotizacion. Por favor indica: "
                "Fecha de entrada, fecha de salida, cantidad de personas, "
                "cantidad de habitaciones y tipo de habitaciones."
            )
            enviar_mensaje(numero, mensaje_error, instance_name)
            cerrar_conversacion(numero)
            return jsonify({"status": "info_incompleta"}), 200
        
        mostrar_escribiendo(numero, instance_name, duracion=DURACION_ESCRIBIENDO)
        
        try:
            check_in = datetime.strptime(info_reserva['check_in'], '%Y-%m-%d')
            check_out = datetime.strptime(info_reserva['check_out'], '%Y-%m-%d')
            cantidad_noches = (check_out - check_in).days
            
            if cantidad_noches <= 0:
                raise ValueError("Fechas invalidas")
            
            precios = obtener_precios_habitaciones()
            totales = calcular_totales(
                info_reserva['tipo_habitaciones'],
                cantidad_noches,
                precios
            )
            
            pdf_base64 = generar_cotizacion_pdf(
                info_reserva,
                totales,
                cantidad_noches
            )
            
            # Construir mensaje de resumen
            habitaciones_lista = []
            for hab in totales['habitaciones']:
                habitaciones_lista.append(f"{hab['cantidad']} {hab['tipo'].replace('Habitación ', '')}")
            
            mensaje_exito = (
                f"Cotizacion generada:\n"
                f"Check-in: {info_reserva['check_in']}\n"
                f"Check-out: {info_reserva['check_out']}\n"
                f"Noches: {cantidad_noches}\n"
                f"Habitaciones: {', '.join(habitaciones_lista)}\n"
                f"Total: ${totales['total_bruto']:,} CLP\n"
                f"Enviando PDF..."
            )
            
            enviar_mensaje(numero, mensaje_exito, instance_name)
            time.sleep(1)
            enviar_pdf(numero, pdf_base64, instance_name)
            
        except Exception as e:
            print(f"Error generando cotizacion: {e}")
            enviar_mensaje(
                numero,
                "Error generando la cotizacion. Intente nuevamente.",
                instance_name
            )
        
        cerrar_conversacion(numero)
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Error en webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "activo"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)