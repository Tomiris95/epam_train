import requests

def get_weather(city: str) -> str:

    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1}
    ).json()

    if "results" not in geo:
        return f"Could not find weather data for {city}."

    lat = geo["results"][0]["latitude"]
    lon = geo["results"][0]["longitude"]

    weather = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current_weather": True
        }
    ).json()

    cw = weather["current_weather"]

    return (
        f"Weather in {city.title()}:\n"
        f"- Temperature: {cw['temperature']} °C\n"
        f"- Wind speed: {cw['windspeed']} km/h\n"
        f"- Weather code: {cw['weathercode']}"
    )
