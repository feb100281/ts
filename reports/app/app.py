from dash import Dash

from .rpts.daily_report import main

app = Dash(__name__)

app.layout = main()

if __name__ == "__main__":

    app.run(debug=True, port=8050)