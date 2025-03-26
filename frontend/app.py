import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import requests

BACKEND_URL = (
    "http://localhost:8000/api"  # Adjust if your backend is deployed elsewhere
)

app = dash.Dash(__name__)

# Define categories and statuses for filters
categories = ["restaurant", "entertainment", "park"]
statuses = ["visited", "pending", "prioritized"]

app.layout = html.Div(
    [
        html.H1("My Places"),
        html.Div(
            [
                html.Label("Category:"),
                dcc.Dropdown(
                    id="category-filter",
                    options=[{"label": "All", "value": ""}]
                    + [{"label": c.capitalize(), "value": c} for c in categories],
                    value="",
                ),
                html.Label("Status:"),
                dcc.Dropdown(
                    id="status-filter",
                    options=[{"label": "All", "value": ""}]
                    + [{"label": s.capitalize(), "value": s} for s in statuses],
                    value="",
                ),
            ],
            style={"display": "flex", "gap": "20px", "marginBottom": "20px"},
        ),
        dcc.Graph(id="places-map", figure={}),
        html.Div(id="place-details"),
        html.H2("Add New Place"),
        html.Form(
            [
                html.Div(
                    [
                        html.Label("Name:"),
                        dcc.Input(id="new-place-name", type="text", required=True),
                    ],
                    style={"marginBottom": "10px"},
                ),
                html.Div(
                    [
                        html.Label("Category:"),
                        dcc.Dropdown(
                            id="new-place-category",
                            options=[
                                {"label": c.capitalize(), "value": c}
                                for c in categories
                            ],
                        ),
                    ],
                    style={"marginBottom": "10px"},
                ),
                html.Div(
                    [
                        html.Label("Latitude:"),
                        dcc.Input(
                            id="new-place-lat", type="number", step="any", required=True
                        ),
                    ],
                    style={"marginBottom": "10px"},
                ),
                html.Div(
                    [
                        html.Label("Longitude:"),
                        dcc.Input(
                            id="new-place-lon", type="number", step="any", required=True
                        ),
                    ],
                    style={"marginBottom": "10px"},
                ),
                html.Button("Add Place", id="add-place-button", n_clicks=0),
                html.Div(id="add-place-output"),
            ],
            style={"marginBottom": "20px"},
        ),
    ]
)


@app.callback(
    Output("places-map", "figure"),
    [Input("category-filter", "value"), Input("status-filter", "value")],
)
def update_map(selected_category, selected_status):
    params = {}
    if selected_category:
        params["category"] = selected_category
    if selected_status:
        params["status"] = selected_status
    try:
        response = requests.get(f"{BACKEND_URL}/places/", params=params)
        response.raise_for_status()
        places = response.json()
        if not places:
            return px.scatter_map(height=600)
        fig = px.scatter_map(
            places,
            lat="latitude",
            lon="longitude",
            hover_name="name",
            hover_data=["category", "status"],
            color="category",
            zoom=10,
            height=600,
            # You might need to adjust the layout depending on your desired style
            # For a style similar to "open-street-map", you can try:
            # mapbox_style="carto-positron" or other available styles
        )
        fig.update_layout(
            # You might need to adjust the map style here.
            # Try commenting this line out first or using a different style.
            # mapbox_style="open-street-map",
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return fig
    except requests.exceptions.RequestException as e:
        return px.scatter_map(title=f"Error loading data: {e}", height=600)


@app.callback(Output("place-details", "children"), Input("places-map", "hoverData"))
def show_place_details(hoverData):
    if hoverData:
        place_name = hoverData["points"][0]["hovertext"]
        try:
            # Fetch place details by name (you might want to use ID for more robustness)
            response = requests.get(f"{BACKEND_URL}/places/")
            response.raise_for_status()
            places = response.json()
            selected_place = next((p for p in places if p["name"] == place_name), None)
            if selected_place:
                details = [
                    html.H3(selected_place["name"]),
                    html.P(f"Category: {selected_place['category']}"),
                    html.P(f"Status: {selected_place['status']}"),
                    html.H4("Reviews:"),
                    html.Ul(
                        [
                            html.Li(r["review_text"])
                            for r in selected_place.get("reviews", [])
                        ]
                    ),
                ]
                return html.Div(details)
        except requests.exceptions.RequestException as e:
            return html.Div(f"Error loading place details: {e}")
    return html.Div("Hover over a point on the map to see details.")


@app.callback(
    Output("add-place-output", "children"),
    Input("add-place-button", "n_clicks"),
    [
        dash.State("new-place-name", "value"),
        dash.State("new-place-category", "value"),
        dash.State("new-place-lat", "value"),
        dash.State("new-place-lon", "value"),
    ],
)
def add_new_place(n_clicks, name, category, lat, lon):
    if n_clicks > 0:
        if not all([name, category, lat, lon]):
            return "Please fill in all the fields."
        try:
            new_place = {
                "name": name,
                "category": category,
                "latitude": lat,
                "longitude": lon,
            }
            response = requests.post(f"{BACKEND_URL}/places/", json=new_place)
            response.raise_for_status()
            return "Place added successfully!"
        except requests.exceptions.RequestException as e:
            return f"Error adding place: {e}"
    return ""


if __name__ == "__main__":
    app.run(debug=True)
