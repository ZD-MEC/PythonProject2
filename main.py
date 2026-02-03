import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from DataProcessor import DataProcessor
from F1_API_importer import F1_API
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# 1. Page Configuration
st.set_page_config(page_title="F1 Analytics", layout="wide")

st.title("🏎️ F1 Analytics App")
st.markdown("Analyze F1 telemetry data for specific drivers and sessions.")

# 2. Sidebar - User Inputs
# We put inputs in the sidebar to keep the main view clean
with st.sidebar:
  st.header("Session Settings")


  selected_year = st.selectbox("Select Year", options= ['2023', '2024'])
  df_session = F1_API.get_sessions(selected_year)

  selected_country = st.selectbox("Select Country", options= df_session['country_name'].unique() )
  df_filtered_country = df_session[df_session['country_name'] == selected_country]
  valid_races = df_filtered_country[df_filtered_country['session_name'].str.contains('Race|Qualifying', case=False)]
  selected_race = st.selectbox("Select Race", options=  valid_races['session_name'].unique())
  session_row = valid_races[valid_races['session_name'] == selected_race]
  session_key = int(session_row['session_key'].iloc[0])


  df_driver = F1_API.get_drivers(session_key)

  selected_driver = st.selectbox("Driver Number", options = df_driver['full_name'])
  driver_number = df_driver.loc[df_driver['full_name']==selected_driver, 'driver_number'].iloc[0]
  #lap_df, date_start_session = F1_API.get_laps(session_key, driver_number)

  st.markdown("---")
  st.markdown("### ⚔️ Compare Drivers")

# removing the selected driver to avoid duplicates
  available_drivers = df_driver[df_driver['full_name'] != selected_driver]['full_name']

  comparison_names = st.multiselect(
    "Select rivals (Max 2)",
    options=available_drivers,
    max_selections=2
  )

  st.markdown("---")





  st.markdown("---")

  # The Button!
  # The app waits here until the user clicks this button
  run_btn=st.button("Load Data")

# --- 3. Main Logic Flow ---

if run_btn:
  # Fetching data
  race_df = DataProcessor.get_merged_race_data(session_key, driver_number)
  positions_df = DataProcessor.get_position_data(session_key)
  laps_data, dates_data = DataProcessor.get_race_positions(session_key)

  # Save to session state
  st.session_state['race_data'] = race_df
  st.session_state['positions_data'] = positions_df
  st.session_state['laps_data'] = laps_data
  st.session_state['dates_data'] = dates_data

  comp_data = {}

  if comparison_names:
    for comp_driver_name in comparison_names:

      comp_num = df_driver.loc[df_driver['full_name'] == comp_driver_name, 'driver_number'].iloc[0]
      comp_race_df = DataProcessor.get_merged_race_data(session_key, comp_num)


      if not comp_race_df.empty:
        comp_data[comp_driver_name] = comp_race_df

  st.session_state['comp_data'] = comp_data

# --- 4. Visualization Logic (Runs on every reload/slider move) ---

# Check if we have data in memory
if 'race_data' in st.session_state and 'positions_data' in st.session_state:

  # Retrieve data from "The Backpack" (Session State)
  race_df = st.session_state['race_data']
  positions_df = st.session_state['positions_data']
  laps_data = st.session_state['laps_data']
  dates_data = st.session_state['dates_data']

  if not race_df.empty:
    #st.success("✅ Data Loaded Successfully!")

    # --- Top Metrics Row (Always visible) ---
    m1, m2 = st.columns(2)
    m1.metric("Top Speed", f"{race_df['speed'].max()} km/h")
    m2.metric("Total Distance", f"{race_df['Total_distance'].max() / 1000:.2f} km")


    st.divider()  # Visual separation

    # --- The Tabs Architecture ---
    tab_telemetry, tab_overview, tab_compare = st.tabs(["📉 Telemetry Deep Dive", "🏁 Race Overview", "⚔️ Head-to-Head"])

    # === TAB 1: TELEMETRY (The slider lives here) ===
    with tab_telemetry:
      st.subheader("Lap-by-Lap Analysis")

      # 1. The Slider
      # We explicitly cast to int to avoid errors
      max_lap = int(race_df['lap_number'].max())
      selected_lap = st.slider("Select Lap", min_value=1, max_value=max_lap, value=1)

      # 2. Filter Data (Fast in-memory operation)
      subset = race_df[race_df['lap_number'] == selected_lap]

      # 3. Split View (Map vs Graph)
      col_map, col_graph = st.columns([1, 1])  # 1:2 ratio

      with col_map:
        st.markdown("**Track Map** (Speed Visualization)", text_alignment="center")
        # Placeholder for the colored map (we will upgrade this next)
        map_df = subset
        map_df = map_df.rename(columns={'x': 'X_coordinate', 'y': 'Y_coordinate'})


        # 3. Visualization Fix: Fixed Aspect Ratio
        # Using Scatter to allow coloring by speed
        fig_map = px.scatter(
          map_df,
          x='X_coordinate',
          y='Y_coordinate',
          color='speed',
          color_continuous_scale='Turbo',
          hover_data=['speed', 'Total_distance', 'throttle', 'rpm', 'n_gear', 'brake']

        )
        st.plotly_chart(fig_map, use_container_width=True)

        #st.line_chart(subset, x='x', y='y')

      with col_graph:
        # 1. Create the Subplots structure (5 rows, sharing X axis)
        fig_tel = make_subplots(
          rows=5, cols=1,
          shared_xaxes=True,  # Critical: Zooming one zooms all
          vertical_spacing=0.06,  # spaces in layout
          row_heights=[0.3, 0.15, 0.15, 0.2, 0.2],  # Speed gets more space
          subplot_titles=("Speed", "RPM", "Gear", "Throttle", "Brake")
        )

        # --- Trace 1: Speed (Blue) ---
        fig_tel.add_trace(
          go.Scatter(
            x=subset['Total_distance'], y=subset['speed'],
            name='Speed',
            line=dict(color='blue', width=2)
          ), row=1, col=1
        )

        # --- Trace 2: RPM (Yellow) ---
        fig_tel.add_trace(
          go.Scatter(
            x=subset['Total_distance'], y=subset['rpm'],
            name='RPM',
            line=dict(color='yellow', width=1)
          ), row=2, col=1
        )

        # --- Trace 3: Gear (White Step Line) ---
        # Important: Gears are discrete steps, not a smooth curve.
        # line_shape='hv' creates the "staircase" effect.
        fig_tel.add_trace(
          go.Scatter(
            x=subset['Total_distance'], y=subset['n_gear'],
            name='Gear',
            line=dict(color='white', width=1.5),
            line_shape='hv'
          ), row=3, col=1
        )

        # --- Trace 4: Throttle (Green Area) ---
        fig_tel.add_trace(
          go.Scatter(
            x=subset['Total_distance'], y=subset['throttle'],
            name='Throttle',
            line=dict(color='green', width=1),
            fill='tozeroy'  # Fills area under the line
          ), row=4, col=1
        )

        # --- Trace 5: Brake (Red Area) ---
        fig_tel.add_trace(
          go.Scatter(
            x=subset['Total_distance'], y=subset['brake'],
            name='Brake',
            line=dict(color='red', width=1),
            fill='tozeroy'
          ), row=5, col=1
        )

        # 3. Layout Polish
        fig_tel.update_layout(
          height=800,  # Taller chart to fit everything
          showlegend=False,  # Titles are enough
          hovermode="x unified"  # The "Crosshair" effect - shows all values at once

        )

        # Update Axes (Remove labels from inner plots to save space)
        fig_tel.update_yaxes(showgrid=True, gridcolor='#333')
        fig_tel.update_xaxes(showgrid=False, visible=False)  # Hide X on top plots
        fig_tel.update_xaxes(title_text="Total Distance (m)", visible=True, row=5, col=1)  # Show X only on bottom

        st.plotly_chart(fig_tel, use_container_width=True)


    # === TAB 2: OVERVIEW (The new graph lives here) ===
    with tab_overview:
      st.subheader("Position Changes: Start vs Finish", text_alignment="center")

      # Using the NEW positions_df we fetched
      if not positions_df.empty:
        # Create the grouped bar chart
        fig_pos = px.bar(
          positions_df,
          x="full_name",
          y="position",
          color="type",  # This creates the two columns (Start/Finish)
          barmode="group",  # Places bars side-by-side
          title="Driver Position Changes",
          text_auto=True  # Shows the numbers on the bars
        )
        st.plotly_chart(fig_pos, use_container_width=True)


    with tab_compare:
      st.subheader("⚔️ Fastest Lap Comparison")
      comp_data = st.session_state.get('comp_data', {})
      drivers_to_plot = []
      drivers_to_plot.append((selected_driver, race_df, '#1f77b4'))
      colors = ['#ff7f0e', '#2ca02c']
      for i, (name, df) in enumerate(comp_data.items()):
        color = colors[i % len(colors)]
        drivers_to_plot.append((name, df, color))

      if race_df is not None:

        # בניית הגרף (3 שורות: מהירות, גז, ברקס)
        fig_comp = make_subplots(
          rows=3, cols=1,
          shared_xaxes=True,
          vertical_spacing=0.08,  # ריווח נדיב לכותרות
          row_heights=[0.5, 0.25, 0.25],  # המהירות מקבלת חצי מהמקום
          subplot_titles=("Speed Comparison", "Throttle", "Brake")
        )

        for name, df, color in drivers_to_plot:
          if df.empty: continue

          # 1. Safely retrieve driver number from the main drivers list
          current_driver_num = df_driver.loc[df_driver['full_name'] == name, 'driver_number'].iloc[0]

          # 2. Fetch official lap times
          laps_official, _ = F1_API.get_laps(session_key, current_driver_num)
          valid_laps = laps_official.dropna(subset=['lap_duration'])

          # Safe variable initialization to prevent NameError
          fastest_lap_num = df['lap_number'].max()
          raw_time = "N/A"

          # 3. Find the fastest lap based on duration (not speed)
          if not valid_laps.empty:
            fastest_idx = valid_laps['lap_duration'].idxmin()
            fastest_lap_num = valid_laps.loc[fastest_idx, 'lap_number']

            # Format time string (remove days and excessive microseconds)
            t_str = str(valid_laps.loc[fastest_idx, 'lap_duration'])
            raw_time = t_str.split('days')[-1].strip()
            if '.' in raw_time and len(raw_time.split('.')[-1]) > 3:
              raw_time = raw_time[:-3]

          # 4. Slice data for specific lap + Normalize X-Axis
          lap_data = df[df['lap_number'] == fastest_lap_num].copy()

          # Skip if no data exists for this specific lap
          if lap_data.empty:
            continue

          # --- Normalization: Create dist_norm column ---
          # Subtract the starting distance so all laps start at 0m
          lap_data['dist_norm'] = lap_data['Total_distance'] - lap_data['Total_distance'].min()

          legend_label = f"{name} (Lap {int(fastest_lap_num)} | {raw_time})"

          # --- Trace 1: Speed ---
          fig_comp.add_trace(
            go.Scatter(
              x=lap_data['dist_norm'],  # Use normalized distance
              y=lap_data['speed'],
              name=f"{legend_label}",
              legendgroup=name,
              line=dict(color=color, width=2)
            ), row=1, col=1
          )

          # --- Trace 2: Throttle ---
          fig_comp.add_trace(
            go.Scatter(
              x=lap_data['dist_norm'],
              y=lap_data['throttle'],
              name=f"{name} Throttle",
              legendgroup=name,
              showlegend=False,
              line=dict(color=color, width=1.5, dash='dot')
            ), row=2, col=1
          )

          # --- Trace 3: Brake ---
          fig_comp.add_trace(
            go.Scatter(
              x=lap_data['dist_norm'],
              y=lap_data['brake'],
              name=f"{name} Brake",
              legendgroup=name,
              showlegend=False,
              line=dict(color=color, width=1.5)
            ), row=3, col=1
          )

          # Update X-axis title for the bottom chart
        fig_comp.update_xaxes(title_text="Lap Distance (m)", visible=True, row=3, col=1)
else:
  # Initial State (Before clicking button)
  st.info("👈 Please select a session and click 'Load Data' to begin.")














