from F1_API_importer import F1_API
import pandas as pd

class DataProcessor:
    @staticmethod
    def get_merged_race_data(session_key, driver_number):

        lap_df, date_start_session = F1_API.get_laps(session_key, driver_number)
        df_tel = F1_API.get_telemetry(session_key, driver_number, date_start_session)
        df_loc = F1_API.get_location(session_key, driver_number, date_start_session)



    # Merge telemetry and location data based on the nearest timestamp
    # 'direction="nearest"' finds the closest match (past or future)
    # tolerance is crucial: we don't want to match data points that are 5 seconds apart
        df_combined = pd.merge_asof(
            df_tel,
            df_loc,
            on='date',
            direction='nearest',  # Strategy
            tolerance=pd.Timedelta('500ms')  # Max allowed gap
        )
    # Drop rows where no location match was found (creates NaNs)
        df_combined = df_combined.dropna(subset=['x', 'y'])

        df_combined_2 = pd.merge_asof(
            df_combined,
            lap_df[['date', 'lap_number']],
            on='date',
            direction='backward'
        )

        return df_combined_2


    @staticmethod
    def get_position_data(session_key):
        lap_pos_df = F1_API.get_all_drivers_positions(session_key)
        if lap_pos_df.empty:
            return pd.DataFrame()

        drivers_df = F1_API.get_drivers(session_key)
        # Ensure we only take relevant columns to avoid 'position_x/y' issues
        drivers_df = drivers_df[['driver_number', 'full_name']]

        start_position = lap_pos_df.groupby('driver_number')['position'].first().reset_index(name='position')
        finish_position= lap_pos_df.groupby('driver_number')['position'].last().reset_index(name='position')
        start_position['type'] = "start_position"
        finish_position['type'] = "finish_position"
        position_table = pd.concat([start_position, finish_position])
        position_df = pd.merge(position_table, drivers_df, on='driver_number')
        position_df = position_df.sort_values(by=['type', 'position'])

        return position_df

    @staticmethod
    def get_race_positions(session_key):

        lap_pos_df = F1_API.get_all_drivers_positions(session_key)
        drivers_df = F1_API.get_drivers(session_key)
        all_laps_df = F1_API.get_all_laps(session_key)

        if lap_pos_df.empty or drivers_df.empty or all_laps_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        drivers_df = drivers_df[['driver_number', 'full_name']]
        lap_pos_df['date'] = pd.to_datetime(lap_pos_df['date'], format='ISO8601', errors='coerce')
        lap_pos_df = lap_pos_df.dropna(subset=['date'])

        pos_subset = lap_pos_df[['date', 'driver_number', 'position']].sort_values('date')

        all_laps_df['date_start'] = pd.to_datetime(all_laps_df['date_start'], format='ISO8601', errors='coerce')
        all_laps_df = all_laps_df.dropna(subset=['date_start'])
        all_laps_df = all_laps_df.sort_values('date_start')

        merged_laps = pd.merge_asof(
            all_laps_df,
            pos_subset,
            left_on='date_start',
            right_on='date',
            by='driver_number',
            direction='nearest',
            tolerance=pd.Timedelta('2s')
        )

        merged_laps = merged_laps.dropna(subset=['position'])
        merged_laps = pd.merge(merged_laps, drivers_df, on='driver_number')
        merged_laps['position'] = pd.to_numeric(merged_laps['position'])
        merged_laps['lap_number'] = pd.to_numeric(merged_laps['lap_number'])

        merged_dates = pd.merge(lap_pos_df, drivers_df, on='driver_number')
        merged_dates['position'] = pd.to_numeric(merged_dates['position'])

        return merged_laps, merged_dates

