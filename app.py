from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Carrier Sales Mock API",
    description="A mock API for verifying carriers, retrieving loads, and evaluating offers."
)

# ------------------------------------------------
# 1. In-Memory Carrier Database
# ------------------------------------------------
# Known MC numbers for verification
carrier_db = {
    "MC123456": "ABC Trucking",
    "MC789012": "XYZ Freight",
    "MC345678": "Delta Logistics"
}

# ------------------------------------------------
# 2. In-Memory Load Data
# ------------------------------------------------
# Updated to include REF09460, REF04684, REF09690, and REF90781
load_data = {
    "REF09460": {
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
    "REF04684": {
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
    "REF09690": {
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
    "REF90781": {
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
# 5. Load Lookup Endpoint
# ------------------------------------------------
@app.get("/loads/{reference_number}")
def get_load(reference_number: str):
    """
    Retrieves load details by reference_number from the in-memory load_data.
    Returns a 404 error if the load is not found.
    """
    ref = reference_number.strip()
    if ref in load_data:
        return load_data[ref]
    else:
        raise HTTPException(status_code=404, detail="Load not found")

# ------------------------------------------------
# 6. Models for Offer Evaluation
# ------------------------------------------------
class EvaluateOfferRequest(BaseModel):
    carrier_offer: int
    our_last_offer: int
    offer_attempt: int = 1

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
    Simulates negotiation logic:
    - If carrier_offer >= our_last_offer, accept.
    - Otherwise, counter by meeting in the middle.
    - If offer_attempt > 1, provide a final counter.
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
# 8. Main Entry Point
# ------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
