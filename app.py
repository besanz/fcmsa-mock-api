import csv
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Clave de la API de FMCSA
FCMSA_API_KEY = "cdc33e44d693a3a58451898d4ec9df862c65b954"

app = FastAPI(
    title="Carrier Sales API",
    description="API for verifying carriers via FMCSA, retrieving load details from CSV, and evaluating offers."
)

# ---------------------------------------------------
# CSV-Based Load Data
# ---------------------------------------------------
load_data_csv = {}

def normalize_reference(ref: str) -> str:
    """
    Normaliza un número de referencia:
      - Elimina el prefijo "REF" si existe.
      - Quita ceros a la izquierda.
    """
    ref = ref.strip().upper()
    if ref.startswith("REF"):
        ref = ref[3:]
    return ref.lstrip("0")

def load_csv_data(filename: str):
    """
    Carga datos de cargas desde un archivo CSV
    y los indexa por número de referencia normalizado.
    """
    global load_data_csv
    try:
        with open(filename, mode="r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                raw_ref = row.get("reference_number", "").strip().upper()
                normalized = normalize_reference(raw_ref)
                # Convertir el campo 'rate' a número si es posible
                try:
                    row["rate"] = float(row["rate"])
                except (ValueError, TypeError):
                    row["rate"] = None
                load_data_csv[normalized] = row
    except FileNotFoundError:
        print(f"CSV file {filename} not found. No load data loaded.")

# Cargar el CSV al iniciar la aplicación
load_csv_data("loads.csv")

# ---------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------
class Load(BaseModel):
    reference_number: str
    origin: str
    destination: str
    equipment_type: str
    rate: float
    commodity: str

class LoadLookupRequest(BaseModel):
    reference_number: str

# ---------------------------------------------------
# POST /loads
# ---------------------------------------------------
@app.post("/loads", response_model=Load)
def get_load(request: LoadLookupRequest):
    """
    Busca detalles de una carga usando el reference_number
    enviado en el cuerpo de la petición.
    Acepta formatos tipo "REF09460", "09460" o "9460".
    """
    normalized = normalize_reference(request.reference_number)
    if normalized in load_data_csv:
        return load_data_csv[normalized]
    else:
        raise HTTPException(status_code=404, detail="Load not found")

# ---------------------------------------------------
# Carrier Verification (FMCSA real API)
# ---------------------------------------------------
class VerifyCarrierRequest(BaseModel):
    mc_number: str

class VerifyCarrierResponse(BaseModel):
    verified: bool
    carrier_name: str

@app.post("/verify-carrier", response_model=VerifyCarrierResponse)
async def verify_carrier(request: VerifyCarrierRequest):
    """
    Verifica el MC number de un carrier usando la API pública de FMCSA.
    Se espera que el MC number venga con el prefijo 'MC', p.ej. 'MC123456'.
    """
    mc = request.mc_number.strip().upper()
    if not mc.startswith("MC"):
        raise HTTPException(status_code=400, detail="Invalid MC number format. Must start with 'MC'.")

    # Extraer la parte numérica del MC (después de 'MC')
    mc_number_only = mc[2:]

    # Construir la URL para la llamada a FMCSA
    url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/MC/{mc_number_only}?webKey={FCMSA_API_KEY}"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # Se espera una estructura del tipo:
            # {
            #   "content": {
            #     "carrier": [
            #       {
            #         "carrierName": "XYZ Freight Inc",
            #         ...
            #       }
            #     ]
            #   }
            # }
            content = data.get("content", {})
            carrier_list = content.get("carrier", [])
            if len(carrier_list) > 0:
                carrier_info = carrier_list[0]
                carrier_name = carrier_info.get("carrierName", "Unknown Carrier")
                return VerifyCarrierResponse(verified=True, carrier_name=carrier_name)
            else:
                raise HTTPException(status_code=404, detail="Carrier not found in FMCSA data.")
        else:
            raise HTTPException(status_code=404, detail="Carrier not found or FMCSA API error.")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error calling FMCSA API: {str(e)}")

# ---------------------------------------------------
# Offer Evaluation
# ---------------------------------------------------
class EvaluateOfferRequest(BaseModel):
    carrier_offer: int
    our_last_offer: int
    offer_attempt: int = 1

class EvaluateOfferResponse(BaseModel):
    result: str   # "accept", "counter", or "decline"
    new_offer: int
    message: str

@app.post("/evaluate-offer", response_model=EvaluateOfferResponse)
def evaluate_offer(request: EvaluateOfferRequest):
    """
    Evalúa una oferta de tarifa.
      - Si carrier_offer >= our_last_offer, se acepta.
      - Si no, se calcula una contrapropuesta promediando ambos valores.
      - Si offer_attempt > 1, se asume como contrapropuesta final.
    """
    carrier_offer = request.carrier_offer
    our_last_offer = request.our_last_offer
    attempt = request.offer_attempt

    if carrier_offer >= our_last_offer:
        return EvaluateOfferResponse(
            result="accept",
            new_offer=carrier_offer,
            message="Offer accepted."
        )
    else:
        new_offer = (our_last_offer + carrier_offer) // 2
        if attempt == 1:
            return EvaluateOfferResponse(
                result="counter",
                new_offer=new_offer,
                message=f"We can go as low as {new_offer} on this load."
            )
        else:
            return EvaluateOfferResponse(
                result="counter",
                new_offer=new_offer,
                message=f"This is our final counter at {new_offer}."
            )

# ---------------------------------------------------
# Main Entry Point
# ---------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
