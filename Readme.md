
# Phishtank service

The application is configured using dockercompose.
It uses Redis as database. Writes to Redis are idempotent


## Running service

Run command

`docker compose build && docker compose up`

to build and run both containers


## Making requests 

You can than run download request below. Service downloads data from url 
http://data.phishtank.com/data/online-valid.csv . Parameter download_from is 
mandatory and can be in ISO 8601 format (You can also use a timestamp).


`curl localhost:8000/download?download_from=<Time>`

For example: 

`curl localhost:8000/download?download_from=0`


If there are issues with rate limiting on phishtank.com server, you can add parameter test_data=true.
Service will use offline data stored inside.

`curl localhost:8000/download?download_from=1\&test_data=true`

To run lookup on domain use command

`curl localhost:8000/search?domain=<Domain>`

For example: 

`curl localhost:8000/search?domain=storage.cloud.google.com`
