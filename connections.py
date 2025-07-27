import psycopg2
import os
from influxdb import InfluxDBClient

POSTGRES_CON = os.getenv("POSTGRES_CON") + "fitness"
 

def get_connection():
    return psycopg2.connect(POSTGRES_CON)


INFLUX_HOST = os.getenv("INFLUX_HOST")
INFLUX_PORT = os.getenv("INFLUX_PORT")
def get_influx_client(database):
    client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT)
    client.switch_database(database)