from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Carrier Sales Mock API",
    description="A self-made FMCSA mock API for verifying carriers, retrieving loads, and evaluating offers."
)

# ------------------------------------------------
# 1. In-Memory Carrier Database
# ------------------------------------------------
carrier_db = {
    "MC123456": "ABC Trucking",
    "MC789012": "XYZ Freight",
    "MC345678": "Delta Logistics"
}

# ------------------------------------------------
# 2. In-Memory Load Data
# ------------------------------------------------
# We'll store keys like "9460", "4684", "9690", "90781"
# so that the user can pass "REF09460" or "09460" or "9460" 
# and we unify it internally to "9460" to find the data.
load_data = {
    "9460": {
        "reference_number": "REF09460",
        "origin": "Denver, CO",
        "destination": "Detroit, MI",
        "equipment_type": "Dry Van",
        "rate": 868,
        "commodity": "Automotive Parts",
        "mc_number": "MC123456",
        "is_partial": True,
        "pickup_time": "15:00",
        "delivery_time": "Friday, July 12th"
    },
    "4684": {
        "reference_number": "REF04684",
        "origin": "Dallas, TX",
        "destination": "Chicago, IL",
        "equipment_type": "Dry Van or Flatbed",
        "rate": 570,
        "commodity": "Agricultural Products",
        "mc_number": "MC789012",
        "is_partial": False,
        "pickup_time": "14:00",
        "delivery_time": "Friday, July 12th"
    },
    "9690": {
        "reference_number": "REF09690",
        "origin": "Detroit, MI",
        "destination": "Nashville, TN",
        "equipment_type": "Dry Van",
        "rate": 1495,
        "commodity": "Industrial Equipment",
        "mc_number": "MC345678",
        "is_partial": False,
        "pickup_time": "13:00",
        "delivery_time": "Friday, July 12th"
    },
    "90781": {
        "reference_number": "REF90781",
        "origin": "San Diego, CA",
        "destination": "Phoenix, AZ",
        "equipment_type": "Reefer",
        "rate": 1200,
        "commodity": "Produce",
        "mc_number": "MC789012",
        "is_partial": False,
        "pickup_time": "16:00",
        "delivery_time": "Saturday, July 13th"
    }
}

# ------------------------------------------------
# 3. Carrier Verification
# ------------------------------------------------
class VerifyCarrierRequest(BaseModel):
    mc_number: str

class VerifyCarrierResponse(BaseModel):
    verified: bool
    carrier_name: str

@app.post("/verify-carrier", response_model=VerifyCarrierResponse)
async def verify_carrier(request: VerifyCarrierRequest):
    """
    Verifies the carrier's MC number against our in-memory carrier_db.
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
# 4. Load Lookup
# ------------------------------------------------
class LoadLookupRequest(BaseModel):
    reference_number: str

@app.post("/loads/lookup")
def lookup_load(request: LoadLookupRequest):
    """
    Accepts a reference_number in any format: "REF09460", "09460", "9460".
    Strips 'REF' if present and leading zeros, then finds the data in 'load_data'.
    """
    raw_ref = request.reference_number.strip().upper()  # e.g. "REF09460", "09460", "9460"
    # Remove "REF" prefix if it exists
    if raw_ref.startswith("REF"):
        raw_ref = raw_ref[3:]  # remove the first 3 chars "REF"
    # Remove leading zeros
    stripped_ref = raw_ref.lstrip("0")  # e.g. "09460" -> "9460"

    if not stripped_ref:
        raise HTTPException(status_code=400, detail="Reference number is empty after stripping REF/zeros.")

    if stripped_ref in load_data:
        return load_data[stripped_ref]
    else:
        raise HTTPException(status_code=404, detail="Load not found")

# ------------------------------------------------
# 5. Offer Evaluation
# ------------------------------------------------
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
    Negotiation logic:
    - If carrier_offer >= our_last_offer, accept.
    - Else counter by meeting in the middle.
    - If offer_attempt > 1, final counter.
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
# 6. Main Entry Point
# ------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
