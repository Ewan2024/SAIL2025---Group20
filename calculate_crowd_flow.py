import pandas as pd
from data_loader import load_sensor_locations
from data_loader import load_sensor_data


# function to add rows with calculated crowd flow data to crowd_flow
def calculate_crowd_flow(timestamp):
    correct_time = str(timestamp) + "+02:00"
    # load data sets
    sensor_data = load_sensor_data()
    sensor_locations = load_sensor_locations()


    # makes crowd_flow a global variable that exists outside the function
    global crowd_flow
    # checks if crowd_flow doesn't exist
    if "crowd_flow" not in globals():
        # create empty data frame
        crowd_flow = pd.DataFrame()


        # add column names and remove useless columns
        column_names = sensor_data.columns
        for i in column_names:
            crowd_flow[i] = ()

        remove_columns = ["hour", "minute", "day", "month", "weekday", "is_weekend"]
        for i in remove_columns:
            crowd_flow = crowd_flow.drop(columns=i)


    # checks if the data type of this column is numeric or something else (string, list...). 
    # "dtype" looks for data type. "object" is non-numeric data type
    if sensor_locations["Effectieve  breedte"].dtype == object:
        # the data in sensor_locations is stored with a "," instead of a "." and first needs to be converted to a float value
        sensor_locations["Effectieve  breedte"] = sensor_locations["Effectieve  breedte"].str.replace(",", ".").astype(float)
    
    
    # checks if the index of crowd_flow is already timestamp
    if crowd_flow.index.name != "timestamp":
        # sets index to column timestamp so the function can later add rows to this data frame
        crowd_flow.set_index("timestamp", inplace=True)


    # gets the index of the respective row
    row = sensor_data.index[sensor_data['timestamp'] == correct_time]
    # list wich will be added to the dataframe
    flow_data = []


    for i in crowd_flow.columns:
        # this skips the current iteration of the loop if the column = timestamp
        if i == "timestamp":
            continue

        # gets the index of the respective row
        another_row = sensor_locations.index[sensor_locations['sensor_id_full'] == i]

        # empty rows might mess up the length of the list that will be appended, therefore an empty placeholder is added instead
        if sensor_data[sensor_data['timestamp'] == correct_time].empty or sensor_locations[sensor_locations['sensor_id_full'] == i].empty:
            flow_data.append(0)
            continue

        # calculates crowd flow as: number of people / width / time(3 mins)
        flow_number = int(sensor_data.loc[row, i].iloc[0]) / float(sensor_locations.loc[another_row, "Effectieve  breedte"].iloc[0]) / 3
        # adds the result of the calculation to the list flow_data
        flow_data.append(flow_number)


    # adds the crowd flow of the timestamp used in this function to the data frame crowd_flow
    crowd_flow.loc[correct_time] = flow_data
    dict = {col: [val] for col, val in crowd_flow.loc[correct_time].items()}
    #crowd_flow_long = crowd_flow.reset_index()

    return dict