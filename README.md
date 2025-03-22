Carrier Sales API

Live API URL: https://happyrobot-usecase-e1d892c0f5a0.herokuapp.com/
API Documentation: https://happyrobot-usecase-e1d892c0f5a0.herokuapp.com/docs#/

This API, built with FastAPI, uses a CSV file (loads.csv) to store load details and provides three main endpoints. It is deployed on Heroku and demonstrates how to look up loads by reference number, verify carriers (simulating the FMCSA API), and evaluate offers.

To look up a load, send a POST request to /loads with a JSON body such as:
{ "reference_number": "REF09460" }
The API will normalize the reference number (removing "REF" and any leading zeros) and return the load details if found (reference_number, origin, destination, equipment_type, rate, commodity). If not found, it returns a 404 error.

To verify a carrier, send a POST request to /verify-carrier with:
{ "mc_number": "MC123456" }
If the MC number is recognized, the API returns whether the carrier is verified (true/false) and the carrier’s name. Otherwise, it returns a 404 error.

To evaluate an offer, send a POST request to /evaluate-offer with:
{ "carrier_offer": 600, "our_last_offer": 700, "offer_attempt": 1 }
The API compares the carrier’s offer with the last offer and either accepts or counters by averaging the two values. If offer_attempt > 1, it treats the new counter as final.

The loads.csv file should have columns: reference_number, origin, destination, equipment_type, rate, commodity. For example:
REF09460, Denver, CO, Detroit, MI, Dry Van, 868, Automotive Parts
REF04684, Dallas, TX, Chicago, IL, Dry Van or Flatbed, 570, Agricultural Products
REF09690, Detroit, MI, Nashville, TN, Dry Van, 1495, Industrial Equipment

This solution is deployed on Heroku, and the documentation can be accessed via the live links above. A demo video is also available, showing how the API works and how it can be tested in practice.
