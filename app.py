from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
matplotlib.use("Agg")
import os

app = Flask(__name__)

CSV_FILE = "sleep_data.csv"
URL_PREFIX = ""

# Ensure CSV exists
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=["date", "fall_asleep", "awake", "wake_up"])
    df.to_csv(CSV_FILE, index=False)

@app.route(URL_PREFIX + "/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Add new data
        date = request.form["date"]
        fall_asleep = request.form["fall_asleep"]
        awake = request.form["awake"]
        wake_up = request.form["wake_up"]

        df = pd.read_csv(CSV_FILE)
        df = pd.concat([df, pd.DataFrame([[date, fall_asleep, awake, wake_up]], columns=df.columns)])
        df.to_csv(CSV_FILE, index=False)
        return redirect(url_for("index"))

    df = pd.read_csv(CSV_FILE)
    plot_sleep_data(df)
    plot_sleep_duration(df)
    # Calculate last night's duration
    if df.empty:
        last_night_duration = "N/A"
        last_week_duration = "N/A"
    else:    
        last_night_duration = calculate_duration(df.iloc[-1])  # Get the last entry
        last_night_duration = f"{last_night_duration.seconds // 3600:02d}h{last_night_duration.seconds % 3600 // 60:02d}m"
        last_week_duration = calculate_average_duration(df)  # Calculate average over the last week
        last_week_duration = f"{last_week_duration.seconds // 3600:02d}h{last_week_duration.seconds % 3600 // 60:02d}m"

    return render_template("index.html", data=df.to_dict(orient="records"),
                           last_night_duration=last_night_duration, last_week_duration=last_week_duration)

@app.route(URL_PREFIX + "/manage", methods=["GET"])
def manage():
    """Render the data management page."""
    df = pd.read_csv(CSV_FILE)
    return render_template("manage.html", data=df.to_dict(orient="records"))

@app.route(URL_PREFIX + "/edit/<int:index>", methods=["GET", "POST"])
def edit(index):
    """Edit an existing row."""
    df = pd.read_csv(CSV_FILE)
    if request.method == "POST":
        df.loc[index, "date"] = request.form["date"]
        df.loc[index, "fall_asleep"] = request.form["fall_asleep"]
        df.loc[index, "awake"] = request.form["awake"]
        df.loc[index, "wake_up"] = request.form["wake_up"]
        df.to_csv(CSV_FILE, index=False)
        return redirect(url_for("manage"))

    row = df.loc[index]
    return render_template("edit.html", index=index, row=row)

@app.route(URL_PREFIX + "/delete/<int:index>", methods=["POST"])
def delete(index):
    """Delete an existing row."""
    df = pd.read_csv(CSV_FILE)
    df = df.drop(index).reset_index(drop=True)
    df.to_csv(CSV_FILE, index=False)
    return redirect(url_for("manage"))

def plot_sleep_duration(df):
    """Generate and save a plot of the sleep duration."""
    if df.empty:
        if os.path.exists("static/duration_plot.png"):
            os.remove("static/duration_plot.png")
        return

    plt.figure(figsize=(10, 6))
    dates = pd.to_datetime(df["date"])

    plt.xticks(ticks=dates, labels=dates.dt.strftime("%Y-%m-%d"), rotation=45)
    durations = df.apply(lambda row: calculate_duration(row), axis=1)
    durations = durations.dt.total_seconds() / 3600  # Convert to hours
    plt.plot(dates, durations, color="red")

    plt.xlabel("Date")
    plt.ylabel("Sleep time (hours)")
    plt.grid(False)
    plt.tight_layout()

    plt.savefig("static/duration_plot.png")
    plt.close()

def plot_sleep_data(df):
    """Generate and save a plot of the sleep data."""
    if df.empty:
        if os.path.exists("static/sleep_plot.png"):
            os.remove("static/sleep_plot.png")
        return

    plt.figure(figsize=(10, 6))
    dates = pd.to_datetime(df["date"])

    plt.xticks(ticks=dates, labels=dates.dt.strftime("%Y-%m-%d"), rotation=45)
    
    # Normalize times relative to a predefined reference hour
    reference_hour = 18

    fall_asleep = (pd.to_datetime(df["fall_asleep"]).dt.hour + 
                pd.to_datetime(df["fall_asleep"]).dt.minute / 60)
    awake = (pd.to_datetime(df["awake"]).dt.hour + 
            pd.to_datetime(df["awake"]).dt.minute / 60)
    wake_up = (pd.to_datetime(df["wake_up"]).dt.hour + 
            pd.to_datetime(df["wake_up"]).dt.minute / 60)

    fall_asleep = fall_asleep.where(fall_asleep >= reference_hour, fall_asleep + 24)
    awake = awake.where(awake >= reference_hour, awake + 24)
    wake_up = wake_up.where(wake_up >= reference_hour, wake_up + 24)
    hours = range(reference_hour, reference_hour + 25)  # From reference hour to the next day
    plt.yticks(ticks=hours[::-1], labels=[f"{int(h) % 24:02d}:{int((h % 1) * 60):02d}" for h in hours[::-1]])
    plt.gca().invert_yaxis()



    plt.fill_between(dates, fall_asleep, awake, color="blue", alpha=0.2, label="Sleep Time")
    plt.fill_between(dates, awake, wake_up, color="green", alpha=0.2, label="Awake Time")

    plt.plot(dates, fall_asleep, label="Fall Asleep", color="blue")
    plt.plot(dates, awake, label="Awake", color="orange")
    plt.plot(dates, wake_up, label="Wake Up", color="green")

    plt.xlabel("Date")
    plt.ylabel("Time")
    plt.legend()
    plt.grid(False)
    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig("static/sleep_plot.png")
    plt.close()

def calculate_duration(row):
    """Calculate the duration between fall asleep and wake up times."""
    if row.empty:
        return
    fall_asleep_time = datetime.strptime(row["fall_asleep"], "%H:%M")
    awake_time = datetime.strptime(row["awake"], "%H:%M")

    # If wake up time is earlier than fall asleep time, it means it spans past midnight
    if awake_time < fall_asleep_time:
        awake_time += timedelta(days=1)  # Adjust wake up time to the next day

    duration = awake_time - fall_asleep_time
    return duration

def calculate_average_duration(df):
    """Calculate the average sleep duration over the last 7 days."""
    if df.empty:
        return
    durations = df.apply(lambda row: calculate_duration(row), axis=1)
    durations = durations.iloc[-7:]
    avg_duration = durations.mean()
    return avg_duration

if __name__ == "__main__":
    app.run(debug=False)
