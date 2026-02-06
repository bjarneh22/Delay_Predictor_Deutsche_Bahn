# import packages here

# encode variables
le_station = LabelEncoder() 
df["station_current_enc"] = le_station.fit_transform(df["station_current"])

# select features and target
X = df[["station_current_enc", "stops_total"]]
y = df["delay"]

# train final model on all data
final_model = RandomForestRegressor(n_estimators=100, random_state=42)
final_model.fit(X, y)

# save model + encoder
joblib.dump(final_model, "model_final.joblib")
joblib.dump(le_station, "le_station.joblib")