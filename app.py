from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import csv

app = FastAPI(
    title="Carrier Sales Mock API",
    description="A mock API for verifying carriers, retrieving loads, and evaluating offers."
)

# ------------------------------------------------
# 1. In-Memory Carrier Database
# ------------------------------------------------
# For a more 'logical' approach, let's store known MC numbers here.
carrier_db = {
    "MC123456": "ABC Trucking",
    "MC789012": "XYZ Freight",
    "MC345678": "Delta Logistics"
}

# ------------------------------------------------
# 2. CSV Load Data
# ------------------------------------------------
def load_csv_data():
    """Reads loads.csv and returns a dict of reference_number -> row data."""
    loads_data = {}
    try:
        with open("loads.csv", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Normalize the reference number
                ref = row["reference_number"].strip()
                # Convert rate to int if it's numeric
                try:
                    row["rate"] = int(row["rate"])
                except ValueError:
                    row["rate"] = 0
                loads_data[ref] = row
    except FileNotFoundError:
        print("WARNING: loads.csv not found. Make sure it exists in the same directory.")
    return loads_data

loads_data = load_csv_data()

# ------------------------------------------------
# 3. Models for Carrier Verification
# ------------------------------------------------
class VerifyCarrierRequest(BaseModel):
    mc_number: str

class VerifyCarrierResponse(BaseModel):
    verified: bool
    carrier_name: str

# ------------------------------------------------
# 4. Carrier Verification Endpoint
# ------------------------------------------------
@app.post("/verify-carrier", response_model=VerifyCarrierResponse)
async def verify_carrier(request: VerifyCarrierRequest):
    """
    Verifies the carrier's MC number against our mock carrier_db.
    Returns a JSON with "verified" and "carrier_name".
    """
    mc = request.mc_number.strip()
    if not mc.startswith("MC"):
        raise HTTPException(status_code=400, detail="Invalid MC number format. Must start with 'MC'.")
    
    if mc in carrier_db:
        return VerifyCarrierResponse(verified=True, carrier_name=carrier_db[mc])
    else:
        raise HTTPException(status_code=404, detail="Carrier not found in our database.")

# ------------------------------------------------
# 5. Load Lookup Endpoint using CSV data
# ------------------------------------------------
@app.get("/loads/{reference_number}")
def get_load(reference_number: str):
    """
    Retrieves load details by reference_number from the CSV data.
    If not found, returns a 404 error.
    """
    ref = reference_number.strip()
    if ref in loads_data:
        return loads_data[ref]
    else:
        raise HTTPException(status_code=404, detail="Load not found")

# ------------------------------------------------
# 6. Models for Offer Evaluation
# ------------------------------------------------
class EvaluateOfferRequest(BaseModel):
    carrier_offer: int
    our_last_offer: int
    offer_attempt: int = 1  # how many times we've countered

class EvaluateOfferResponse(BaseModel):
    result: str   # "accept", "counter", or "decline"
    new_offer: int
    message: str

# ------------------------------------------------
# 7. Offer Evaluation Endpoint
# ------------------------------------------------
@app.post("/evaluate-offer", response_model=EvaluateOfferResponse)
def evaluate_offer(request: EvaluateOfferRequest):
    """
    Simulates a negotiation logic:
    - If carrier_offer >= our_last_offer, we accept.
    - Else we counter by meeting in the middle, up to 2 times.
    - If offer_attempt > 1 and still no agreement, we do a final counter.
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

# ------------------------------------------------
# 8. Main Entry Point for Local Testing
# ------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
