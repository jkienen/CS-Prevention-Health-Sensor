#################################### Part 0: Environment Evaluation ->

# Imports necessary modules
import os
import datetime
import pandas as pd
from falconpy import Hosts
from falconpy import ZeroTrustAssessment


# ----------------------------------------->

# Define base names
BASE_AUDIT = "Prevention-Health-Sensor"

# Getting current date in format (MM-YYYY)
current_date = datetime.datetime.now()
formatted_date = current_date.strftime("%m-%Y")

# Getting current path for file saving
current_dir = os.path.dirname(os.path.realpath(__file__))
env_path = os.path.join(current_dir, f"./.env")

# Define saving directory
parent_directory = os.path.join(current_dir, f"../Datas/{formatted_date}")

# Define auto create DIR
if not os.path.exists(parent_directory):
    os.makedirs(parent_directory)



#################################### Part 1: Obtaining Authorization Token ->

# Data obtained from project file
from dotenv import load_dotenv
if os.path.exists(env_path):

    load_dotenv(env_path)

    # Get .env variables
    CLIENT_ID = os.getenv("CLIENT_ID")
    SECRET_ID = os.getenv("SECRET_ID")
    
    # If valid itens
    if CLIENT_ID and SECRET_ID:



        #################################### Part 2: Extracting Falcon ID"s ->

        # Init extract data
        try:

            # Define falcon request
            falcon = Hosts(client_id=CLIENT_ID, client_secret=SECRET_ID)

            # Prepare variables for [id] call
            filter_limit = 5000

            response = falcon.query_devices_by_filter(limit=filter_limit)

            # Response variable
            if response["status_code"] == 401:
                print("\nAccess denied, invalid bearer token\n")

            assets = response["body"]["resources"]


            
            #################################### Part 3: Extracting Falcon Fields ->

            # Perform the query
            response = falcon.get_device_details(ids=assets)

            # Response variable
            results = response["body"]["resources"]

            # Create list with filter
            empty = "-"
            datas = []

            for item in results:

                host_id = item["device_id"]
                host_name = item["hostname"] if "hostname" in item else empty
                host_type = item["product_type_desc"] if "product_type_desc" in item else empty
                host_os = item["platform_name"] if "platform_name" in item else empty
                host_state = item["host_hidden_status"].capitalize() if "host_hidden_status" in item else empty
                rfm = True if "reduced_functionality_mode" in item and item["reduced_functionality_mode"] == "yes" else False
                linux_mode = item["linux_sensor_mode"] if "linux_sensor_mode" in item else empty
                
                # ->
                datas.append({
                    "Host Id": host_id,
                    "Host Name": host_name, 
                    "Host Type": host_type,
                    "Host OS": host_os, 
                    "Host State": host_state,
                    "RFM": rfm,
                    "Linux Mode": linux_mode
                })



            #################################### Part 4: Extracting Falcon Sensor Health Checks ->

            # Perform the query
            falcon = ZeroTrustAssessment(client_id=CLIENT_ID, client_secret=SECRET_ID)

            def is_rfm(signal):
                name = signal["signal_name"].upper()
                return "REDUCED" in name or "RFM" in name

            # Index assessment results by aid (matches the device_id / Host Id from Part 3)
            assessments = {}
            id_list = [item["Host Id"] for item in datas]

            # Falcon allows at most 1000 AIDs per assessment call — request in chunks
            for start in range(0, len(id_list), 1000):

                response = falcon.get_assessment(ids=id_list[start:start + 1000])

                for resource in (response["body"]["resources"] or []):

                    aid = resource["aid"]
                    sensor_signals = resource["assessment_items"]["sensor_signals"]
                    is_linux = resource["event_platform"] == "Lin"
                    host_score = resource.get("assessment", {}).get("sensor_config", empty)

                    # Host is in Reduced Functionality Mode if its RFM signal fails
                    in_rfm = any(is_rfm(s) and s["meets_criteria"] != "yes" for s in sensor_signals)

                    # "Host Score" comes before the item columns; then one column per sensor signal
                    signals = {"Host Score": host_score}
                    for signal in sensor_signals:
                        column_name = f"Item: {signal['signal_name']}"

                        # RFM signal itself: OK when in full functionality, ATTENTION (root cause) otherwise
                        if is_rfm(signal): value = "OK" if signal["meets_criteria"] == "yes" else "ATTENTION"

                        # Linux host in RFM: every other item points to the root cause, even passing ones
                        elif is_linux and in_rfm: value = "Check RFM"
                        elif signal["meets_criteria"] == "yes": value = "OK"
                        else: value = "ATTENTION"

                        signals[column_name] = value

                    assessments[aid] = signals

            # Link each host (Host Id) with its assessment (aid) and append the signal columns
            for item in datas: item.update(assessments.get(item["Host Id"], {}))



            #################################### Part 5: Saving the information ->

            # Create a DataFrame with every host
            df = pd.DataFrame(datas)

            # Keep "Linux Mode" only for Linux hosts
            df["Linux Mode"] = df["Linux Mode"].where(df["Host OS"] == "Linux")

            # Only generate reports for these operating systems
            target_os = {"Linux", "Mac", "Windows"}

            # Create a separate DataFrame per Host OS
            for host_os, dataframe in df.groupby("Host OS"):
                if host_os not in target_os: continue

                # Keep only the signal columns relevant to this OS, then fill remaining nulls with the empty marker
                dataframe = dataframe.dropna(axis=1, how="all").fillna(empty)

                # Reference stamp columns — always last
                dataframe["Reference Month"] = current_date.strftime("%m")
                dataframe["Reference Year"] = current_date.strftime("%Y")
                dataframe["Reference Date"] = current_date.strftime("%Y-%m-%d")

                os_csv = os.path.join(parent_directory, f"{host_os}_{BASE_AUDIT}.csv")
                dataframe.to_csv(os_csv, index=False, encoding="utf-8")


        # Except errors
        except Exception as err: print(err)

    else: print(".env file exists but is missing some variables!")
else: print(".env file does not exist!")
