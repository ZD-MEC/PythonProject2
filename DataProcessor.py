from F1_API_importer import F1_API
import pandas as pd
import streamlit as st

class DataProcessor:
    @staticmethod
    def get_merged_race_data(session_key, driver_number):
        try:
            lap_df, date_start_session = F1_API.get_laps(session_key, driver_number)
            df_tel = F1_API.get_telemetry(session_key, driver_number, date_start_session)
            df_loc = F1_API.get_location(session_key, driver_number, date_start_session)

            # Critical Data Cleaning & Sorting
            # Convert 'date' to datetime objects to avoid type mismatches
            df_tel['date'] = pd.to_datetime(df_tel['date'])
            df_loc['date'] = pd.to_datetime(df_loc['date'])
            lap_df['date'] = pd.to_datetime(lap_df['date'])

            # Drop rows with missing dates and sort by date
            # (This is mandatory for merge_asof to work correctly without crashing)
            df_tel = df_tel.dropna(subset=['date']).sort_values('date')
            df_loc = df_loc.dropna(subset=['date']).sort_values('date')
            lap_df = lap_df.dropna(subset=['date']).sort_values('date')

            # Merge based on nearest timestamp (car data and location)
            df_combined = pd.merge_asof(
                df_tel,
                df_loc,
                on='date',
                direction='nearest',
                tolerance=pd.Timedelta('500ms')
            )

            # Drop rows where location matching failed (no x, y data)
            df_combined = df_combined.dropna(subset=['x', 'y'])

            # Merge lap info based on timestamp, adding lap numbers (backward direction)
            df_combined_2 = pd.merge_asof(
                df_combined,
                lap_df[['date', 'lap_number']],
                on='date',
                direction='backward'
            )

            return df_combined_2

        except Exception as e:
            # Error Handling
            # Display a user-friendly error in the app
            st.error(f"⚠️ Error processing race data: {e}")

            # Log the full error to the console for debugging
            print(f"DEBUG ERROR: {e}")

            # Return an empty DataFrame to prevent the main app from crashing
            return pd.DataFrame()

    @staticmethod
    def get_position_data(session_key):
        """
        Calculates Start vs Finish positions based on telemetry timestamps.
        This is reliable even when the official grid info is missing.
        """
        lap_pos_df = F1_API.get_all_drivers_positions(session_key)
        if lap_pos_df.empty:
            return pd.DataFrame()

        drivers_df = F1_API.get_drivers(session_key)

        # Determine start (first timestamp) and finish (last timestamp) positions
        start_position = lap_pos_df.groupby('driver_number')['position'].first().reset_index(name='position')
        finish_position = lap_pos_df.groupby('driver_number')['position'].last().reset_index(name='position')

        start_position['type'] = "Grid Start"
        finish_position['type'] = "Race Finish"

        position_table = pd.concat([start_position, finish_position])

        # Merge with driver names
        if not drivers_df.empty:
            drivers_df['driver_number'] = drivers_df['driver_number'].astype(int)
            position_table['driver_number'] = position_table['driver_number'].astype(int)
            position_df = pd.merge(position_table, drivers_df[['driver_number', 'full_name']], on='driver_number',
                                   how='left')
        else:
            position_df = position_table
            position_df['full_name'] = "Driver " + position_df['driver_number'].astype(str)

        position_df = position_df.sort_values(by=['type', 'position'], ascending=[False, True])

        return position_df

    @staticmethod
    def get_race_positions(session_key):
        """
        Used for the Line Charts (Position changes over laps/time).
        """
        lap_pos_df = F1_API.get_all_drivers_positions(session_key)
        drivers_df = F1_API.get_drivers(session_key)
        all_laps_df = F1_API.get_all_laps(session_key)

        if lap_pos_df.empty or all_laps_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # Clean Dates
        lap_pos_df['date'] = pd.to_datetime(lap_pos_df['date'], format='ISO8601', errors='coerce')
        lap_pos_df = lap_pos_df.dropna(subset=['date'])

        all_laps_df['date_start'] = pd.to_datetime(all_laps_df['date_start'], format='ISO8601', errors='coerce')
        all_laps_df = all_laps_df.dropna(subset=['date_start'])
        all_laps_df = all_laps_df.sort_values('date_start')

        # Prepare subset for merging
        pos_subset = lap_pos_df[['date', 'driver_number', 'position']].sort_values('date')

        # Merge positions with laps
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

        # Add driver names if available
        if not drivers_df.empty:
            drivers_df['driver_number'] = drivers_df['driver_number'].astype(int)
            merged_laps['driver_number'] = merged_laps['driver_number'].astype(int)
            lap_pos_df['driver_number'] = lap_pos_df['driver_number'].astype(int)

            merged_laps = pd.merge(merged_laps, drivers_df[['driver_number', 'full_name']], on='driver_number',
                                   how='left')
            merged_dates = pd.merge(lap_pos_df, drivers_df[['driver_number', 'full_name']], on='driver_number',
                                    how='left')
        else:
            merged_laps['full_name'] = merged_laps['driver_number'].astype(str)
            merged_dates = lap_pos_df
            merged_dates['full_name'] = merged_dates['driver_number'].astype(str)

        merged_laps['position'] = pd.to_numeric(merged_laps['position'])
        merged_laps['lap_number'] = pd.to_numeric(merged_laps['lap_number'])
        merged_dates['position'] = pd.to_numeric(merged_dates['position'])

        return merged_laps, merged_dates

    @staticmethod
    def get_session_fastest_lap(session_key):
        """
        Retrieves details of the fastest lap.
        FIXED: Added unit='s' to timedelta conversion to handle seconds correctly.
        """
        all_laps = F1_API.get_all_laps(session_key)
        drivers = F1_API.get_drivers(session_key)

        if all_laps.empty: return None

        # --- THE FIX IS HERE: unit='s' ---
        # Without unit='s', 80 seconds becomes 80 nanoseconds (effectively 0)
        all_laps['lap_duration'] = pd.to_timedelta(all_laps['lap_duration'], unit='s')

        # Filter valid laps (now that units are correct, > 30s logic works)
        valid_laps = all_laps[all_laps['lap_duration'] > pd.Timedelta(seconds=30)]
        valid_laps = valid_laps.dropna(subset=['lap_duration'])

        if valid_laps.empty: return None

        # Find the fastest lap
        fastest_idx = valid_laps['lap_duration'].idxmin()
        fastest_row = valid_laps.loc[fastest_idx]
        driver_num = int(fastest_row['driver_number'])

        # Find driver name safely
        driver_name = f"#{driver_num}"
        if not drivers.empty:
            drivers['driver_number'] = drivers['driver_number'].astype(int)
            match = drivers[drivers['driver_number'] == driver_num]
            if not match.empty:
                driver_name = match['full_name'].iloc[0]

        # Format time nicely
        total_seconds = fastest_row['lap_duration'].total_seconds()
        minutes, seconds = divmod(total_seconds, 60)
        time_str = f"{int(minutes)}:{seconds:06.3f}"

        return {"driver": driver_name, "time": time_str, "lap": int(fastest_row['lap_number'])}

    @staticmethod
    def get_session_summary_stats(session_key):
        """
        Calculates Race Winner, DNFs, and Biggest Mover.
        FIXED: Uses 'get_position_data' (the graph data) instead of API grid_position.
        """
        results_df = F1_API.get_session_result(session_key)
        drivers_df = F1_API.get_drivers(session_key)

        # --- USE THE GRAPH DATA FOR MOVERS ---
        pos_df = DataProcessor.get_position_data(session_key)

        if results_df.empty: return None

        # Merge for names
        results_df['driver_number'] = results_df['driver_number'].astype(int)
        if not drivers_df.empty:
            drivers_df['driver_number'] = drivers_df['driver_number'].astype(int)
            results_df = pd.merge(results_df, drivers_df[['driver_number', 'full_name']], on='driver_number',
                                  how='left')
        else:
            results_df['full_name'] = "Driver " + results_df['driver_number'].astype(str)

        stats = {}

        # --- A. The Winner ---
        winner_row = results_df[results_df['position'] == 1]
        if not winner_row.empty:
            stats['winner'] = winner_row['full_name'].iloc[0]
        else:
            stats['winner'] = "N/A"

        # --- B. DNFs ---
        if 'dnf' in results_df.columns:
            dnf_rows = results_df[results_df['dnf'] == True]
            stats['dnf_count'] = len(dnf_rows)
            stats['dnf_names'] = ", ".join(dnf_rows['full_name'].tolist()) if not dnf_rows.empty else "None"
        else:
            stats['dnf_count'] = 0
            stats['dnf_names'] = "None"

        # --- C. Biggest Mover (USING POS_DF) ---
        if not pos_df.empty:
            # Pivot the graph data: One row per driver with Start and Finish
            # We filter for only drivers who have both Start and Finish data points
            starts = pos_df[pos_df['type'] == 'Grid Start'][['driver_number', 'position']].rename(
                columns={'position': 'Start'})
            finishes = pos_df[pos_df['type'] == 'Race Finish'][['driver_number', 'position']].rename(
                columns={'position': 'Finish'})

            # Merge Start and Finish
            movers = pd.merge(starts, finishes, on='driver_number')

            if not movers.empty:
                # Calculate Gain (Start - Finish)
                movers['gain'] = movers['Start'] - movers['Finish']

                # Find Max Gain
                max_gain = movers['gain'].max()
                best_driver_num = movers[movers['gain'] == max_gain]['driver_number'].iloc[0]

                # Get Name
                mover_name = f"#{best_driver_num}"
                if not drivers_df.empty:
                    name_match = drivers_df[drivers_df['driver_number'] == best_driver_num]
                    if not name_match.empty:
                        mover_name = name_match['full_name'].iloc[0]

                stats['mover_name'] = mover_name
                stats['mover_gain'] = int(max_gain)
            else:
                stats['mover_name'] = "N/A"
                stats['mover_gain'] = 0
        else:
            stats['mover_name'] = "N/A"
            stats['mover_gain'] = 0

        return stats

    @staticmethod
    def get_championship_tables(session_key):
        """
        Generates clean Driver and Constructor standings tables using official API data.
        Note: This data is only available for RACE sessions, not Qualifying.
        """
        drivers_standings = F1_API.get_championship_drivers(session_key)
        teams_standings = F1_API.get_championship_teams(session_key)
        driver_info = F1_API.get_drivers(session_key)

        df_drivers_final = pd.DataFrame()
        df_teams_final = pd.DataFrame()

        # --- 1. Process Constructors (Teams) ---
        if not teams_standings.empty:
            teams_standings['Points Added'] = teams_standings['points_current'] - teams_standings['points_start']

            df_teams_final = teams_standings[['team_name', 'points_start', 'points_current', 'Points Added']].copy()
            df_teams_final.columns = ['Team', 'Points Before', 'Points After', 'Points Added']
            df_teams_final = df_teams_final.sort_values(by='Points After', ascending=False)

        # --- 2. Process Drivers ---
        if not drivers_standings.empty:
            drivers_standings['driver_number'] = drivers_standings['driver_number'].astype(int)

            if not driver_info.empty:
                driver_info['driver_number'] = driver_info['driver_number'].astype(int)
                merged_drivers = pd.merge(drivers_standings, driver_info, on='driver_number', how='left')
            else:
                merged_drivers = drivers_standings
                merged_drivers['full_name'] = "Driver " + merged_drivers['driver_number'].astype(str)
                merged_drivers['team_name'] = "Unknown"

            merged_drivers['Points Added'] = merged_drivers['points_current'] - merged_drivers['points_start']

            if 'full_name' not in merged_drivers.columns:
                merged_drivers['full_name'] = "Driver " + merged_drivers['driver_number'].astype(str)
            if 'team_name' not in merged_drivers.columns:
                merged_drivers['team_name'] = "Unknown"

            merged_drivers['team_name'] = merged_drivers['team_name'].fillna('Unknown')

            df_drivers_final = merged_drivers[
                ['full_name', 'team_name', 'points_start', 'points_current', 'Points Added']].copy()
            df_drivers_final.columns = ['Driver', 'Team', 'Points Before', 'Points After', 'Points Added']
            df_drivers_final = df_drivers_final.sort_values(by='Points After', ascending=False)

        return df_drivers_final, df_teams_final