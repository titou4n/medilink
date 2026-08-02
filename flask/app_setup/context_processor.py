import extensions as ext
from flask import Flask

def register_context_processors(app:Flask):

    @app.context_processor
    def inject_format_datetime():
        return {"format_datetime": ext.utils.format_datetime}