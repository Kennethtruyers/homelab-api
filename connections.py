import psycopg2
import os
from influxdb import InfluxDBClient

POSTGRES_CON = os.getenv("POSTGRES_CON")
 

def get_fitness_connection():
    return psycopg2.connect(POSTGRES_CON) + "fitness"

def get_cashflow_connection():
    return psycopg2.connect(POSTGRES_CON) + "cashflow"


INFLUX_HOST = os.getenv("INFLUX_HOST")
INFLUX_PORT = os.getenv("INFLUX_PORT")
def get_influx_client(database):
    client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT)
    client.switch_database(database)
    return client