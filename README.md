# SAIL Amsterdam Crowd Monitoring Dashboard

## Overview 

The crowd monitoring dashboard provides real-time and historical insights of crowd (count/flow) data within the event area. It also provides crowd predictions by locations using XGBoost Machine Learning Model.  

## Features

(i) User Authentication 

(ii) Visualisation of Current/Historical Crowd Count/Flow with relevant features (tram/metro stations, car flow data and vessel position)

(iii) Crowd Count Prediction

## Structure 

project/

│

├── README.md (author: @sheikharfahmibinsheikharzimi)

├── home.py (author: @Ewan2024-2.0) 

├── data_loader.py 

├── map_utils.py (author: @Ewan2024-2.0) 

├── security.py (author: @nhollnagel)

├── calculate_crowd_flow.py (author: @cedric6022)

├── Notebooks

│   ├── calculate_crowd_flow.ipynb (author: @cedric6022)

│   ├── event_graphs.ipynb (author: @Ewan2024-2.0) 

│   ├── Map_Filters_Vessels.ipynb (author: @nhollnagel)

│   ├── Pre_ML_DataExploration.ipynb (author: @sheikharfahmibinsheikharzimi)

│   ├── Read_KNMI_WeatherData.ipynb (author: @sheikharfahmibinsheikharzimi)

│   ├── Read_Sensor_(Crowd)_Data.ipynb (author: @sheikharfahmibinsheikharzimi)

│   ├── Read_Sensor_(Location)_Data.ipynb (author: @sheikharfahmibinsheikharzimi)

│   ├── Read_TramMetro_Data.ipynb (author: @sheikharfahmibinsheikharzimi)

│   ├── User_Authentication.ipynb (author: @nhollnagel)

│   ├── XGB_Model_Training.ipynb (author: @sheikharfahmibinsheikharzimi)

├── Archived_PastNotebooks

├── data

├── pages/

│   ├── 1_Crowd_Data_Graph.py (author: @cedric6022)

│   ├── 2_Settings.py (author: @sheikharfahmibinsheikharzimi)

│   ├── 3_Predictive_Analysis.py (author: @sheikharfahmibinsheikharzimi)

│   ├── 4_Vessels_Positioning.py (author: @lukarekhvia)

│   ├── 5_Car_Flow.py (author: @lukarekhvia)

└── requirements.txt



## Installation 

1. Clone the repo:

git clone [[https://github.com/<your-username>/<repo-name>.git](https://github.com/Ewan2024/SAIL2025---Group20.git)](https://github.com/Ewan2024/SAIL2025---Group20.git)

cd SAIL2025---Group20

2. Create a virtual environment:

python -m venv venv

source venv/bin/activate     # Mac/Linux

venv\Scripts\activate        # Windows

3. Install dependecies:

pip install -r requirements.txt

## Running the Dashboard

streamlit run app.py

## Data Sources

Tram/Metro Stations: Municipality of Amsterdam

Weather Data: KNMI Weather Data

Sensor Location: From TU Delft Faculty 

Sensor Data (Crowd Count): From TU Delft Faculty 

Vessel Position: From TU Delft Faculty 

Car Flow Data: TomTom

## Acknowledgements

We would like to express our gratitude to instructors, guest lecturers and teaching assistants of TIL6020 TIL Python Programming for their support, guidance and mentorship throughout this project.

Contributors: 

1. Sheikh Arfahmi Bin Sheikh Arzimi [@sheikharfahmibinsheikharzimi](https://github.com/sheikharfahmibinsheikharzimi)


2. Ewan Brett [@Ewan2024-2.0](https://github.com/Ewan2024-2.0)


3. Cedric Nissen [@cedric6022](https://github.com/cedric6022)


4. Nils Hollnagel [@nhollnagel](https://github.com/nhollnagel)


5. Luka Rehviašvili [@lukarekhvia](https://github.com/lukarekhvia)

