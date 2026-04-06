"""Module for displaying line charts using Flask and matplotlib."""
from flask import Flask, render_template, request



import numpy as np
import matplotlib.pyplot as plt
import pandas as pd



app = Flask(__name__)


times = pd.timedelta_range(start="0 days 00:03:00", periods=50, freq="3S")


df = pd.DataFrame({
    "t": times.astype(str),
    "Phase": ["Exercise"] * 50,
    "Marker": [""] * 50,
    "V'O2": np.random.normal(1.5, 0.2, 50).round(2),
    "V'O2/kg": np.random.normal(13, 1.5, 50).round(1),
    "V'O2/HR": np.random.normal(12, 1, 50).round(1),
    "V'CO2": np.random.normal(1.3, 0.15, 50).round(2),
    "HR": np.random.randint(120, 150, 50),
    "WR": np.random.randint(50, 100, 50),
    "V'E/V'O2": np.random.normal(23, 2, 50).round(1),
    "V'E/V'CO2": np.random.normal(25, 2, 50).round(1),
    "RER": np.random.normal(0.9, 0.05, 50).round(2),
    "V'E": np.random.normal(35, 5, 50).round(1),
    "VT": np.random.normal(1.8, 0.4, 50).round(2),
    "BF": np.random.randint(15, 25, 50),
    "METS": np.random.normal(3.5, 0.7, 50).round(1)
})

## Time to seconds for plotting
def time_to_seconds(t):
    """Convert time string to seconds."""
    if "days" in t:
        t = t.split("days")[-1].strip()
    h, m, s = t.split(':')
    return int(h)*3600 + int(m)*60 + float(s)




df['t_seconds'] = df['t'].apply(time_to_seconds)

metrics = ['V\'O2', 'V\'CO2', 'HR', 'RER', 'V\'E', 'VT', 'BF', 'METS']

@app.route("/")
def index():
    """Render the line chart page with the selected metric."""
    metric = request.args.get("metric", "V'O2")

    fig, ax = plt.subplots(figsize=(8, 4))

    line_obj, = ax.plot(
        df['t_seconds'],
        df[metric],
        marker='o',
        color="#51b6cf"   
    )
    line_obj.set_gid("chart-line")

    ax.set_title(f"{metric} over time")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel(metric)
    ax.grid(True)

    # Save SVG directly into /static/
    fig.savefig("static/chart.svg", format="svg")

    with open("static/chart.svg", "r", encoding="utf-8") as f:
        svg = f.read()

    return render_template(
        "index.html",
        metrics=metrics,
        selected=metric,
        svg=svg
    )
if __name__ == "__main__":
    app.run(debug=True)
