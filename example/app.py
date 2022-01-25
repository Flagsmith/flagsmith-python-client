import json
import os

from flask import Flask, render_template

from flagsmith import Flagsmith

app = Flask(__name__)

flagsmith = Flagsmith(environment_key=os.environ.get("FLAGSMITH_ENVIRONMENT_KEY"))


@app.route("/")
def hello_world():
    flags = flagsmith.get_environment_flags()
    identity_flags = flagsmith.get_identity_flags("identifier")

    show_button = flags.is_feature_enabled(
        "secret_button"
    ) and identity_flags.is_feature_enabled("secret_button")

    button_data = json.loads(flags.get_feature_value("secret_button"))

    return render_template(
        "home.html", show_button=show_button, button_colour=button_data["colour"]
    )
