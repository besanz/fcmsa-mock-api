Carrier Sales API

Live API URL: https://happyrobot-usecase-e1d892c0f5a0.herokuapp.com/
API Documentation: https://happyrobot-usecase-e1d892c0f5a0.herokuapp.com/docs#/

This API, built with FastAPI, uses a CSV file (loads.csv) to store load details and provides three main endpoints: POST /loads, POST /verify-carrier, and POST /evaluate-offer.

For load lookup, send a JSON body like:
{
  "reference_number": "REF09460"
}
The API normalizes the reference number (removing "REF" and leading zeros) and returns the load details (fields: reference_number, origin, destination, equipment_type, rate, commodity).

For carrier verification, send:
{
  "mc_number": "MC123456"
}
This simulates verifying a carrier against a preset list and returns whether the carrier is verified along with the carrier name.

For offer evaluation, send:
{
  "carrier_offer": 600,
  "our_last_offer": 700,
  "offer_attempt": 1
}
The API responds with a JSON object indicating the result ("accept" or "counter"), the new offer value, and a message.

The CSV file must have the following columns:
reference_number, origin, destination, equipment_type, rate, commodity
For example:
REF09460, Denver, CO, Detroit, MI, Dry Van, 868, Automotive Parts
REF04684, Dallas, TX, Chicago, IL, Dry Van or Flatbed, 570, Agricultural Products
REF09690, Detroit, MI, Nashville, TN, Dry Van, 1495, Industrial Equipment

This API is deployed on Heroku. You can test it using the live URL and documentation provided above. A demo video is also available to walk through the solution and showcase the API’s functionality.
