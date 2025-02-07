# Setting up and running the project

First create a virtual environment to install the project's requirements in a local environment:
```
$ python3 -m venv <myvenvpath>
```

Then install the requirements after activating your venv:
```
$ source <myvenvpath>/bin/activate
$ pip isntall -r requirements
```

Apply migration to create the fuel stations table:
```
$ python manage.py migrate
```

## Loading fuel stations data

Make sure you have the csv file containing the data with the needed format and header names and export the path to the file as an environment variable:
```
FUEL_PRICES_PATH=<path_to_fuel_stations_data>
```
Then you can run the `load_fuel_prices` command:
```
$ python manage.py load_fuel_data
```
### running the app
```
$ python manage.py runserver
```

**NOTE**: The data will be added to a local sqlite database which is the default for django.

### Testing the api
```
curl -XPOST -H "Content-type: application/json" -d '{
 "start": [<longitude>, <latitude>],
 "finish": [<longitude>, <latitude>]
}' 'http://localhost:8000/optimize-fuel/'
```