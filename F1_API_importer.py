import requests
import pandas as pd
import streamlit as st


class F1_API:
    BASE_URL = "https://api.openf1.org/v1"

    @staticmethod
    @st.cache_data
    def get_sessions(year):
        url = f"{F1_API.BASE_URL}/sessions?year={year}"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            df = pd.DataFrame(data)
            cols_to_keep = ['session_key', 'location', 'country_name', 'session_name', 'date_start', 'session_type']
            existing_cols = [c for c in cols_to_keep if c in df.columns]
            df = df[existing_cols]
            df['label']= df['country_name'] + " " + df['session_name']


            return df.sort_values(by='date_start')

        except Exception as e:
            st.error(f"Error fetching sessions: {e}")
            return pd.DataFrame()


    @staticmethod
    @st.cache_data
    def get_drivers(session_key):
        url = f"{F1_API.BASE_URL}/drivers?session_key={session_key}"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            df = pd.DataFrame(data)

            if 'driver_number' in df.columns:
                df = df.dropna(subset=['driver_number'])
            if 'full_name' not in df.columns:
                print("⚠️ Warning: 'full_name' column missing. Using 'broadcast_name' instead.")

                df['full_name'] = df['broadcast_name']


            return df[['driver_number', 'full_name']]


        except Exception as e:
            st.error(f"Error fetching drivers: {e}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data
    def get_telemetry(session_key, driver_number, date_start_session):
        print(session_key, driver_number, date_start_session)
        url = f"{F1_API.BASE_URL}/car_data?driver_number={driver_number}&session_key={session_key}"
        try:
            response = requests.get(url, timeout=20)

            if response.status_code != 200:
                print(f"Server Error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()
            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'], format='ISO8601')
            df = df.sort_values('date')[df['date'] > date_start_session]

            df['time_diff'] = df['date'].diff().dt.total_seconds().fillna(0)
            df['distance'] = df['time_diff'] * df['speed'] / 3.6
            df['Total_distance'] = df['distance'].cumsum()

            return df

        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame()



    @staticmethod
    @st.cache_data

    def get_laps(session_key, driver_number):
        url = f"{F1_API.BASE_URL}/laps?session_key={session_key}&driver_number={driver_number}"

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"Server Error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()
            if not data:
                return pd.DataFrame()

            lap_df = pd.DataFrame(data)
            lap_df['date_start'] = pd.to_datetime(lap_df['date_start'], format='ISO8601')
            lap_df = lap_df.sort_values('date_start')
            lap_df['lap_duration'] = pd.to_timedelta(lap_df['lap_duration'], unit='s')
            if 1 in lap_df['lap_number'].values:
                date_start_session= lap_df[lap_df['lap_number'] == 1 ]['date_start'][0]


            else:
                date_start_session = lap_df['date_start'].iloc[0]

            lap_df = lap_df.rename(columns={'date_start': 'date'})
            # df['date_end_session'] = pd.to_timedelta(df['lap_duration']) + df['date_start_session']
            return lap_df, date_start_session


        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data
    def get_location(session_key, driver_number, date_start_session):
        url_loc = f"{F1_API.BASE_URL}/location?driver_number={driver_number}&session_key={session_key}"
        try:
            response = requests.get(url_loc, timeout=20)

            if response.status_code != 200:
                print(f"Server Error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()
            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'], format='ISO8601')
            df = df.sort_values('date')[df['date'] > date_start_session]


            return df

        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data
    def get_all_drivers_positions(session_key):
        url_position = f"{F1_API.BASE_URL}/position?session_key={session_key}"
        try:
            response = requests.get(url_position, timeout=20)

            if response.status_code != 200:
                print(f"Server Error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()
            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'], format='ISO8601')
            df = df.sort_values('date')

            return df

        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data
    def get_all_laps(session_key):
        url_laps = f"{F1_API.BASE_URL}/laps?session_key={session_key}"
        try:
            response = requests.get(url_laps, timeout=15)

            if response.status_code != 200:
                print(f"Server Error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()
            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)

            return df

        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame()