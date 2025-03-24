import csv
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Your FMCSA API key
FCMSA_API_KEY = "cdc33e44d693a3a58451898d4ec9df862c65b954"

app = FastAPI(
    title="Carrier Sales API",
    description="API for verifying carriers via FMCSA docket-number endpoint, retrieving load details from CSV, and evaluating offers."
)

# ---------------------------------------------------
# CSV-Based Load Data
# ---------------------------------------------------
load_data_csv = {}

def normalize_reference(ref: str) -> str:
    """
    Normalizes a reference number by removing the 'REF' prefix if present
    and stripping leading zeros.
    """
    ref = ref.strip().upper()
    if ref.startswith("REF"):
        ref = ref[3:]
    return ref.lstrip("0")

def load_csv_data(filename: str):
    """
    Loads load details from a CSV file and indexes by normalized reference number.
    """
    global load_data_csv
    try:
        with open(filename, mode="r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                raw_ref = row.get("reference_number", "").strip().upper()
                normalized = normalize_reference(raw_ref)
                try:
                    row["rate"] = float(row["rate"])
                except (ValueError, TypeError):
                    row["rate"] = None
                load_data_csv[normalized] = row
    except FileNotFoundError:
        print(f"CSV file {filename} not found. No load data loaded.")

# Load the CSV on startup
load_csv_data("loads.csv")

# ---------------------------------------------------
# Models
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

# POST /loads
@app.post("/loads", response_model=Load)
def get_load(request: LoadLookupRequest):
    """
    Retrieves load details by reference number from the request body.
    Accepts formats like "REF09460", "09460", or "9460".
    """
    normalized = normalize_reference(request.reference_number)
    if normalized in load_data_csv:
        return load_data_csv[normalized]
    else:
        raise HTTPException(status_code=404, detail="Load not found")

# ---------------------------------------------------
# Carrier Verification via docket-number
# ---------------------------------------------------
class VerifyCarrierRequest(BaseModel):
    mc_number: str

class VerifyCarrierResponse(BaseModel):
    verified: bool
    carrier_name: str

@app.post("/verify-carrier", response_model=VerifyCarrierResponse)
async def verify_carrier(request: VerifyCarrierRequest):
    """
    Verifies the carrier’s MC number or numeric docket number using the FMCSA API:
      https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{NUMBER}?webKey=...
    If user provides "MC123456", we strip "MC" to get "123456".
    If user provides just "123456", we use that directly.
    """
    mc_raw = request.mc_number.strip().upper()
    # If it starts with "MC", remove it:
    if mc_raw.startswith("MC"):
        mc_raw = mc_raw[2:].strip()  # e.g. "MC123456" -> "123456"

    # mc_raw should now be the pure numeric portion
    if not mc_raw.isdigit():
        raise HTTPException(status_code=400, detail="Invalid MC/docket number. Must be numeric after removing 'MC'.")

    url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_raw}?webKey={FCMSA_API_KEY}"

    try:
        resp = requests.get(url, timeout=10)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error calling FMCSA API: {str(e)}")

    if resp.status_code == 200:
        try:
            data = resp.json()
        except ValueError:
            raise HTTPException(status_code=500, detail="FMCSA returned invalid JSON.")

        # The structure typically:
        # {
        #   "content": {
        #     "carrier": [
        #       {
        #         "legalName": "...",
        #         "dbaName": "...",
        #         ...
        #       }
        #     ]
        #   }
        # }
        content = data.get("content")
        if not content:
            raise HTTPException(status_code=404, detail="No content found in FMCSA data.")
        carriers = content.get("carrier")
        if not carriers or len(carriers) == 0:
            raise HTTPException(status_code=404, detail="No carriers found in FMCSA data.")

        carrier_info = carriers[0]
        # We prioritize legalName; fallback to dbaName
        legal_name = carrier_info.get("legalName")
        if not legal_name:
            legal_name = carrier_info.get("dbaName")

        if not legal_name:
            raise HTTPException(status_code=404, detail="Carrier name not found in FMCSA data.")

        return VerifyCarrierResponse(verified=True, carrier_name=legal_name)
    else:
        raise HTTPException(status_code=404, detail="Carrier not found or FMCSA API error.")

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
    Evaluates an offer:
      - Accept if carrier_offer >= our_last_offer.
      - Otherwise, counter by averaging the two values.
      - If offer_attempt > 1, the counter is considered final.
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
