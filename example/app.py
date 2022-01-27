import json
import os

from flask import Flask, render_template, request

from flagsmith import Flagsmith
from flagsmith.models import DefaultFlag

app = Flask(__name__)

flagsmith = Flagsmith(
    environment_key=os.environ.get("FLAGSMITH_ENVIRONMENT_KEY"),
    defaults=[
        # Set a default flag which will be used if the "secret_button"
        # feature is not returned by the API
        DefaultFlag(
            enabled=False,
            value=json.dumps({"colour": "#b8b8b8"}),
            feature_name="secret_button",
        )
    ],
)


@app.route("/", methods=["GET", "POST"])
def home():
    if request.args:
        identifier = request.args["identifier"]

        trait_key = request.args.get("trait-key")
        trait_value = request.args.get("trait-value")
        traits = {trait_key: trait_value} if trait_key else None

        # Get the flags for an identity, including the provided trait which will be
        # persisted to the API for future requests.
        identity_flags = flagsmith.get_identity_flags(
            identifier=identifier, traits=traits
        )
        show_button = identity_flags.is_feature_enabled("secret_button")
        button_data = json.loads(identity_flags.get_feature_value("secret_button"))
        return render_template(
            "home.html",
            show_button=show_button,
            button_colour=button_data["colour"],
            identifier=identifier,
        )

    # Get the default flags for the current environment
    flags = flagsmith.get_environment_flags()
    show_button = flags.is_feature_enabled("secret_button")
    button_data = json.loads(flags.get_feature_value("secret_button"))

    return render_template(
        "home.html", show_button=show_button, button_colour=button_data["colour"]
    )
