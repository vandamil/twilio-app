from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, request
from openai import OpenAI
from twilio.twiml.messaging_response import MessagingResponse
from vanna.openai import OpenAI_Chat
from vanna.vannadb import VannaDB_VectorStore
import psycopg2
import os

app = Flask(__name__)

load_dotenv()
MY_VANNA_MODEL = os.environ["MY_VANNA_MODEL"]
vanna_api_key = os.environ["vanna_api_key"]
api_key = os.environ["api_key"]
postgres_key = os.environ["postgres_key"]


class MyVanna(VannaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        VannaDB_VectorStore.__init__(self, vanna_model=MY_VANNA_MODEL, vanna_api_key=vanna_api_key, config=config)
        OpenAI_Chat.__init__(self, client=OpenAI(base_url="https://api.groq.com/openai/v1",api_key=api_key), config=config)

vn = MyVanna(config={'model': "llama3-8b-8192"})

vn.connect_to_sqlite('BallByBall.db')


def sql(question):
    return vn.generate_sql(question,allow_llm_to_see_data=True)

def df(sql_q):
    return vn.run_sql(sql_q)

def summary(qn,df):
    return vn.generate_summary(question=qn,df=df)  

def store_data(phone_number,question,sql_query,response):
    
    conn = psycopg2.connect(postgres_key)
    cur = conn.cursor()
    
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                phone_number VARCHAR(15),
                question TEXT,
                sql_query TEXT,
                response TEXT,
                date_time TIMESTAMP);''')
    
    cur.execute("INSERT INTO users (phone_number, question, sql_query, response, date_time) VALUES (%s, %s, %s, %s, %s)",(phone_number,question,sql_query,response,datetime.now()))
    
    conn.commit()
    cur.close()
    conn.close()


@app.route("/message", methods=['POST'])
def receive_message():
    
    # Get the incoming message from the request
    phone_number = request.values.get('From', '').replace('whatsapp:','')
    question = request.values.get('Body', '')
    sql_query = sql(question)
    response = summary(question,df(sql_query))+"\n"+"Want more insights? Check out our website!"+"\n"+"https://cricace-2024.streamlit.app/"

    # Create Twilio response
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(response)
    
    store_data(phone_number,question,sql_query,response)
    
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
