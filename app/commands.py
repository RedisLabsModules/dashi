import asyncio
import os

import click
import yaml
from flask import current_app

from . import db, utils

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
repos_file = os.path.join(parent_dir, "main.yaml")


@click.command("sync_db")
def sync_db():
    # Load data from yaml file
    with open(repos_file) as file:
        repos = yaml.load(file, Loader=yaml.BaseLoader)["repos"]

    # Run the db population coroutine
    current_app.logger.info("Starting to populate the database.")
    utils.populate_repos(db, repos)
    asyncio.run(utils.populate_commits(db))
    asyncio.run(utils.populate_pipelines(db))
    current_app.logger.info("Finished populating the database.")
