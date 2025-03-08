FROM python:3.11

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

RUN pip3 install pytest==8.3.4
RUN pip3 install requests
RUN pip3 install xmltodict==0.12.0
RUN pip3 install geopy==2.2.0
RUN pip3 install astropy
RUN pip3 install redis==4.0.0
RUN pip3 install Werkzeug==2.2.2 

COPY iss_tracker.py /app/iss_tracker.py
COPY test_iss_tracker.py /app/test_iss_tracker.py

ENV FLASK_APP=iss_tracker.py

ENTRYPOINT ["python"]
CMD ["iss_tracker.py"]
