import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, HTTPException  # type: ignore
import httpx
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.responses import JSONResponse  # type: ignore
from google.cloud import texttospeech
from elevenlabs import ElevenLabs # type: ignore
import openai  # type: ignore
import base64
import logging
import asyncio  # Asegúrate de importar asyncio si no está incluido.

logging.basicConfig(level=logging.INFO)

openai_api_key = os.getenv("OPENAI_API_KEY", "clave_por_defecto")
logging.info(f"Clave API de OpenAI: {openai_api_key[:5]}******")  # Solo muestra los primeros caracteres para verificar

# Configura tu archivo JSON de autenticación de Google Cloud
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key/clave.json"

# Configura tu clave de API de ElevenLabs
eleven_labs_api_key = os.getenv("ELEVENLABS_API_KEY")
if not eleven_labs_api_key:
    raise Exception("No se encontró la clave API de ElevenLabs en las variables de entorno")
eleven_labs = ElevenLabs(api_key=eleven_labs_api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200","https://0j7f3mhw-4200.use2.devtunnels.ms","https://agente-lait.web.app"],  # Permitir solicitudes solo desde el servidor Angular
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API route to get signed URL
@app.get("/api/signed-url")
async def get_signed_url():
    agent_id = os.getenv("AGENT_ID")
    xi_api_key = os.getenv("XI_API_KEY")
    
    if not agent_id or not xi_api_key:
        raise HTTPException(status_code=500, detail="Missing environment variables")
    
    url = f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={"xi-api-key": xi_api_key}
            )
            response.raise_for_status()
            data = response.json()
            return {"signedUrl": data["signed_url"]}
            
        except httpx.HTTPError:
            raise HTTPException(status_code=500, detail="Failed to get signed URL")

# API route for getting Agent ID
@app.get("/api/getAgentId")
def get_unsigned_url():
    agent_id = os.getenv("AGENT_ID")
    if not agent_id:
        raise HTTPException(status_code=500, detail="Agent ID not found in environment variables")
    return {"agentId": agent_id}

# API route to get signed URL
@app.get("/api/signed-url-lait")
async def get_signed_url():
    agent_id = os.getenv("AGENT_ID_LAIT")
    xi_api_key = os.getenv("XI_API_KEY")
    
    if not agent_id or not xi_api_key:
        raise HTTPException(status_code=500, detail="Missing environment variables")
    
    url = f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={"xi-api-key": xi_api_key}
            )
            response.raise_for_status()
            data = response.json()
            return {"signedUrl": data["signed_url"]}
            
        except httpx.HTTPError:
            raise HTTPException(status_code=500, detail="Failed to get signed URL")

# API route for getting Agent ID
@app.get("/api/getAgentIdLait")
def get_unsigned_url():
    agent_id = os.getenv("AGENT_ID_LAIT")
    if not agent_id:
        raise HTTPException(status_code=500, detail="Agent ID not found in environment variables")
    return {"agentId": agent_id}

@app.post("/api/configurar-agente")
async def configurar_agente(request: Request):
    agent_id = os.getenv("AGENT_ID_LAIT")
    xi_api_key = os.getenv("XI_API_KEY")
    
    if not agent_id or not xi_api_key:
        raise HTTPException(status_code=500, detail="Faltan variables de entorno")
    
    data = await request.json()
    print(data)
    prompt = data.get("prompt")
    voice_id = data.get("voice_id")
    agent_name = data.get("agentName")
    initial_greeting = 'Hola, mucho gusto soy '+data.get("agentName")+', tu agente de personalizado ¿En qué te puedo colaborar el día de hoy?'
    
    if not prompt or not voice_id:
        raise HTTPException(status_code=400, detail="Faltan datos: prompt y/o voice_id")
    
    body = {
        "name": agent_name,
        "conversation_config": {
            "agent": {
              "first_message": initial_greeting,
                "prompt": {
                    "prompt": prompt,
                    "llm": "gemini-2.0-flash-001",
                    "temperature": 0,
                    "max_tokens": -1
                }
            },
            "tts": {
                "voice_id": voice_id
            }
        }
    }
    
    url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"
    headers = {
        "xi-api-key": xi_api_key,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(url, headers=headers, json=body)
            response.raise_for_status()
            return {"message": "Agente configurado correctamente"}
        except httpx.HTTPStatusError as e:
            print("Error en la respuesta:", e.response.text)
            raise HTTPException(status_code=500, detail=f"Error de ElevenLabs: {e.response.text}")
        except Exception as e:
            print("Error inesperado:", str(e))
            raise HTTPException(status_code=500, detail="Error inesperado al configurar el agente")

# Inicializa el cliente de Google TTS
tts_client = texttospeech.TextToSpeechClient()

# Configura la clave de API de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY", "clave_por_defecto")
if not openai.api_key:
    raise Exception("No se encontró la clave API de OpenAI en las variables de entorno")

# Prompt combinado para el agente conversacional
PROMPT = """
LAIT Technology - Inbound Support and Sales Call Script
Introducción y Contexto
Eres Natalia, una agente digital especializada en soporte y ventas en LAIT Technology. Tu objetivo es ofrecer soluciones efectivas a clientes actuales y potenciales, maximizando la satisfacción mientras exploras oportunidades de venta. Puedes responder en inglés y español.

Instrucciones clave:
1. Mantén tus respuestas claras y breves, en un rango de 70 a 100 palabras.
2. Resume las ideas principales sin omitir información importante.
3. Si el cliente solicita detalles extensos, proporciona una respuesta concisa y ofrece la opción de seguir la conversación para más información.
4. Si supera los 2 minutos con 30 segundos y requiere más detalle, conéctalo con un asesor especializado y despídete.

Servicios Clave de LAIT Technology
LAIT Smart Document: Gestión inteligente de documentos para optimizar el manejo de facturas y recibos de pago.
LAIT NexAI: Bots personalizados que ofrecen tanto asistencia por voz como chatbots configurables. Estos bots están diseñados para automatizar tareas y mejorar la productividad empresarial, adaptándose a las necesidades específicas de cada empresa.
Público Objetivo
Empresas que buscan automatizar procesos, mejorar la eficiencia operativa y mantenerse competitivas con soluciones tecnológicas avanzadas.

SCRIPT PARA LLAMADAS ENTRANTES
1. Identificación de Necesidades
Averigua el motivo de la llamada con preguntas abiertas:
Ejemplo: "¿Podrías contarme un poco más sobre el desafío que estás enfrentando o lo que necesitas lograr?"
Si es un cliente nuevo, investiga brevemente sobre su sector para personalizar tu enfoque.
2. Respuesta Personalizada y Presentación de Soluciones
Adapta tu respuesta según la consulta:
Soporte técnico: Proporciona pasos claros para resolver problemas y, si es necesario, abre un ticket de soporte.
Consulta sobre servicios: Explica cómo nuestras soluciones como LAIT NexAI o Smart Document pueden beneficiar a su sector. Destaca ventajas clave:
Llamadas automatizadas naturales.
Escalabilidad para empresas en crecimiento.
Seguridad avanzada, como detección de fraudes.
Ejemplo: "Nuestra solución es compatible con tu CRM y te permitirá ahorrar tiempo mientras aseguras altos estándares de privacidad."
3. Manejo de Objeciones
Dificultad Técnica: Ofrece asistencia guiada o entrenamiento personalizado.
Comparaciones con Competencia: Destaca personalización, métricas de análisis y casos de éxito.
Precios: Habla del ROI y ofrece agendar una consulta con ventas para detalles específicos.
4. Ofrecer Demostraciones y Cierres
Propón una demostración personalizada:
Ejemplo: "¿Qué te parece si agendamos una demostración para que veas cómo nuestra tecnología puede resolver tus necesidades?"
Asegúrate de confirmar la cita con claridad:
Ejemplo: "Te puedo agendar el [día/hora]. ¿Te funciona?"
Menciona cualquier promoción especial o beneficio exclusivo.
5. Conclusión de la Llamada
Pregunta si hay algo más en lo que puedas ayudar.
Ejemplo: "¿Hay algo más que pueda hacer por ti hoy?"
Agradece al cliente y despídete de forma amable:
Ejemplo: "Gracias por elegir LAIT Technology. Estamos aquí para ayudarte. Que tengas un excelente día."
"""

# Función para interactuar con el agente en tiempo real

async def interactuar_agente_conversacional(mensaje):
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": mensaje},
        ],
        max_tokens=150,  # Ajustado para producir respuestas de 70-100 palabras
        temperature=0.7,  # Reduce la creatividad para priorizar la concisión
        n=1
    )
    return response['choices'][0]['message']['content']



# Función para sintetizar texto a audio ELEVENLABS
# Lista todas las voces asociadas con tu cuenta
# Listar voces disponibles

def generar_audio(respuesta_texto):
    try:
        # Genera el audio utilizando ElevenLabs
        audio_generator = eleven_labs.generate(
            text=respuesta_texto,
            voice="Db2IZsmhaC6whev4HkLm",  # Cambia por el ID de la voz que prefieras
            model="eleven_multilingual_v2",
            
        )

        # Consume el generador para obtener los datos de audio como bytes
        audio_bytes = b"".join(audio_generator)

        if not audio_bytes:
            raise ValueError("La generación de audio no devolvió datos.")

        # Codifica el audio en Base64
        return base64.b64encode(audio_bytes).decode("utf-8")
    except ValueError as ve:
        raise HTTPException(status_code=500, detail=f"Error al generar audio: {str(ve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error desconocido: {str(e)}")

# Función para sintetizar texto a audio GOOGLE CLOUD
"""def generar_audio(respuesta_texto):
    try:
        synthesis_input = texttospeech.SynthesisInput(text=respuesta_texto)
        voice = texttospeech.VoiceSelectionParams(
            language_code="es-US",
            name="es-US-Journey-F"
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        # Genera el audio usando Google Text-to-Speech
        response_audio = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Codifica el audio en Base64
        return base64.b64encode(response_audio.audio_content).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al generar audio")"""

@app.websocket("/ws/conversar")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Introducción inicial del agente
    introduccion = (
        "Hola, soy Natalia, tu agente de ventas digital de LAIT Technology. Estoy aquí para ayudarte a descubrir "
        "cómo nuestras soluciones avanzadas pueden optimizar tus operaciones. ¿Me podrías decir tu nombre, por favor?"
    )
    introduccion_audio = generar_audio(introduccion)
    await websocket.send_json({"texto": introduccion, "audio": introduccion_audio})

    # Palabras clave para identificar una despedida
    palabras_despedida = ["adiós", "hasta luego", "muchas gracias", "gracias", "eso es todo", "terminemos", "bye"]

    while True:
        try:
            mensaje = await websocket.receive_text()

            # Verificar si el mensaje contiene una despedida
            if any(palabra in mensaje.lower() for palabra in palabras_despedida):
                despedida = "Gracias por comunicarte con LAIT Technology. ¡Que tengas un excelente día!"
                despedida_audio = generar_audio(despedida)
                await websocket.send_json({"texto": despedida, "audio": despedida_audio})

                # Cerrar el WebSocket después de enviar la despedida
                await websocket.close()
                break

            # Interactúa con el agente utilizando el prompt fluido
            respuesta_texto = await interactuar_agente_conversacional(mensaje)
            respuesta_audio = generar_audio(respuesta_texto)

            await websocket.send_json({"texto": respuesta_texto, "audio": respuesta_audio})

        except Exception as e:
            await websocket.send_json({"texto": "Ocurrió un error en el servidor.", "detalle": str(e)})
            break


# Inicia el servidor FastAPI con Uvicorn
if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=8000)
