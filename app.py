import csv
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

FCMSA_API_KEY = "cdc33e44d693a3a58451898d4ec9df862c65b954"

app = FastAPI(
    title="Carrier Sales API",
    description="API for verifying carriers via FMCSA (docket-number), retrieving load details from CSV, and evaluating offers."
)

# ---------------------------------------------------
# CSV-Based Load Data
# ---------------------------------------------------
load_data_csv = {}

def normalize_reference(ref: str) -> str:
    """
    Removes 'REF' prefix if present, strips leading zeros.
    E.g. 'REF09460' -> '9460'
    """
    ref = ref.strip().upper()
    if ref.startswith("REF"):
        ref = ref[3:]
    return ref.lstrip("0")

def load_csv_data(filename: str):
    global load_data_csv
    try:
        with open(filename, mode="r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                raw_ref = row.get("reference_number", "").strip().upper()
                normalized = normalize_reference(raw_ref)
                # Convert 'rate' to float if possible
                try:
                    row["rate"] = float(row["rate"])
                except (ValueError, TypeError):
                    row["rate"] = None
                load_data_csv[normalized] = row
    except FileNotFoundError:
        print(f"CSV file {filename} not found. No load data loaded.")

load_csv_data("loads.csv")

# ---------------------------------------------------
# Pydantic Models
# ---------------------------------------------------
class Load(BaseModel):
    reference_number: str
    origin: str
    destination: str
    equipment_type: str
    rate: float
    commodity: str

class LoadLookupRequest(BaseModel):
    reference_number: str = Field(..., example="REF09460")

class VerifyCarrierRequest(BaseModel):
    mc_number: str = Field(
        ...,
        example="MC845901",
        description="If docket number is 845901, pass either '845901' or 'MC845901'."
    )

class VerifyCarrierResponse(BaseModel):
    verified: bool
    carrier_name: str

class EvaluateOfferRequest(BaseModel):
    carrier_offer: int = Field(..., example=600)
    our_last_offer: int = Field(..., example=700)
    offer_attempt: int = Field(1, example=1)

class EvaluateOfferResponse(BaseModel):
    result: str   # "accept", "counter", or "decline"
    new_offer: int
    message: str

# ---------------------------------------------------
# POST /loads
# ---------------------------------------------------
@app.post("/loads", response_model=Load)
def get_load(request: LoadLookupRequest):
    """
    Retrieves load details from 'loads.csv' by reference number.
    Accepts 'REF09460', '09460', '9460', etc.
    """
    normalized = normalize_reference(request.reference_number)
    if normalized in load_data_csv:
        return load_data_csv[normalized]
    else:
        raise HTTPException(status_code=404, detail="Load not found")

# ---------------------------------------------------
# Carrier Verification (Using docket-number endpoint)
# ---------------------------------------------------
@app.post("/verify-carrier", response_model=VerifyCarrierResponse)
async def verify_carrier(request: VerifyCarrierRequest):
    """
    Verifies a carrier's docket number via FMCSA:
      https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{NUMBER}?webKey=...
    
    If user passes 'MC845901', we strip 'MC' -> '845901' and call the docket endpoint.
    If user passes '845901', we use that directly.
    
    Example successful data:
      {
        "content": {
          "carrier": [
            {
              "legalName": "JOHN S THOMPSON HAULING INC",
              "dotNumber": "348507",
              "mcNumber": "845901",
              ...
            }
          ]
        }
      }
    """
    raw = request.mc_number.strip().upper()
    if raw.startswith("MC"):
        docket_number = raw[2:].strip()
    else:
        docket_number = raw  # assume just digits

    url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{docket_number}?webKey={FCMSA_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error calling FMCSA: {str(e)}")

    if resp.status_code == 200:
        # parse JSON
        try:
            data = resp.json()
        except ValueError:
            raise HTTPException(status_code=500, detail="FMCSA returned invalid JSON.")
        
        content = data.get("content")
        if not content:
            raise HTTPException(status_code=404, detail="No content in FMCSA data.")
        carriers = content.get("carrier")
        if not carriers or len(carriers) == 0:
            raise HTTPException(status_code=404, detail="No carriers found in FMCSA data.")
        
        # pick the first carrier
        carrier_info = carriers[0]
        # 'legalName' or 'carrierName' might exist
        # often it's 'carrierName' or 'legalName' in the data
        # If you see 'legalName' is more accurate, use that:
        legal_name = carrier_info.get("legalName")
        if not legal_name:
            legal_name = carrier_info.get("carrierName")
        if not legal_name:
            raise HTTPException(status_code=404, detail="Carrier name not found in FMCSA data.")

        return VerifyCarrierResponse(verified=True, carrier_name=legal_name)
    elif resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Carrier not found in FMCSA data.")
    else:
        raise HTTPException(status_code=500, detail=f"FMCSA API error. Status code: {resp.status_code}")

# ---------------------------------------------------
# Offer Evaluation
# ---------------------------------------------------
@app.post("/evaluate-offer", response_model=EvaluateOfferResponse)
def evaluate_offer(request: EvaluateOfferRequest):
    """
    Evaluates an offer:
      - Accept if carrier_offer >= our_last_offer
      - Otherwise, counter by averaging the two values
      - If offer_attempt > 1, final counter
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
# Main
# ---------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
