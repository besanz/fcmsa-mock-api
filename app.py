from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import csv

app = FastAPI()

# Load CSV data into a dictionary at startup
def load_csv_data():
    loads_data = {}
    try:
        with open("loads.csv", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Strip any extra spaces from the reference number
                ref = row["reference_number"].strip()
                # Optionally, convert numeric fields like rate to int
                row["rate"] = int(row["rate"])
                loads_data[ref] = row
    except FileNotFoundError:
        print("loads.csv not found. Please make sure it exists in the same directory.")
    return loads_data

loads_data = load_csv_data()

# Verify Carrier Endpoint
class VerifyCarrierRequest(BaseModel):
    mc_number: str

class VerifyCarrierResponse(BaseModel):
    verified: bool
    carrier_name: str

@app.post("/verify-carrier", response_model=VerifyCarrierResponse)
async def verify_carrier(request: VerifyCarrierRequest):
    if not request.mc_number.startswith("MC"):
        raise HTTPException(status_code=400, detail="Invalid MC number format")
    return VerifyCarrierResponse(verified=True, carrier_name="ABC Trucking")

# Load Details Endpoint using CSV data
@app.get("/loads/{reference_number}")
def get_load(reference_number: str):
    reference_number = reference_number.strip()
    if reference_number in loads_data:
        return loads_data[reference_number]
    else:
        raise HTTPException(status_code=404, detail="Load not found")

# Evaluate Offer Endpoint
class EvaluateOfferRequest(BaseModel):
    carrier_offer: int
    our_last_offer: int
    offer_attempt: int = 1

class EvaluateOfferResponse(BaseModel):
    result: str
    new_offer: int
    message: str

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
