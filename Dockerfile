FROM python:3.12.5
WORKDIR /app
COPY ./nidibot /app/nidibot
COPY setup.cfg /app/setup.cfg
COPY setup.py /app/setup.py
COPY pyproject.toml /app/pyproject.toml
RUN pip install -e .
RUN python -c 'from nidibot import Nidibot; Nidibot.initialize_folder()'
CMD [ "python", "-OO", "start_bot_docker.py" ]