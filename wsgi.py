from flask import Flask

def create_app():
    app = Flask(__name__)

    import forms
    app.register_blueprint(forms.bp)

    return app
