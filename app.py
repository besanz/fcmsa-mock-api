import csv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Carrier Sales API",
    description="API for verifying carriers, retrieving load details from CSV, and evaluating offers."
)

# -----------------------------------------
# CSV-Based Load Data
# -----------------------------------------
# Global dictionary to hold load data indexed by normalized reference number.
load_data_csv = {}

def normalize_reference(ref: str) -> str:
    """
    Normalizes a reference number by:
    - Removing the "REF" prefix if present.
    - Stripping leading zeros.
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
                # Convert rate to number (float or int) if needed
                try:
                    row["rate"] = float(row["rate"])
                except (ValueError, TypeError):
                    row["rate"] = None
                load_data_csv[normalized] = row
    except FileNotFoundError:
        print(f"CSV file {filename} not found. No load data loaded.")

# Load the CSV on startup
load_csv_data("loads.csv")

# Pydantic model for load response
class Load(BaseModel):
    reference_number: str
    origin: str
    destination: str
    equipment_type: str
    rate: float
    commodity: str

# -----------------------------------------
# POST /loads/{reference_number}
# -----------------------------------------
@app.post("/loads/{reference_number}", response_model=Load)
def get_load(reference_number: str):
    """
    Retrieves load details by a flexible reference number format (via POST).
    Accepts formats like "REF09460", "09460", or "9460" in the path.
    """
    normalized = normalize_reference(reference_number)
    if normalized in load_data_csv:
        return load_data_csv[normalized]
    else:
        raise HTTPException(status_code=404, detail="Load not found")

# -----------------------------------------
# Carrier Verification (Simulated FMCSA API)
# -----------------------------------------
carrier_db = {
    "MC123456": "ABC Trucking",
    "MC789012": "XYZ Freight",
    "MC345678": "Delta Logistics"
}

class VerifyCarrierRequest(BaseModel):
    mc_number: str

class VerifyCarrierResponse(BaseModel):
    verified: bool
    carrier_name: str

@app.post("/verify-carrier", response_model=VerifyCarrierResponse)
async def verify_carrier(request: VerifyCarrierRequest):
    """
    Verifies the carrier’s MC number (simulates FMCSA API).
    """
    mc = request.mc_number.strip()
    if not mc.startswith("MC"):
        raise HTTPException(status_code=400, detail="Invalid MC number format. Must start with 'MC'.")
    if mc in carrier_db:
        return VerifyCarrierResponse(verified=True, carrier_name=carrier_db[mc])
    else:
        raise HTTPException(status_code=404, detail="Carrier not found in our database.")

# -----------------------------------------
# Offer Evaluation
# -----------------------------------------
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
      - If offer_attempt > 1, this is our final counter.
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

# -----------------------------------------
# Main Entry Point
# -----------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
