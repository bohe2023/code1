import matplotlib
matplotlib.use("TkAgg")

import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("raw_all.csv")

plt.plot(df["LON_GPS"], df["LAT_GPS"], ".", markersize=1)
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title("LAT/LON GPS trajectory")
plt.axis("equal")
plt.show()