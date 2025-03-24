Carrier Sales API

Live API URL:
https://happyrobot-usecase-e1d892c0f5a0.herokuapp.com/

API Documentation:
https://happyrobot-usecase-e1d892c0f5a0.herokuapp.com/docs#/

------------------------------------------------------------
Overview
------------------------------------------------------------
This API is built with FastAPI and uses a CSV file (loads.csv) as the data source for load details. It provides three main endpoints:

1. Load Lookup: Retrieve load details by reference number.
2. Carrier Verification: Verify carriers using the FMCSA API.
3. Offer Evaluation: Evaluate and negotiate offers.

The solution is deployed on Heroku and demonstrates integration of voice AI use cases with backend API development.

------------------------------------------------------------
Endpoints
------------------------------------------------------------

1. Load Lookup
   Endpoint: POST /loads

   Description:
   Retrieves load details by reference number from the request body. The API normalizes the reference number by removing the "REF" prefix and any leading zeros. If a matching load is found in the CSV, it returns details such as reference_number, origin, destination, equipment_type, rate, and commodity. Otherwise, it returns a 404 error.

   Example Request Body:
   {
     "reference_number": "REF09460"
   }

   Example Response:
   {
     "reference_number": "REF09460",
     "origin": "Denver, CO",
     "destination": "Detroit, MI",
     "equipment_type": "Dry Van",
     "rate": 868,
     "commodity": "Automotive Parts"
   }

2. Carrier Verification
   Endpoint: POST /verify-carrier

   Description:
   Verifies the carrier’s MC number using the FMCSA API. You can provide the MC number as either "MC845901" or simply "845901". The API strips any "MC" prefix and calls the FMCSA endpoint:
   https://mobile.fmcsa.dot.gov/qc/services/carriers/845901?webKey=cdc33e44d693a3a58451898d4ec9df862c65b954

   It then parses the JSON response to extract the carrier’s legal name (or DBA name as a fallback).

   Example Request Body:
   {
     "mc_number": "MC845901"
   }

   Example Response:
   {
     "verified": true,
     "carrier_name": "JOHN S THOMPSON HAULING INC"
   }

3. Offer Evaluation
   Endpoint: POST /evaluate-offer

   Description:
   Evaluates an offer by comparing the carrier’s offer with the last offer. If the carrier’s offer is greater than or equal to the last offer, the offer is accepted. Otherwise, the API calculates a counter-offer by averaging the two values. If multiple negotiation attempts have been made (i.e. offer_attempt > 1), the counter-offer is considered final.

   Example Request Body:
   {
     "carrier_offer": 600,
     "our_last_offer": 700,
     "offer_attempt": 1
   }

   Example Response:
   {
     "result": "counter",
     "new_offer": 650,
     "message": "We can go as low as 650 on this load."
   }

------------------------------------------------------------
CSV Data Format
------------------------------------------------------------
The loads.csv file should contain the following columns:
- reference_number
- origin
- destination
- equipment_type
- rate
- commodity

Example CSV Content:
reference_number,origin,destination,equipment_type,rate,commodity
REF09460,Denver, CO,Detroit, MI,Dry Van,868,Automotive Parts
REF04684,Dallas, TX,Chicago, IL,Dry Van or Flatbed,570,Agricultural Products
REF09690,Detroit, MI,Nashville, TN,Dry Van,1495,Industrial Equipment

------------------------------------------------------------
Deployment
------------------------------------------------------------
This solution is deployed on Heroku:

Live API URL:
https://happyrobot-usecase-e1d892c0f5a0.herokuapp.com/

API Documentation:
https://happyrobot-usecase-e1d892c0f5a0.herokuapp.com/docs#/

For local development, run:
uvicorn app:app --reload

Ensure that the following packages are installed:
pip install fastapi uvicorn requests

------------------------------------------------------------
Demo Video
------------------------------------------------------------
A demo video is available that walks through the solution, explains the implementation, and demonstrates test calls for the API endpoints.
