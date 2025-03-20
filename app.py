from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import csv

app = FastAPI()

# ---------------------------
# Models for Carrier Verification
# ---------------------------
class VerifyCarrierRequest(BaseModel):
    mc_number: str

class VerifyCarrierResponse(BaseModel):
    verified: bool
    carrier_name: str

# ---------------------------
# Endpoint: /verify-carrier
# This mocks FMCSA verification.
# If the MC number starts with "MC", it’s valid.
# ---------------------------
@app.post("/verify-carrier", response_model=VerifyCarrierResponse)
async def verify_carrier(request: VerifyCarrierRequest):
    if not request.mc_number.startswith("MC"):
        raise HTTPException(status_code=400, detail="Invalid MC number format")
    
    # Simulated successful verification.
    return VerifyCarrierResponse(verified=True, carrier_name="ABC Trucking")

# ---------------------------
# Endpoint: /loads/{reference_number}
# This endpoint simulates loading details from a CSV.
# ---------------------------
@app.get("/loads/{reference_number}")
def get_load(reference_number: str):
    # For demonstration, using a hardcoded dictionary.
    loads_data = {
        "REF09460": {
            "reference_number": "REF09460",
            "origin": "Denver, CO",
            "destination": "Detroit, MI",
            "equipment_type": "Dry Van",
            "rate": 868,
            "commodity": "Automotive Parts"
        },
        "REF04684": {
            "reference_number": "REF04684",
            "origin": "Dallas, TX",
            "destination": "Chicago, IL",
            "equipment_type": "Dry Van or Flatbed",
            "rate": 570,
            "commodity": "Agricultural Products"
        },
        "REF09690": {
            "reference_number": "REF09690",
            "origin": "Detroit, MI",
            "destination": "Nashville, TN",
            "equipment_type": "Dry Van",
            "rate": 1495,
            "commodity": "Industrial Equipment"
        }
    }
    
    if reference_number in loads_data:
        return loads_data[reference_number]
    else:
        raise HTTPException(status_code=404, detail="Load not found")

# ---------------------------
# Models for Evaluate Offer
# ---------------------------
class EvaluateOfferRequest(BaseModel):
    carrier_offer: int
    our_last_offer: int
    offer_attempt: int = 1

class EvaluateOfferResponse(BaseModel):
    result: str  # e.g., "counter", "accept", "decline"
    new_offer: int
    message: str

# ---------------------------
# Endpoint: /evaluate-offer
# This endpoint simulates simple negotiation logic.
# ---------------------------
@app.post("/evaluate-offer", response_model=EvaluateOfferResponse)
def evaluate_offer(request: EvaluateOfferRequest):
    if request.carrier_offer >= request.our_last_offer:
        return EvaluateOfferResponse(
            result="accept",
            new_offer=request.carrier_offer,
            message="Offer accepted."
        )
    else:
        if request.offer_attempt == 1:
            new_offer = (request.our_last_offer + request.carrier_offer) // 2
            return EvaluateOfferResponse(
                result="counter",
                new_offer=new_offer,
                message=f"We can go as low as {new_offer} on this load."
            )
        else:
            new_offer = (request.our_last_offer + request.carrier_offer) // 2
            return EvaluateOfferResponse(
                result="counter",
                new_offer=new_offer,
                message=f"This is our final counter at {new_offer}."
            )

# ---------------------------
# Run the API with Uvicorn (for local testing)
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
