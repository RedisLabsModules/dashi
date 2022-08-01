FROM python:latest

WORKDIR /app
ADD . /app

RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt

CMD [ "python", "-m" , "flask", "run", "--host=0.0.0.0"]
